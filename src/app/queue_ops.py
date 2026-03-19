"""Queue operations for async solver tasks via Lakebase."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import SolveTask


def submit_task(session: Session, user_id: str, input_data: dict) -> str:
    """Insert a new PENDING task and return its ID."""
    task = SolveTask(
        user_id=user_id,
        input_json=json.dumps(input_data),
        status="PENDING",
    )
    session.add(task)
    session.flush()
    return str(task.id)


def poll_task(session: Session, task_id: str) -> Optional[dict]:
    """Check task status. Returns dict with status, output_json, error."""
    task = session.query(SolveTask).filter(SolveTask.id == uuid.UUID(task_id)).first()
    if not task:
        return None
    return {
        "status": task.status,
        "output_json": task.output_json,
        "error": task.error,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
    }


def claim_next_task(session: Session) -> Optional[SolveTask]:
    """Atomically claim the oldest PENDING task using SELECT FOR UPDATE SKIP LOCKED."""
    row = session.execute(
        text("""
            SELECT id FROM solve_tasks
            WHERE status = 'PENDING'
            ORDER BY created_at
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        """)
    ).fetchone()
    if not row:
        return None
    task = session.query(SolveTask).filter(SolveTask.id == row[0]).first()
    task.status = "RUNNING"
    task.started_at = datetime.now(timezone.utc)
    session.flush()
    return task


def complete_task(session: Session, task_id: uuid.UUID, output_json: str):
    """Mark a task as COMPLETED with results."""
    task = session.query(SolveTask).filter(SolveTask.id == task_id).first()
    task.status = "COMPLETED"
    task.finished_at = datetime.now(timezone.utc)
    task.output_json = output_json


def fail_task(session: Session, task_id: uuid.UUID, error_msg: str):
    """Mark a task as FAILED with an error message."""
    task = session.query(SolveTask).filter(SolveTask.id == task_id).first()
    task.status = "FAILED"
    task.finished_at = datetime.now(timezone.utc)
    task.error = error_msg
