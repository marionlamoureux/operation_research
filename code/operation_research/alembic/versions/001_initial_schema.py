"""Initial schema for shift scheduler.

Revision ID: 001
Revises:
Create Date: 2026-02-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
    )

    op.create_table(
        "employees",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("max_hours_per_week", sa.Integer, default=40),
        sa.Column("max_shifts_per_day", sa.Integer, default=1),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "employee_skills",
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.id"), primary_key=True),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.id"), primary_key=True),
    )

    op.create_table(
        "employee_availability",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("day_of_week", sa.Integer, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
    )

    op.create_table(
        "shifts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("day_of_week", sa.Integer, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("min_staff", sa.Integer, default=1),
        sa.Column("max_staff", sa.Integer, default=5),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "shift_required_skills",
        sa.Column("shift_id", UUID(as_uuid=True), sa.ForeignKey("shifts.id"), primary_key=True),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.id"), primary_key=True),
    )

    op.create_table(
        "schedule_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("week_start_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("solver_time_seconds", sa.Float, nullable=True),
        sa.Column("objective_value", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "schedule_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("schedule_run_id", UUID(as_uuid=True), sa.ForeignKey("schedule_runs.id"), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("shift_id", UUID(as_uuid=True), sa.ForeignKey("shifts.id"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("schedule_assignments")
    op.drop_table("schedule_runs")
    op.drop_table("shift_required_skills")
    op.drop_table("shifts")
    op.drop_table("employee_availability")
    op.drop_table("employee_skills")
    op.drop_table("employees")
    op.drop_table("skills")
