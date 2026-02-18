"""Backend factory: toggle between mock (local dev) and real (Lakebase) backends."""

import os

USE_MOCK = os.getenv("USE_MOCK_BACKEND", "true").lower() == "true"


def get_backend():
    if USE_MOCK:
        from backend_mock import MockBackend
        return MockBackend()
    else:
        from backend_db import DbBackend
        return DbBackend()
