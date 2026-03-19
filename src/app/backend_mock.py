"""In-memory mock backend with large-scale synthetic data for local development."""

import json
import random
import uuid
from datetime import time
from models import (
    AvailabilitySchema,
    DAY_NAMES,
    EmployeeSchema,
    ScheduleRunSchema,
    ShiftSchema,
    SkillSchema,
)
from solver import SolverInput, solve_schedule


def _id():
    return str(uuid.uuid4())


# --- 12 Skills ---
SKILLS = [
    SkillSchema(id=_id(), name="Cashier", description="Point-of-sale operation"),
    SkillSchema(id=_id(), name="Stocking", description="Shelf stocking and inventory"),
    SkillSchema(id=_id(), name="Customer Service", description="Help desk and returns"),
    SkillSchema(id=_id(), name="Management", description="Shift supervision"),
    SkillSchema(id=_id(), name="Cleaning", description="Facility maintenance"),
    SkillSchema(id=_id(), name="Bakery", description="In-store bakery preparation"),
    SkillSchema(id=_id(), name="Deli", description="Delicatessen counter"),
    SkillSchema(id=_id(), name="Pharmacy", description="Pharmacy assistance"),
    SkillSchema(id=_id(), name="Produce", description="Fresh produce handling"),
    SkillSchema(id=_id(), name="Security", description="Loss prevention and safety"),
    SkillSchema(id=_id(), name="Receiving", description="Goods receiving and dock"),
    SkillSchema(id=_id(), name="Electronics", description="Electronics department"),
]

SKILL_IDS = [s.id for s in SKILLS]

# Deterministic seed for reproducibility
_rng = random.Random(42)

# --- 80 Employees ---
_FIRST_NAMES = [
    "Alice", "Bob", "Clara", "David", "Emma", "Frank", "Grace", "Hugo",
    "Iris", "Jean", "Kate", "Liam", "Marie", "Nathan", "Olivia", "Paul",
    "Quinn", "Rose", "Simon", "Tara", "Ursula", "Victor", "Wendy", "Xavier",
    "Yvonne", "Zachary", "Amelia", "Bruno", "Chloe", "Daniel", "Elena", "Felix",
    "Gina", "Henri", "Ines", "Jules", "Karen", "Leon", "Mina", "Noel",
    "Ophelia", "Pierre", "Rita", "Samir", "Thea", "Ugo", "Vera", "Walid",
    "Xena", "Yann", "Zara", "Antoine", "Brigitte", "Cyril", "Diane", "Ethan",
    "Fanny", "Gaston", "Helene", "Igor", "Julie", "Kevin", "Laure", "Marc",
    "Nina", "Oscar", "Patricia", "Quentin", "Rebecca", "Stephane", "Tatiana",
    "Ulrich", "Valerie", "William", "Yasmine", "Arnaud", "Beatrice", "Charles",
    "Delphine", "Eric",
]

_LAST_NAMES = [
    "Martin", "Dupont", "Moreau", "Leroy", "Petit", "Bernard", "Thomas", "Robert",
    "Richard", "Durand", "Dubois", "Lambert", "Bonnet", "Fontaine", "Rousseau", "Blanc",
    "Girard", "Roux", "Clement", "Morel", "Nicolas", "Henry", "Garnier", "Chevalier",
    "Mercier", "Moulin", "Perrin", "Robin", "Rey", "Faure", "Andre", "Leclerc",
    "Lemoine", "Colin", "Bertrand", "Vidal", "Picard", "Gilles", "Renard", "Maillard",
    "Simon", "Laurent", "Michel", "Garcia", "David", "Noel", "Meyer", "Dumas",
    "Joly", "Gautier", "Roger", "Roche", "Roy", "Lefebvre", "Carpentier", "Masson",
    "Marchand", "Duval", "Denis", "Caron", "Brun", "Herve", "Pichon", "Breton",
    "Legrand", "Meunier", "Guerin", "Lacroix", "Sanchez", "Muller", "Leroux", "Louis",
    "Baron", "Morin", "Philippe", "Masse", "Pages", "Benoit", "Rolland", "Prevost",
]

# Availability pattern templates
_AVAIL_PATTERNS = [
    # Full-timers: Mon-Fri
    {"days": [0, 1, 2, 3, 4], "start": "06:00", "end": "22:00"},
    # Full-timers: Mon-Sat
    {"days": [0, 1, 2, 3, 4, 5], "start": "06:00", "end": "22:00"},
    # Full-timers: every day
    {"days": [0, 1, 2, 3, 4, 5, 6], "start": "06:00", "end": "22:00"},
    # Part-timers: Mon-Wed-Fri
    {"days": [0, 2, 4], "start": "06:00", "end": "22:00"},
    # Part-timers: Tue-Thu-Sat
    {"days": [1, 3, 5], "start": "06:00", "end": "22:00"},
    # Part-timers: Wed-Sun
    {"days": [2, 3, 4, 5, 6], "start": "06:00", "end": "22:00"},
    # Evening only: Mon-Fri
    {"days": [0, 1, 2, 3, 4], "start": "14:00", "end": "23:00"},
    # Morning only: Mon-Sat
    {"days": [0, 1, 2, 3, 4, 5], "start": "05:00", "end": "14:00"},
    # Weekend warriors: Fri-Sun
    {"days": [4, 5, 6], "start": "06:00", "end": "23:00"},
    # Four-day week: Mon-Thu
    {"days": [0, 1, 2, 3], "start": "06:00", "end": "22:00"},
]


def _build_employees() -> list[EmployeeSchema]:
    employees = []
    for i in range(80):
        first = _FIRST_NAMES[i % len(_FIRST_NAMES)]
        last = _LAST_NAMES[i % len(_LAST_NAMES)]
        # Avoid duplicate names
        name = f"{first} {last}" if i < 64 else f"{first} {last} {i - 63}"

        # Each employee gets 2-5 skills
        num_skills = _rng.randint(2, 5)
        skill_indices = _rng.sample(range(len(SKILLS)), num_skills)

        # Availability pattern
        pattern = _AVAIL_PATTERNS[i % len(_AVAIL_PATTERNS)]
        avails = [
            AvailabilitySchema(day_of_week=d, start_time=pattern["start"], end_time=pattern["end"])
            for d in pattern["days"]
        ]

        # Max hours: full-timers 35-40, part-timers 15-25
        is_part_time = len(pattern["days"]) <= 4
        max_hours = _rng.randint(15, 25) if is_part_time else _rng.randint(35, 40)
        min_hours = _rng.randint(4, 8) if is_part_time else _rng.randint(10, 16)

        # Max consecutive days: 3-6
        max_consec = _rng.randint(3, 6)

        # Holidays: ~30% of employees have 1-2 holiday days this week
        holiday_days = []
        if _rng.random() < 0.30:
            num_holidays = _rng.randint(1, 2)
            holiday_days = _rng.sample(pattern["days"], min(num_holidays, len(pattern["days"])))

        employees.append(
            EmployeeSchema(
                name=name,
                email=f"{first.lower()}.{last.lower()}{i}@example.com",
                max_hours_per_week=max_hours,
                min_hours_per_week=min_hours,
                max_shifts_per_day=_rng.choice([1, 1, 1, 2, 2]),  # mostly 1, some 2
                max_consecutive_days=max_consec,
                skill_ids=[SKILL_IDS[s] for s in skill_indices],
                availabilities=avails,
                holiday_days=holiday_days,
            )
        )
    return employees


def _build_shifts() -> list[ShiftSchema]:
    """Build a realistic shift roster: ~98 shifts per week (14 templates × 7 days)."""
    shift_templates = [
        # name, start, end, min_staff, max_staff, required_skill_indices, is_priority
        ("Morning Cashier", "08:00", "14:00", 3, 7, [0], False),
        ("Afternoon Cashier", "14:00", "20:00", 3, 7, [0], False),
        ("Morning Stocking", "06:00", "10:00", 2, 5, [1], False),
        ("Afternoon Stocking", "13:00", "17:00", 2, 4, [1], False),
        ("Customer Service AM", "08:00", "13:00", 2, 4, [2], False),
        ("Customer Service PM", "13:00", "20:00", 2, 5, [2], True),
        ("Manager Morning", "07:00", "15:00", 1, 2, [3], True),
        ("Cleaning Morning", "06:00", "10:00", 1, 3, [4], False),
        ("Bakery Morning", "06:00", "12:00", 2, 4, [5], True),
        ("Deli Morning", "07:00", "13:00", 2, 4, [6], False),
        ("Pharmacy AM", "08:00", "14:00", 1, 2, [7], True),
        ("Produce Morning", "06:00", "12:00", 2, 4, [8], False),
        ("Security Day", "06:00", "14:00", 1, 2, [9], True),
        ("Receiving AM", "06:00", "12:00", 2, 4, [10], False),
    ]

    shifts = []
    for day in range(7):
        for name, start, end, min_s, max_s, req_skills, is_prio in shift_templates:
            # Weekend: reduce min_staff slightly for non-priority shifts
            adj_min = max(1, min_s - 1) if day >= 5 and not is_prio else min_s
            shifts.append(
                ShiftSchema(
                    name=f"{name} ({DAY_NAMES[day][:3]})",
                    day_of_week=day,
                    start_time=start,
                    end_time=end,
                    min_staff=adj_min,
                    max_staff=max_s,
                    required_skill_ids=[SKILL_IDS[s] for s in req_skills],
                    is_priority=is_prio,
                )
            )
    return shifts


class MockBackend:
    """In-memory backend for local development without a database."""

    def __init__(self):
        self.skills: list[SkillSchema] = list(SKILLS)
        self.employees: list[EmployeeSchema] = _build_employees()
        self.shifts: list[ShiftSchema] = _build_shifts()
        self.schedule_runs: list[ScheduleRunSchema] = []

        # Assign shift preferences/avoidances now that shifts exist
        self._assign_preferences()

    def _assign_preferences(self):
        """Give ~50% of employees preferred and avoided shifts."""
        shift_ids = [s.id for s in self.shifts]
        for emp in self.employees:
            if _rng.random() < 0.50:
                emp.preferred_shift_ids = _rng.sample(shift_ids, min(5, len(shift_ids)))
            if _rng.random() < 0.40:
                emp.avoid_shift_ids = _rng.sample(shift_ids, min(3, len(shift_ids)))

    # --- Skills ---
    def list_skills(self) -> list[SkillSchema]:
        return self.skills

    def create_skill(self, name: str, description: str = "") -> SkillSchema:
        skill = SkillSchema(name=name, description=description)
        self.skills.append(skill)
        return skill

    def delete_skill(self, skill_id: str):
        self.skills = [s for s in self.skills if s.id != skill_id]

    # --- Employees ---
    def list_employees(self) -> list[EmployeeSchema]:
        return self.employees

    def get_employee(self, employee_id: str) -> EmployeeSchema | None:
        return next((e for e in self.employees if e.id == employee_id), None)

    def create_employee(self, data: EmployeeSchema) -> EmployeeSchema:
        self.employees.append(data)
        return data

    def update_employee(self, employee_id: str, data: EmployeeSchema) -> EmployeeSchema | None:
        for i, e in enumerate(self.employees):
            if e.id == employee_id:
                data.id = employee_id
                self.employees[i] = data
                return data
        return None

    def delete_employee(self, employee_id: str):
        self.employees = [e for e in self.employees if e.id != employee_id]

    # --- Shifts ---
    def list_shifts(self) -> list[ShiftSchema]:
        return self.shifts

    def get_shift(self, shift_id: str) -> ShiftSchema | None:
        return next((s for s in self.shifts if s.id == shift_id), None)

    def create_shift(self, data: ShiftSchema) -> ShiftSchema:
        self.shifts.append(data)
        return data

    def update_shift(self, shift_id: str, data: ShiftSchema) -> ShiftSchema | None:
        for i, s in enumerate(self.shifts):
            if s.id == shift_id:
                data.id = shift_id
                self.shifts[i] = data
                return data
        return None

    def delete_shift(self, shift_id: str):
        self.shifts = [s for s in self.shifts if s.id != shift_id]

    # --- Schedule runs ---
    def list_schedule_runs(self) -> list[ScheduleRunSchema]:
        return self.schedule_runs

    def get_schedule_run(self, run_id: str) -> ScheduleRunSchema | None:
        return next((r for r in self.schedule_runs if r.id == run_id), None)

    def save_schedule_run(self, run: ScheduleRunSchema):
        existing = next((i for i, r in enumerate(self.schedule_runs) if r.id == run.id), None)
        if existing is not None:
            self.schedule_runs[existing] = run
        else:
            self.schedule_runs.append(run)

    def delete_schedule_run(self, run_id: str):
        self.schedule_runs = [r for r in self.schedule_runs if r.id != run_id]

    # --- Solve Task Queue (mock: runs synchronously) ---
    def submit_solve_task(self, user_id: str, input_data: dict) -> str:
        task_id = str(uuid.uuid4())
        employees = [EmployeeSchema(**e) for e in input_data["employees"]]
        shifts = [ShiftSchema(**s) for s in input_data["shifts"]]
        result = solve_schedule(SolverInput(
            employees=employees, shifts=shifts,
            max_time_seconds=input_data.get("max_time_seconds", 10),
            fairness_weight=input_data.get("fairness_weight", 10),
        ))
        self._mock_tasks = getattr(self, "_mock_tasks", {})
        self._mock_tasks[task_id] = {
            "status": "COMPLETED",
            "output_json": json.dumps({
                "status": result.status, "assignments": result.assignments,
                "solver_time_seconds": result.solver_time_seconds,
                "objective_value": result.objective_value, "stats": result.stats,
                "run_name": input_data.get("run_name", ""),
                "week_start_date": input_data.get("week_start_date", ""),
            }),
            "error": None, "started_at": None, "finished_at": None,
        }
        return task_id

    def poll_solve_task(self, task_id: str) -> dict | None:
        return getattr(self, "_mock_tasks", {}).get(task_id)
