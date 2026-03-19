"""CRUD operations against Lakebase PostgreSQL using SQLAlchemy."""

import json
import uuid
from datetime import time

from sqlalchemy.orm import Session, joinedload

from models import (
    Employee,
    EmployeeAvailability,
    EmployeeSchema,
    AvailabilitySchema,
    ScheduleAssignment,
    ScheduleRun,
    ScheduleRunSchema,
    Shift,
    ShiftSchema,
    Skill,
    SkillSchema,
    employee_skills,
    shift_required_skills,
)


def _parse_time(t: str) -> time:
    parts = t.split(":")
    return time(int(parts[0]), int(parts[1]))


# --- Skills ---

def list_skills(session: Session) -> list[SkillSchema]:
    rows = session.query(Skill).order_by(Skill.name).all()
    return [SkillSchema(id=str(r.id), name=r.name, description=r.description) for r in rows]


def create_skill(session: Session, name: str, description: str = "") -> SkillSchema:
    skill = Skill(name=name, description=description or None)
    session.add(skill)
    session.flush()
    return SkillSchema(id=str(skill.id), name=skill.name, description=skill.description)


def delete_skill(session: Session, skill_id: str):
    session.query(Skill).filter(Skill.id == uuid.UUID(skill_id)).delete()


# --- Employees ---

def list_employees(session: Session) -> list[EmployeeSchema]:
    rows = (
        session.query(Employee)
        .options(joinedload(Employee.skills), joinedload(Employee.availabilities))
        .filter(Employee.is_active == True)
        .order_by(Employee.name)
        .all()
    )
    result = []
    for e in rows:
        result.append(EmployeeSchema(
            id=str(e.id),
            name=e.name,
            email=e.email,
            max_hours_per_week=e.max_hours_per_week,
            min_hours_per_week=e.min_hours_per_week,
            max_shifts_per_day=e.max_shifts_per_day,
            max_consecutive_days=e.max_consecutive_days,
            is_active=e.is_active,
            skill_ids=[str(s.id) for s in e.skills],
            availabilities=[
                AvailabilitySchema(
                    day_of_week=a.day_of_week,
                    start_time=a.start_time.strftime("%H:%M"),
                    end_time=a.end_time.strftime("%H:%M"),
                )
                for a in e.availabilities
            ],
            holiday_days=json.loads(e.holiday_days_json) if e.holiday_days_json else [],
            preferred_shift_ids=json.loads(e.preferred_shift_ids_json) if e.preferred_shift_ids_json else [],
            avoid_shift_ids=json.loads(e.avoid_shift_ids_json) if e.avoid_shift_ids_json else [],
        ))
    return result


def create_employee(session: Session, data: EmployeeSchema) -> EmployeeSchema:
    emp = Employee(
        name=data.name,
        email=data.email,
        max_hours_per_week=data.max_hours_per_week,
        min_hours_per_week=data.min_hours_per_week,
        max_shifts_per_day=data.max_shifts_per_day,
        max_consecutive_days=data.max_consecutive_days,
        holiday_days_json=json.dumps(data.holiday_days) if data.holiday_days else None,
        preferred_shift_ids_json=json.dumps(data.preferred_shift_ids) if data.preferred_shift_ids else None,
        avoid_shift_ids_json=json.dumps(data.avoid_shift_ids) if data.avoid_shift_ids else None,
    )
    if data.skill_ids:
        skills = session.query(Skill).filter(Skill.id.in_([uuid.UUID(s) for s in data.skill_ids])).all()
        emp.skills = skills
    session.add(emp)
    session.flush()

    for a in data.availabilities:
        avail = EmployeeAvailability(
            employee_id=emp.id,
            day_of_week=a.day_of_week,
            start_time=_parse_time(a.start_time),
            end_time=_parse_time(a.end_time),
        )
        session.add(avail)

    data.id = str(emp.id)
    return data


def update_employee(session: Session, employee_id: str, data: EmployeeSchema) -> EmployeeSchema | None:
    emp = session.query(Employee).options(
        joinedload(Employee.skills), joinedload(Employee.availabilities)
    ).filter(Employee.id == uuid.UUID(employee_id)).first()
    if not emp:
        return None

    emp.name = data.name
    emp.email = data.email
    emp.max_hours_per_week = data.max_hours_per_week
    emp.min_hours_per_week = data.min_hours_per_week
    emp.max_shifts_per_day = data.max_shifts_per_day
    emp.max_consecutive_days = data.max_consecutive_days
    emp.holiday_days_json = json.dumps(data.holiday_days) if data.holiday_days else None
    emp.preferred_shift_ids_json = json.dumps(data.preferred_shift_ids) if data.preferred_shift_ids else None
    emp.avoid_shift_ids_json = json.dumps(data.avoid_shift_ids) if data.avoid_shift_ids else None

    if data.skill_ids:
        skills = session.query(Skill).filter(Skill.id.in_([uuid.UUID(s) for s in data.skill_ids])).all()
        emp.skills = skills
    else:
        emp.skills = []

    # Replace availabilities
    session.query(EmployeeAvailability).filter(
        EmployeeAvailability.employee_id == uuid.UUID(employee_id)
    ).delete()
    for a in data.availabilities:
        avail = EmployeeAvailability(
            employee_id=emp.id,
            day_of_week=a.day_of_week,
            start_time=_parse_time(a.start_time),
            end_time=_parse_time(a.end_time),
        )
        session.add(avail)

    data.id = employee_id
    return data


def delete_employee(session: Session, employee_id: str):
    session.query(Employee).filter(Employee.id == uuid.UUID(employee_id)).delete()


# --- Shifts ---

def list_shifts(session: Session) -> list[ShiftSchema]:
    rows = (
        session.query(Shift)
        .options(joinedload(Shift.required_skills))
        .order_by(Shift.day_of_week, Shift.start_time)
        .all()
    )
    return [
        ShiftSchema(
            id=str(s.id),
            name=s.name,
            day_of_week=s.day_of_week,
            start_time=s.start_time.strftime("%H:%M"),
            end_time=s.end_time.strftime("%H:%M"),
            min_staff=s.min_staff,
            max_staff=s.max_staff,
            required_skill_ids=[str(sk.id) for sk in s.required_skills],
            is_priority=s.is_priority,
        )
        for s in rows
    ]


def create_shift(session: Session, data: ShiftSchema) -> ShiftSchema:
    shift = Shift(
        name=data.name,
        day_of_week=data.day_of_week,
        start_time=_parse_time(data.start_time),
        end_time=_parse_time(data.end_time),
        min_staff=data.min_staff,
        max_staff=data.max_staff,
        is_priority=data.is_priority,
    )
    if data.required_skill_ids:
        skills = session.query(Skill).filter(Skill.id.in_([uuid.UUID(s) for s in data.required_skill_ids])).all()
        shift.required_skills = skills
    session.add(shift)
    session.flush()
    data.id = str(shift.id)
    return data


def delete_shift(session: Session, shift_id: str):
    session.query(Shift).filter(Shift.id == uuid.UUID(shift_id)).delete()


# --- Schedule Runs ---

def list_schedule_runs(session: Session) -> list[ScheduleRunSchema]:
    rows = (
        session.query(ScheduleRun)
        .options(joinedload(ScheduleRun.assignments))
        .order_by(ScheduleRun.created_at)
        .all()
    )
    return [
        ScheduleRunSchema(
            id=str(r.id),
            name=r.name,
            week_start_date=r.week_start_date.isoformat(),
            status=r.status,
            solver_time_seconds=r.solver_time_seconds,
            objective_value=r.objective_value,
            assignments=[(str(a.employee_id), str(a.shift_id)) for a in r.assignments],
        )
        for r in rows
    ]


def get_schedule_run(session: Session, run_id: str) -> ScheduleRunSchema | None:
    r = (
        session.query(ScheduleRun)
        .options(joinedload(ScheduleRun.assignments))
        .filter(ScheduleRun.id == uuid.UUID(run_id))
        .first()
    )
    if not r:
        return None
    return ScheduleRunSchema(
        id=str(r.id),
        name=r.name,
        week_start_date=r.week_start_date.isoformat(),
        status=r.status,
        solver_time_seconds=r.solver_time_seconds,
        objective_value=r.objective_value,
        assignments=[(str(a.employee_id), str(a.shift_id)) for a in r.assignments],
    )


def save_schedule_run(session: Session, run: ScheduleRunSchema):
    from datetime import date as date_type
    db_run = ScheduleRun(
        id=uuid.UUID(run.id),
        name=run.name,
        week_start_date=date_type.fromisoformat(run.week_start_date),
        status=run.status,
        solver_time_seconds=run.solver_time_seconds,
        objective_value=run.objective_value,
    )
    session.add(db_run)
    session.flush()

    for e_id, s_id in run.assignments:
        assignment = ScheduleAssignment(
            schedule_run_id=db_run.id,
            employee_id=uuid.UUID(e_id),
            shift_id=uuid.UUID(s_id),
        )
        session.add(assignment)


def delete_schedule_run(session: Session, run_id: str):
    session.query(ScheduleRun).filter(ScheduleRun.id == uuid.UUID(run_id)).delete()
