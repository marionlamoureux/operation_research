"""Real backend using Lakebase PostgreSQL via SQLAlchemy."""

import logging
import os

from db import init_database, session_scope, start_token_refresh, is_postgres_configured
from models import EmployeeSchema, ScheduleRunSchema, ShiftSchema, SkillSchema
import repository as repo
import queue_ops

logger = logging.getLogger(__name__)


def _get_current_user_email() -> str | None:
    """Get the current user's email from Databricks App headers (via Streamlit)."""
    try:
        import streamlit as st
        headers = st.context.headers
        # Databricks Apps set X-Forwarded-Email and X-Forwarded-User
        email = headers.get("X-Forwarded-Email") or headers.get("X-Forwarded-User")
        if email:
            return email
        # Fallback: try preferred-username
        return headers.get("X-Forwarded-Preferred-Username")
    except Exception:
        return None


class DbBackend:
    """Production backend backed by Lakebase Provisioned PostgreSQL."""

    def __init__(self):
        if is_postgres_configured():
            init_database()
            start_token_refresh()

    def _user_session(self):
        """Return a session_scope with the current user's email for RLS."""
        return session_scope(user_email=_get_current_user_email())

    # --- Skills ---
    def list_skills(self) -> list[SkillSchema]:
        with session_scope() as session:
            return repo.list_skills(session)

    def create_skill(self, name: str, description: str = "") -> SkillSchema:
        with session_scope() as session:
            return repo.create_skill(session, name, description)

    def delete_skill(self, skill_id: str):
        with session_scope() as session:
            repo.delete_skill(session, skill_id)

    # --- Employees (RLS-filtered by current user) ---
    def list_employees(self) -> list[EmployeeSchema]:
        with self._user_session() as session:
            return repo.list_employees(session)

    def get_employee(self, employee_id: str) -> EmployeeSchema | None:
        with self._user_session() as session:
            employees = repo.list_employees(session)
            return next((e for e in employees if e.id == employee_id), None)

    def create_employee(self, data: EmployeeSchema) -> EmployeeSchema:
        with self._user_session() as session:
            return repo.create_employee(session, data)

    def update_employee(self, employee_id: str, data: EmployeeSchema) -> EmployeeSchema | None:
        with self._user_session() as session:
            return repo.update_employee(session, employee_id, data)

    def delete_employee(self, employee_id: str):
        with self._user_session() as session:
            repo.delete_employee(session, employee_id)

    # --- Shifts ---
    def list_shifts(self) -> list[ShiftSchema]:
        with session_scope() as session:
            return repo.list_shifts(session)

    def get_shift(self, shift_id: str) -> ShiftSchema | None:
        with session_scope() as session:
            shifts = repo.list_shifts(session)
            return next((s for s in shifts if s.id == shift_id), None)

    def create_shift(self, data: ShiftSchema) -> ShiftSchema:
        with session_scope() as session:
            return repo.create_shift(session, data)

    def update_shift(self, shift_id: str, data: ShiftSchema) -> ShiftSchema | None:
        with session_scope() as session:
            shifts = repo.list_shifts(session)
            existing = next((s for s in shifts if s.id == shift_id), None)
            if not existing:
                return None
            repo.delete_shift(session, shift_id)
            data.id = shift_id
            return repo.create_shift(session, data)

    def delete_shift(self, shift_id: str):
        with session_scope() as session:
            repo.delete_shift(session, shift_id)

    # --- Schedule Runs ---
    def list_schedule_runs(self) -> list[ScheduleRunSchema]:
        with session_scope() as session:
            return repo.list_schedule_runs(session)

    def get_schedule_run(self, run_id: str) -> ScheduleRunSchema | None:
        with session_scope() as session:
            return repo.get_schedule_run(session, run_id)

    def save_schedule_run(self, run: ScheduleRunSchema):
        with session_scope() as session:
            repo.save_schedule_run(session, run)

    def delete_schedule_run(self, run_id: str):
        with session_scope() as session:
            repo.delete_schedule_run(session, run_id)

    # --- Solve Task Queue ---
    def _trigger_worker_job(self):
        """Trigger the solver worker Databricks Job so it picks up the new task."""
        job_id = os.environ.get("SOLVER_WORKER_JOB_ID")
        if not job_id:
            print("[SOLVER] SOLVER_WORKER_JOB_ID not set", flush=True)
            return
        try:
            from databricks.sdk import WorkspaceClient
            client = WorkspaceClient()
            host = client.config.host.rstrip("/")
            headers = client.config.authenticate()
            headers["Content-Type"] = "application/json"
            print(f"[SOLVER] Triggering job {job_id} via REST...", flush=True)
            import requests
            resp = requests.post(
                f"{host}/api/2.1/jobs/run-now",
                headers=headers,
                json={"job_id": int(job_id)},
                timeout=30,
            )
            resp.raise_for_status()
            run_id = resp.json().get("run_id")
            print(f"[SOLVER] Triggered job {job_id}, run_id={run_id}", flush=True)
        except Exception as e:
            print(f"[SOLVER] Failed to trigger job: {e}", flush=True)
            import traceback
            traceback.print_exc()

    def submit_solve_task(self, user_id: str, input_data: dict) -> str:
        with session_scope() as session:
            task_id = queue_ops.submit_task(session, user_id, input_data)
        self._trigger_worker_job()
        return task_id

    def poll_solve_task(self, task_id: str) -> dict | None:
        with session_scope() as session:
            return queue_ops.poll_task(session, task_id)
