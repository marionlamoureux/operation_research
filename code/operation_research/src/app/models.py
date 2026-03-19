"""Data models: SQLAlchemy ORM for Lakebase PostgreSQL + Pydantic schemas for validation."""

import enum
import uuid
from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


employee_skills = Table(
    "employee_skills",
    Base.metadata,
    Column("employee_id", UUID(as_uuid=True), ForeignKey("employees.id"), primary_key=True),
    Column("skill_id", UUID(as_uuid=True), ForeignKey("skills.id"), primary_key=True),
)

shift_required_skills = Table(
    "shift_required_skills",
    Base.metadata,
    Column("shift_id", UUID(as_uuid=True), ForeignKey("shifts.id"), primary_key=True),
    Column("skill_id", UUID(as_uuid=True), ForeignKey("skills.id"), primary_key=True),
)


class DayOfWeek(enum.IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    max_hours_per_week: Mapped[int] = mapped_column(Integer, default=40)
    min_hours_per_week: Mapped[int] = mapped_column(Integer, default=0)
    max_shifts_per_day: Mapped[int] = mapped_column(Integer, default=1)
    max_consecutive_days: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    holiday_days_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of day indices
    preferred_shift_ids_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    avoid_shift_ids_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    skills = relationship("Skill", secondary=employee_skills, backref="employees")
    availabilities = relationship("EmployeeAvailability", back_populates="employee", cascade="all, delete-orphan")


class EmployeeAvailability(Base):
    __tablename__ = "employee_availability"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    employee = relationship("Employee", back_populates="availabilities")


class Shift(Base):
    __tablename__ = "shifts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    min_staff: Mapped[int] = mapped_column(Integer, default=1)
    max_staff: Mapped[int] = mapped_column(Integer, default=5)
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    required_skills = relationship("Skill", secondary=shift_required_skills)


class ScheduleRun(Base):
    __tablename__ = "schedule_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    week_start_date: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    solver_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    objective_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignments = relationship("ScheduleAssignment", back_populates="schedule_run", cascade="all, delete-orphan")


class ScheduleAssignment(Base):
    __tablename__ = "schedule_assignments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schedule_runs.id"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    shift_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=False)

    schedule_run = relationship("ScheduleRun", back_populates="assignments")
    employee = relationship("Employee")
    shift = relationship("Shift")


class SolveTask(Base):
    """Queue table for async solver tasks. Workers claim PENDING rows."""
    __tablename__ = "solve_tasks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    output_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SkillSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None


class AvailabilitySchema(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: str = "08:00"
    end_time: str = "18:00"


class EmployeeSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: Optional[str] = None
    max_hours_per_week: int = 40
    min_hours_per_week: int = 0
    max_shifts_per_day: int = 1
    max_consecutive_days: int = 5
    is_active: bool = True
    skill_ids: list[str] = Field(default_factory=list)
    availabilities: list[AvailabilitySchema] = Field(default_factory=list)
    holiday_days: list[int] = Field(default_factory=list)  # day_of_week indices on holiday
    preferred_shift_ids: list[str] = Field(default_factory=list)  # preferred shifts (soft)
    avoid_shift_ids: list[str] = Field(default_factory=list)  # shifts to avoid (soft)


class ShiftSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    day_of_week: int = Field(ge=0, le=6)
    start_time: str = "08:00"
    end_time: str = "16:00"
    min_staff: int = 1
    max_staff: int = 5
    required_skill_ids: list[str] = Field(default_factory=list)
    is_priority: bool = False  # priority shifts get bonus in objective


class ScheduleRunSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    week_start_date: str = ""
    status: str = "pending"
    solver_time_seconds: Optional[float] = None
    objective_value: Optional[float] = None
    assignments: list[tuple[str, str]] = Field(default_factory=list)  # (employee_id, shift_id)
