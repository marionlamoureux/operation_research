"""Employee management page: CRUD + availability + skills."""

import streamlit as st
from models import AvailabilitySchema, DAY_NAMES, EmployeeSchema

st.set_page_config(page_title="Employees", page_icon="\U0001f465", layout="wide")
st.title("\U0001f465 Employee Management")

backend = st.session_state.get("backend")
if not backend:
    st.error("Backend not initialized. Go to the Home page first.")
    st.stop()

skills = backend.list_skills()
skill_map = {s.id: s.name for s in skills}
skill_names = [s.name for s in skills]

# ---- Skill management (expander) ----
with st.expander("Manage Skills", expanded=False):
    st.markdown("**Current Skills**")
    for skill in skills:
        c1, c2 = st.columns([4, 1])
        c1.write(f"**{skill.name}** — {skill.description or ''}")
        if c2.button("Delete", key=f"del_skill_{skill.id}"):
            backend.delete_skill(skill.id)
            st.rerun()

    st.markdown("**Add New Skill**")
    with st.form("add_skill_form"):
        new_name = st.text_input("Skill name")
        new_desc = st.text_input("Description (optional)")
        if st.form_submit_button("Add Skill") and new_name:
            backend.create_skill(new_name, new_desc)
            st.rerun()

st.divider()

# ---- Employee list ----
employees = backend.list_employees()

st.subheader(f"Employees ({len(employees)})")

for emp in employees:
    with st.expander(f"{emp.name} — {emp.max_hours_per_week}h/week — {len(emp.skill_ids)} skills"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Details**")
            new_name = st.text_input("Name", value=emp.name, key=f"name_{emp.id}")
            new_email = st.text_input("Email", value=emp.email or "", key=f"email_{emp.id}")
            new_max_hours = st.number_input(
                "Max hours/week", value=emp.max_hours_per_week, min_value=1, max_value=80, key=f"hours_{emp.id}"
            )
            new_max_shifts = st.number_input(
                "Max shifts/day", value=emp.max_shifts_per_day, min_value=1, max_value=3, key=f"mshifts_{emp.id}"
            )
            emp_skill_names = [skill_map[sid] for sid in emp.skill_ids if sid in skill_map]
            new_skill_names = st.multiselect(
                "Skills", options=skill_names, default=emp_skill_names, key=f"skills_{emp.id}"
            )

        with col2:
            st.markdown("**Availability**")
            avail_days = {a.day_of_week for a in emp.availabilities}
            new_avail_days = []
            for d in range(7):
                if st.checkbox(DAY_NAMES[d], value=d in avail_days, key=f"avail_{emp.id}_{d}"):
                    new_avail_days.append(d)

            avail_start = st.time_input(
                "Available from", value=None, key=f"avail_start_{emp.id}"
            )
            avail_end = st.time_input(
                "Available until", value=None, key=f"avail_end_{emp.id}"
            )

        bc1, bc2 = st.columns(2)
        if bc1.button("Save Changes", key=f"save_{emp.id}", type="primary"):
            new_skill_ids = [s.id for s in skills if s.name in new_skill_names]
            start_str = avail_start.strftime("%H:%M") if avail_start else "06:00"
            end_str = avail_end.strftime("%H:%M") if avail_end else "22:00"
            new_avails = [
                AvailabilitySchema(day_of_week=d, start_time=start_str, end_time=end_str)
                for d in new_avail_days
            ]
            updated = EmployeeSchema(
                id=emp.id,
                name=new_name,
                email=new_email if new_email else None,
                max_hours_per_week=new_max_hours,
                max_shifts_per_day=new_max_shifts,
                skill_ids=new_skill_ids,
                availabilities=new_avails,
            )
            backend.update_employee(emp.id, updated)
            st.success(f"Updated {new_name}")
            st.rerun()

        if bc2.button("Delete", key=f"delete_{emp.id}"):
            backend.delete_employee(emp.id)
            st.rerun()

st.divider()

# ---- Add new employee ----
st.subheader("Add New Employee")
with st.form("add_employee_form"):
    name = st.text_input("Name")
    email = st.text_input("Email (optional)")
    max_hours = st.number_input("Max hours/week", value=40, min_value=1, max_value=80)
    max_shifts = st.number_input("Max shifts/day", value=1, min_value=1, max_value=3)
    emp_skills = st.multiselect("Skills", options=skill_names)
    avail_checkboxes = st.multiselect("Available days", options=DAY_NAMES, default=DAY_NAMES[:5])

    if st.form_submit_button("Add Employee") and name:
        skill_ids = [s.id for s in skills if s.name in emp_skills]
        avails = [
            AvailabilitySchema(day_of_week=DAY_NAMES.index(d), start_time="06:00", end_time="22:00")
            for d in avail_checkboxes
        ]
        new_emp = EmployeeSchema(
            name=name,
            email=email if email else None,
            max_hours_per_week=max_hours,
            max_shifts_per_day=max_shifts,
            skill_ids=skill_ids,
            availabilities=avails,
        )
        backend.create_employee(new_emp)
        st.success(f"Added {name}")
        st.rerun()
