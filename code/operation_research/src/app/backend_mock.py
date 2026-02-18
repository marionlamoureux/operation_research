"""In-memory mock backend with synthetic data for local development."""

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


def _id():
    return str(uuid.uuid4())


SKILLS = [
    SkillSchema(id=_id(), name="Cashier", description="Point-of-sale operation"),
    SkillSchema(id=_id(), name="Stocking", description="Shelf stocking and inventory"),
    SkillSchema(id=_id(), name="Customer Service", description="Help desk and returns"),
    SkillSchema(id=_id(), name="Management", description="Shift supervision"),
    SkillSchema(id=_id(), name="Cleaning", description="Facility maintenance"),
]


def _build_employees() -> list[EmployeeSchema]:
    names = [
        ("Alice Martin", "alice@example.com"),
        ("Bob Dupont", "bob@example.com"),
        ("Clara Moreau", "clara@example.com"),
        ("David Leroy", "david@example.com"),
        ("Emma Petit", "emma@example.com"),
        ("Frank Bernard", "frank@example.com"),
        ("Grace Thomas", "grace@example.com"),
        ("Hugo Robert", "hugo@example.com"),
    ]
    skill_assignments = [
        [0, 2],        # Alice: Cashier, Customer Service
        [1, 4],        # Bob: Stocking, Cleaning
        [0, 2, 3],     # Clara: Cashier, Customer Service, Management
        [1, 2],        # David: Stocking, Customer Service
        [0, 1],        # Emma: Cashier, Stocking
        [3, 4],        # Frank: Management, Cleaning
        [0, 2],        # Grace: Cashier, Customer Service
        [1, 3, 4],     # Hugo: Stocking, Management, Cleaning
    ]
    max_hours = [40, 35, 40, 30, 25, 40, 20, 35]
    # Weekday availability patterns
    avail_patterns = [
        list(range(5)),         # Alice: Mon-Fri
        list(range(6)),         # Bob: Mon-Sat
        list(range(5)),         # Clara: Mon-Fri
        [0, 1, 2, 3],          # David: Mon-Thu
        [2, 3, 4, 5],          # Emma: Wed-Sat
        list(range(7)),         # Frank: every day
        [0, 2, 4],             # Grace: Mon, Wed, Fri
        [1, 3, 5, 6],          # Hugo: Tue, Thu, Sat, Sun
    ]

    employees = []
    for i, (name, email) in enumerate(names):
        avails = [
            AvailabilitySchema(day_of_week=d, start_time="06:00", end_time="22:00")
            for d in avail_patterns[i]
        ]
        employees.append(
            EmployeeSchema(
                name=name,
                email=email,
                max_hours_per_week=max_hours[i],
                max_shifts_per_day=1,
                skill_ids=[SKILLS[s].id for s in skill_assignments[i]],
                availabilities=avails,
            )
        )
    return employees


def _build_shifts() -> list[ShiftSchema]:
    shift_templates = [
        ("Morning", "06:00", "14:00", 2, 4, [0]),       # needs Cashier
        ("Afternoon", "14:00", "22:00", 2, 4, [0]),      # needs Cashier
        ("Stocking AM", "06:00", "10:00", 1, 2, [1]),    # needs Stocking
        ("Manager", "08:00", "17:00", 1, 1, [3]),        # needs Management
        ("Cleaning PM", "18:00", "22:00", 1, 2, [4]),    # needs Cleaning
    ]
    shifts = []
    for day in range(7):
        for name, start, end, min_s, max_s, req_skills in shift_templates:
            shifts.append(
                ShiftSchema(
                    name=f"{name} ({DAY_NAMES[day][:3]})",
                    day_of_week=day,
                    start_time=start,
                    end_time=end,
                    min_staff=min_s,
                    max_staff=max_s,
                    required_skill_ids=[SKILLS[s].id for s in req_skills],
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
