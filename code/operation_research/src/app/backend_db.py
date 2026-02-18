"""Real backend using Lakebase PostgreSQL via SQLAlchemy."""

from db import init_database, session_scope, start_token_refresh, is_postgres_configured
from models import EmployeeSchema, ScheduleRunSchema, ShiftSchema, SkillSchema
import repository as repo


class DbBackend:
    """Production backend backed by Lakebase Provisioned PostgreSQL."""

    def __init__(self):
        if is_postgres_configured():
            init_database()
            start_token_refresh()

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

    # --- Employees ---
    def list_employees(self) -> list[EmployeeSchema]:
        with session_scope() as session:
            return repo.list_employees(session)

    def get_employee(self, employee_id: str) -> EmployeeSchema | None:
        with session_scope() as session:
            employees = repo.list_employees(session)
            return next((e for e in employees if e.id == employee_id), None)

    def create_employee(self, data: EmployeeSchema) -> EmployeeSchema:
        with session_scope() as session:
            return repo.create_employee(session, data)

    def update_employee(self, employee_id: str, data: EmployeeSchema) -> EmployeeSchema | None:
        with session_scope() as session:
            return repo.update_employee(session, employee_id, data)

    def delete_employee(self, employee_id: str):
        with session_scope() as session:
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
