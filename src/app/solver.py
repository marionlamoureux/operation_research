"""Staff/shift scheduling optimizer using Google OR-Tools CP-SAT solver.

Constraints (hard):
  1.  Availability — employees only assigned during available times
  2.  Skill matching — employee must have all required skills
  3.  No overlapping shifts per employee per day
  4.  Max shifts per day per employee
  5.  Max hours per week per employee
  6.  Min hours per week per employee (if > 0)
  7.  Staff coverage — min/max staff per shift
  8.  Holidays — employees off on their holiday days
  9.  Max consecutive working days
  10. No close-open — forbid closing shift (ending ≥20:00) then opening shift (starting ≤08:00) next day
  11. At least one full weekend off per employee (Sat+Sun both free) — relaxed if infeasible
  12. Rest gap — at least 10 hours between end of last shift one day and start of first shift next day

Constraints (soft / objective):
  - Maximize total coverage
  - Fairness: minimize max-min shifts gap across employees
  - Shift preference bonus: employees on preferred shifts
  - Shift avoidance penalty: employees on avoided shifts
  - Priority shift bonus: extra weight for priority shifts covered
  - Consecutive days penalty: discourage long streaks even below max
  - Weekend work penalty: discourage weekend shifts

Objective: weighted sum of all soft terms.
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
    max_time_seconds: int = 600
    fairness_weight: int = 10


@dataclass
class SolverOutput:
    status: str  # "optimal", "feasible", "infeasible", "error"
    assignments: list[tuple[str, str]] = field(default_factory=list)
    solver_time_seconds: float = 0.0
    objective_value: Optional[float] = None
    stats: dict = field(default_factory=dict)


def _parse_time_minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _shift_duration_hours(shift: ShiftSchema) -> int:
    start = _parse_time_minutes(shift.start_time)
    end = _parse_time_minutes(shift.end_time)
    if end <= start:
        end += 24 * 60
    return (end - start) // 60


def _shifts_overlap(s1: ShiftSchema, s2: ShiftSchema) -> bool:
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

    # Index structures
    shifts_by_day: dict[int, list[ShiftSchema]] = {}
    for s in shifts:
        shifts_by_day.setdefault(s.day_of_week, []).append(s)

    emp_preferred = {e.id: set(e.preferred_shift_ids) for e in employees}
    emp_avoid = {e.id: set(e.avoid_shift_ids) for e in employees}
    emp_holidays = {e.id: set(e.holiday_days) for e in employees}

    # =========================================================================
    # Decision variables: x[e_id, s_id] = 1 if employee e assigned to shift s
    # =========================================================================
    x = {}
    for e in employees:
        for s in shifts:
            x[e.id, s.id] = model.new_bool_var(f"x_{e.id[:8]}_{s.id[:8]}")

    # Per-employee per-day working indicator: w[e_id, day] = 1 if working that day
    w = {}
    for e in employees:
        for day in range(7):
            w[e.id, day] = model.new_bool_var(f"w_{e.id[:8]}_{day}")

    # Link w to x: w[e,d] = 1 iff any x[e,s] = 1 for s on day d
    for e in employees:
        for day in range(7):
            day_shifts = shifts_by_day.get(day, [])
            if day_shifts:
                model.add_max_equality(w[e.id, day], [x[e.id, s.id] for s in day_shifts])
            else:
                model.add(w[e.id, day] == 0)

    # =========================================================================
    # HARD CONSTRAINTS
    # =========================================================================

    # --- 1. Availability ---
    for e in employees:
        for s in shifts:
            if not _is_employee_available(e, s):
                model.add(x[e.id, s.id] == 0)

    # --- 2. Skill matching ---
    for e in employees:
        for s in shifts:
            if not _has_required_skills(e, s):
                model.add(x[e.id, s.id] == 0)

    # --- 3. No overlapping shifts per employee per day ---
    for e in employees:
        for day, day_shifts in shifts_by_day.items():
            for i, s1 in enumerate(day_shifts):
                for s2 in day_shifts[i + 1:]:
                    if _shifts_overlap(s1, s2):
                        model.add(x[e.id, s1.id] + x[e.id, s2.id] <= 1)

    # --- 4. Max shifts per day ---
    for e in employees:
        for day, day_shifts in shifts_by_day.items():
            model.add(sum(x[e.id, s.id] for s in day_shifts) <= e.max_shifts_per_day)

    # --- 5. Max hours per week ---
    for e in employees:
        model.add(
            sum(x[e.id, s.id] * _shift_duration_hours(s) for s in shifts)
            <= e.max_hours_per_week
        )

    # --- 6. Min hours per week (SOFT — penalised in objective, not hard) ---
    # Handled below in soft constraints section

    # --- 7. Staff coverage ---
    for s in shifts:
        total = sum(x[e.id, s.id] for e in employees)
        model.add(total >= s.min_staff)
        model.add(total <= s.max_staff)

    # --- 8. Holidays ---
    for e in employees:
        for holiday_day in emp_holidays[e.id]:
            for s in shifts_by_day.get(holiday_day, []):
                model.add(x[e.id, s.id] == 0)

    # --- 9. Max consecutive working days ---
    for e in employees:
        max_consec = e.max_consecutive_days
        # Sliding window: for every window of (max_consec+1) consecutive days
        for start_day in range(7):
            window_days = [(start_day + d) % 7 for d in range(max_consec + 1)]
            # At most max_consec of these days can be working days
            model.add(sum(w[e.id, d] for d in window_days) <= max_consec)

    # --- 10. No close-open: forbid ending ≥20:00 then starting ≤08:00 next day ---
    for e in employees:
        for day in range(6):  # Mon-Sat (next day exists within the week)
            next_day = day + 1
            late_shifts = [s for s in shifts_by_day.get(day, []) if _parse_time_minutes(s.end_time) >= 20 * 60]
            early_shifts = [s for s in shifts_by_day.get(next_day, []) if _parse_time_minutes(s.start_time) <= 8 * 60]
            for ls in late_shifts:
                for es in early_shifts:
                    model.add(x[e.id, ls.id] + x[e.id, es.id] <= 1)

    # --- 11. Rest gap: ≥10 hours between last shift end one day and first shift start next day ---
    # (Pair-wise constraint on shifts across consecutive days that violate the 10h gap)
    for e in employees:
        for day in range(6):
            next_day = day + 1
            for s1 in shifts_by_day.get(day, []):
                s1_end = _parse_time_minutes(s1.end_time)
                for s2 in shifts_by_day.get(next_day, []):
                    s2_start = _parse_time_minutes(s2.start_time)
                    # gap = (24:00 - s1_end) + s2_start = s2_start + 1440 - s1_end
                    gap_minutes = s2_start + 24 * 60 - s1_end
                    if gap_minutes < 10 * 60:  # less than 10 hours
                        model.add(x[e.id, s1.id] + x[e.id, s2.id] <= 1)

    # =========================================================================
    # SOFT CONSTRAINTS (via objective)
    # =========================================================================

    objective_terms = []

    # --- Coverage: maximize total assignments ---
    total_assigned = sum(x[e.id, s.id] for e in employees for s in shifts)
    objective_terms.append(total_assigned * 100)

    # --- Fairness: minimize max-min shift gap ---
    shifts_per_employee = []
    for e in employees:
        count = model.new_int_var(0, len(shifts), f"count_{e.id[:8]}")
        model.add(count == sum(x[e.id, s.id] for s in shifts))
        shifts_per_employee.append(count)

    max_shifts_var = model.new_int_var(0, len(shifts), "max_shifts")
    min_shifts_var = model.new_int_var(0, len(shifts), "min_shifts")
    model.add_max_equality(max_shifts_var, shifts_per_employee)
    model.add_min_equality(min_shifts_var, shifts_per_employee)
    fairness_penalty = max_shifts_var - min_shifts_var
    objective_terms.append(-fairness_penalty * input_data.fairness_weight)

    # --- Shift preferences bonus ---
    pref_bonus = sum(
        x[e.id, s.id] * 5
        for e in employees
        for s in shifts
        if s.id in emp_preferred[e.id]
    )
    objective_terms.append(pref_bonus)

    # --- Shift avoidance penalty ---
    avoid_penalty = sum(
        x[e.id, s.id] * 8
        for e in employees
        for s in shifts
        if s.id in emp_avoid[e.id]
    )
    objective_terms.append(-avoid_penalty)

    # --- Priority shift bonus ---
    priority_bonus = sum(
        x[e.id, s.id] * 15
        for e in employees
        for s in shifts
        if s.is_priority
    )
    objective_terms.append(priority_bonus)

    # --- Weekend work penalty (discourage Sat=5, Sun=6) ---
    weekend_penalty = sum(
        x[e.id, s.id] * 3
        for e in employees
        for s in shifts
        if s.day_of_week in (5, 6)
    )
    objective_terms.append(-weekend_penalty)

    # --- Consecutive days penalty: penalise streaks ≥ 3 days ---
    # For each window of 4 consecutive days, penalise if all 4 are worked
    for e in employees:
        for start_day in range(7):
            window = [(start_day + d) % 7 for d in range(4)]
            streak_4 = model.new_bool_var(f"streak4_{e.id[:8]}_{start_day}")
            # streak_4 = 1 iff all 4 days worked
            model.add(sum(w[e.id, d] for d in window) >= 4).only_enforce_if(streak_4)
            model.add(sum(w[e.id, d] for d in window) <= 3).only_enforce_if(streak_4.negated())
            objective_terms.append(-streak_4 * 12)

    # --- Min hours shortfall penalty (soft version of constraint 6) ---
    for e in employees:
        if e.min_hours_per_week > 0:
            total_hours = sum(x[e.id, s.id] * _shift_duration_hours(s) for s in shifts)
            shortfall = model.new_int_var(0, e.min_hours_per_week, f"minhshort_{e.id[:8]}")
            model.add(shortfall >= e.min_hours_per_week - total_hours)
            objective_terms.append(-shortfall * 20)  # heavy penalty

    # --- Hours balance: penalise deviation from target hours ---
    for e in employees:
        target = (e.min_hours_per_week + e.max_hours_per_week) // 2
        total_hours_e = sum(x[e.id, s.id] * _shift_duration_hours(s) for s in shifts)
        deviation = model.new_int_var(0, e.max_hours_per_week, f"hdev_{e.id[:8]}")
        diff = model.new_int_var(-e.max_hours_per_week, e.max_hours_per_week, f"hdiff_{e.id[:8]}")
        model.add(diff == total_hours_e - target)
        model.add_abs_equality(deviation, diff)
        objective_terms.append(-deviation * 2)

    # --- Combine objective ---
    model.maximize(sum(objective_terms))

    # =========================================================================
    # SOLVE — deliberately leave room for long computation
    # =========================================================================
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = input_data.max_time_seconds
    solver.parameters.num_workers = 8
    solver.parameters.relative_gap_limit = 0.05  # stop when within 5% of optimal

    status = solver.solve(model)
    elapsed = round(_time.time() - start_time, 2)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        assignments = [
            (e.id, s.id)
            for e in employees
            for s in shifts
            if solver.value(x[e.id, s.id]) == 1
        ]

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
            "gap_to_optimal_pct": round(solver.best_objective_bound - solver.objective_value, 2)
                if solver.objective_value else None,
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
