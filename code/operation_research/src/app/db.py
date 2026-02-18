"""Synchronous database connection with Lakebase OAuth token refresh.

Adapted from lakebase_app async pattern for Streamlit:
- Uses synchronous SQLAlchemy (create_engine, sessionmaker)
- Token refresh runs in a background daemon thread
- do_connect event hook injects fresh tokens
"""

import logging
import os
import socket
import subprocess
import threading
import uuid
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base

logger = logging.getLogger(__name__)

_engine: Optional[Engine] = None
_session_maker: Optional[sessionmaker] = None
_current_token: Optional[str] = None
_token_refresh_thread: Optional[threading.Thread] = None
_lakebase_instance_name: Optional[str] = None
_stop_event = threading.Event()

TOKEN_REFRESH_INTERVAL_SECONDS = 50 * 60  # 50 minutes


def _resolve_hostname(hostname: str) -> Optional[str]:
    """Resolve hostname to IP, falling back to dig on macOS."""
    try:
        result = socket.getaddrinfo(hostname, 5432)
        if result:
            return result[0][4][0]
    except socket.gaierror:
        pass
    try:
        result = subprocess.run(
            ["dig", "+short", hostname, "A"],
            capture_output=True, text=True, timeout=10,
        )
        ips = [line for line in result.stdout.strip().split("\n") if line and line[0].isdigit()]
        if ips:
            return ips[0]
    except Exception:
        pass
    return None


def _get_workspace_client():
    """Get Databricks WorkspaceClient for token generation."""
    try:
        from databricks.sdk import WorkspaceClient
        if os.environ.get("DATABRICKS_CLIENT_ID") and os.environ.get("DATABRICKS_CLIENT_SECRET"):
            return WorkspaceClient(
                host=os.environ.get("DATABRICKS_HOST", ""),
                client_id=os.environ.get("DATABRICKS_CLIENT_ID", ""),
                client_secret=os.environ.get("DATABRICKS_CLIENT_SECRET", ""),
            )
        return WorkspaceClient()
    except Exception as e:
        logger.debug(f"Could not create WorkspaceClient: {e}")
        return None


def _generate_lakebase_token(instance_name: str) -> Optional[str]:
    """Generate a fresh OAuth token for Lakebase connection."""
    client = _get_workspace_client()
    if not client:
        return None
    try:
        cred = client.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[instance_name],
        )
        logger.info(f"Generated Lakebase token for: {instance_name}")
        return cred.token
    except Exception as e:
        logger.error(f"Failed to generate Lakebase token: {e}")
        return None


def _token_refresh_loop():
    """Background thread to refresh Lakebase OAuth token every 50 minutes."""
    global _current_token
    while not _stop_event.is_set():
        _stop_event.wait(TOKEN_REFRESH_INTERVAL_SECONDS)
        if _stop_event.is_set():
            break
        if _lakebase_instance_name:
            new_token = _generate_lakebase_token(_lakebase_instance_name)
            if new_token:
                _current_token = new_token
                logger.info("Lakebase token refreshed")


def start_token_refresh():
    global _token_refresh_thread
    if _token_refresh_thread is None:
        _stop_event.clear()
        _token_refresh_thread = threading.Thread(target=_token_refresh_loop, daemon=True)
        _token_refresh_thread.start()
        logger.info("Started Lakebase token refresh thread")


def is_postgres_configured() -> bool:
    return bool(
        os.environ.get("LAKEBASE_PG_URL")
        or (os.environ.get("LAKEBASE_INSTANCE_NAME") and os.environ.get("LAKEBASE_DATABASE_NAME"))
    )


def init_database(database_url: Optional[str] = None) -> Engine:
    """Initialize synchronous database engine with OAuth token injection."""
    global _engine, _session_maker, _current_token, _lakebase_instance_name

    url = database_url or os.environ.get("LAKEBASE_PG_URL")
    connect_args = {}

    if url:
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        logger.info("Using static LAKEBASE_PG_URL")
    else:
        instance_name = os.environ.get("LAKEBASE_INSTANCE_NAME")
        database_name = os.environ.get("LAKEBASE_DATABASE_NAME")
        if not instance_name or not database_name:
            raise ValueError("Set LAKEBASE_PG_URL or LAKEBASE_INSTANCE_NAME + LAKEBASE_DATABASE_NAME")

        _lakebase_instance_name = instance_name
        client = _get_workspace_client()
        if not client:
            raise ValueError("Could not create Databricks WorkspaceClient")

        instance = client.database.get_database_instance(name=instance_name)
        host = instance.read_write_dns

        _current_token = _generate_lakebase_token(instance_name)
        if not _current_token:
            raise ValueError(f"Failed to generate token for: {instance_name}")

        username = os.environ.get("LAKEBASE_USERNAME") or client.current_user.me().user_name

        hostaddr = _resolve_hostname(host)
        if hostaddr:
            connect_args["hostaddr"] = hostaddr
        connect_args["sslmode"] = "require"

        url = URL.create(
            drivername="postgresql+psycopg",
            username=username,
            password="",
            host=host,
            port=int(os.environ.get("DATABRICKS_DATABASE_PORT", "5432")),
            database=database_name,
        )
        logger.info(f"Using dynamic OAuth for Lakebase: {instance_name}")

    _engine = create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=False,
        pool_recycle=3600,
        echo=False,
        connect_args=connect_args,
    )

    if _lakebase_instance_name:
        @event.listens_for(_engine, "do_connect")
        def provide_token(dialect, conn_rec, cargs, cparams):
            if _current_token:
                cparams["password"] = _current_token

    _session_maker = sessionmaker(bind=_engine, expire_on_commit=False)

    # Create tables if they don't exist
    Base.metadata.create_all(_engine)

    return _engine


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        init_database()
    return _engine


@contextmanager
def session_scope():
    """Synchronous session context manager."""
    if _session_maker is None:
        init_database()
    session = _session_maker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
