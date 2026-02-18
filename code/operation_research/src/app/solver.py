"""Staff/shift scheduling optimizer using Google OR-Tools CP-SAT solver.

Constraints:
  1. Availability — employees only assigned to shifts during their available times
  2. Skill matching — employee must have all required skills for the shift
  3. No overlapping shifts per employee per day
  4. Max shifts per day per employee
  5. Max hours per week per employee
  6. Staff coverage — min/max staff required per shift

Objective: maximize total coverage + minimize unfairness across employees.
"""

import time as _time
from dataclasses import dataclass, field
from typing import Optional

from ortools.sat.python import cp_model

from models import EmployeeSchema, ShiftSchema


@dataclass
class SolverInput:
    employees: list[EmployeeSchema]
    shifts: list[ShiftSchema]
    max_time_seconds: int = 30
    fairness_weight: int = 10


@dataclass
class SolverOutput:
    status: str  # "optimal", "feasible", "infeasible", "error"
    assignments: list[tuple[str, str]] = field(default_factory=list)  # (employee_id, shift_id)
    solver_time_seconds: float = 0.0
    objective_value: Optional[float] = None
    stats: dict = field(default_factory=dict)


def _parse_time_minutes(t: str) -> int:
    """Convert 'HH:MM' to minutes since midnight."""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _shift_duration_hours(shift: ShiftSchema) -> int:
    """Shift duration in whole hours (rounded down)."""
    start = _parse_time_minutes(shift.start_time)
    end = _parse_time_minutes(shift.end_time)
    if end <= start:
        end += 24 * 60
    return (end - start) // 60


def _shifts_overlap(s1: ShiftSchema, s2: ShiftSchema) -> bool:
    """Check if two shifts on the same day have overlapping times."""
    a_start = _parse_time_minutes(s1.start_time)
    a_end = _parse_time_minutes(s1.end_time)
    b_start = _parse_time_minutes(s2.start_time)
    b_end = _parse_time_minutes(s2.end_time)
    if a_end <= a_start:
        a_end += 24 * 60
    if b_end <= b_start:
        b_end += 24 * 60
    return a_start < b_end and b_start < a_end


def _is_employee_available(employee: EmployeeSchema, shift: ShiftSchema) -> bool:
    """Check if employee has availability covering the shift."""
    shift_start = _parse_time_minutes(shift.start_time)
    shift_end = _parse_time_minutes(shift.end_time)
    if shift_end <= shift_start:
        shift_end += 24 * 60

    for avail in employee.availabilities:
        if avail.day_of_week != shift.day_of_week:
            continue
        avail_start = _parse_time_minutes(avail.start_time)
        avail_end = _parse_time_minutes(avail.end_time)
        if avail_end <= avail_start:
            avail_end += 24 * 60
        if avail_start <= shift_start and avail_end >= shift_end:
            return True
    return False


def _has_required_skills(employee: EmployeeSchema, shift: ShiftSchema) -> bool:
    """Check if employee has all skills required by the shift."""
    if not shift.required_skill_ids:
        return True
    emp_skills = set(employee.skill_ids)
    return all(s in emp_skills for s in shift.required_skill_ids)


def solve_schedule(input_data: SolverInput) -> SolverOutput:
    """Run the CP-SAT solver to produce an optimal staff schedule."""
    model = cp_model.CpModel()
    start_time = _time.time()

    employees = input_data.employees
    shifts = input_data.shifts

    if not employees or not shifts:
        return SolverOutput(status="error", stats={"message": "No employees or shifts provided"})

    # --- Decision variables: x[e_id, s_id] = 1 if employee e assigned to shift s ---
    x = {}
    for e in employees:
        for s in shifts:
            x[e.id, s.id] = model.new_bool_var(f"x_{e.id[:8]}_{s.id[:8]}")

    # --- Constraint 1: Availability ---
    for e in employees:
        for s in shifts:
            if not _is_employee_available(e, s):
                model.add(x[e.id, s.id] == 0)

    # --- Constraint 2: Skill matching ---
    for e in employees:
        for s in shifts:
            if not _has_required_skills(e, s):
                model.add(x[e.id, s.id] == 0)

    # --- Constraint 3: No overlapping shifts per employee per day ---
    shifts_by_day: dict[int, list[ShiftSchema]] = {}
    for s in shifts:
        shifts_by_day.setdefault(s.day_of_week, []).append(s)

    for e in employees:
        for day, day_shifts in shifts_by_day.items():
            for i, s1 in enumerate(day_shifts):
                for s2 in day_shifts[i + 1 :]:
                    if _shifts_overlap(s1, s2):
                        model.add(x[e.id, s1.id] + x[e.id, s2.id] <= 1)

    # --- Constraint 4: Max shifts per day ---
    for e in employees:
        for day, day_shifts in shifts_by_day.items():
            model.add(sum(x[e.id, s.id] for s in day_shifts) <= e.max_shifts_per_day)

    # --- Constraint 5: Max hours per week ---
    for e in employees:
        model.add(
            sum(x[e.id, s.id] * _shift_duration_hours(s) for s in shifts)
            <= e.max_hours_per_week
        )

    # --- Constraint 6: Staff coverage (min/max per shift) ---
    for s in shifts:
        total = sum(x[e.id, s.id] for e in employees)
        model.add(total >= s.min_staff)
        model.add(total <= s.max_staff)

    # --- Objective: maximize coverage + fairness ---
    shifts_per_employee = []
    for e in employees:
        count = model.new_int_var(0, len(shifts), f"count_{e.id[:8]}")
        model.add(count == sum(x[e.id, s.id] for s in shifts))
        shifts_per_employee.append(count)

    max_shifts = model.new_int_var(0, len(shifts), "max_shifts")
    min_shifts = model.new_int_var(0, len(shifts), "min_shifts")
    model.add_max_equality(max_shifts, shifts_per_employee)
    model.add_min_equality(min_shifts, shifts_per_employee)

    total_assigned = sum(x[e.id, s.id] for e in employees for s in shifts)
    fairness_penalty = max_shifts - min_shifts

    model.maximize(total_assigned * 100 - fairness_penalty * input_data.fairness_weight)

    # --- Solve ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = input_data.max_time_seconds
    status = solver.solve(model)
    elapsed = round(_time.time() - start_time, 2)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        assignments = [
            (e.id, s.id)
            for e in employees
            for s in shifts
            if solver.value(x[e.id, s.id]) == 1
        ]

        # Compute stats
        emp_counts = {}
        for e_id, _ in assignments:
            emp_counts[e_id] = emp_counts.get(e_id, 0) + 1

        shift_coverage = {}
        for _, s_id in assignments:
            shift_coverage[s_id] = shift_coverage.get(s_id, 0) + 1

        stats = {
            "total_assignments": len(assignments),
            "employees_used": len(emp_counts),
            "avg_shifts_per_employee": round(len(assignments) / max(len(emp_counts), 1), 1),
            "min_shifts_per_employee": min(emp_counts.values()) if emp_counts else 0,
            "max_shifts_per_employee": max(emp_counts.values()) if emp_counts else 0,
            "shifts_fully_covered": sum(
                1 for s in shifts if shift_coverage.get(s.id, 0) >= s.min_staff
            ),
            "total_shifts": len(shifts),
        }

        return SolverOutput(
            status="optimal" if status == cp_model.OPTIMAL else "feasible",
            assignments=assignments,
            solver_time_seconds=elapsed,
            objective_value=solver.objective_value,
            stats=stats,
        )
    else:
        return SolverOutput(
            status="infeasible",
            solver_time_seconds=elapsed,
            stats={"message": "No feasible solution found. Try relaxing constraints."},
        )
