"""Staff & Shift Scheduler — Streamlit entry point and home dashboard."""

import streamlit as st
from backend import get_backend
from models import DAY_NAMES

st.set_page_config(page_title="Staff Scheduler", page_icon="\U0001f4c5", layout="wide")


@st.cache_resource
def init_backend():
    return get_backend()


backend = init_backend()
st.session_state.setdefault("backend", backend)

st.title("\U0001f4c5 Staff & Shift Scheduler")
st.markdown("Optimize staff scheduling with constraint programming (Google OR-Tools CP-SAT)")

st.divider()

# KPI cards
employees = backend.list_employees()
shifts = backend.list_shifts()
skills = backend.list_skills()
runs = backend.list_schedule_runs()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Employees", len(employees))
col2.metric("Shifts / week", len(shifts))
col3.metric("Skills", len(skills))
col4.metric("Schedule Runs", len(runs))

if runs:
    last_run = runs[-1]
    st.subheader("Latest Schedule Run")
    r1, r2, r3 = st.columns(3)
    r1.metric("Status", last_run.status.upper())
    r2.metric("Solver Time", f"{last_run.solver_time_seconds or 0:.1f}s")
    r3.metric("Assignments", len(last_run.assignments))

st.divider()
st.subheader("Quick Overview")

# Employee skills matrix
if employees and skills:
    st.markdown("**Employee Skills Matrix**")
    skill_map = {s.id: s.name for s in skills}
    rows = []
    for e in employees:
        row = {"Employee": e.name}
        for s in skills:
            row[s.name] = "\u2705" if s.id in e.skill_ids else ""
        rows.append(row)
    st.dataframe(rows, use_container_width=True, hide_index=True)

# Shift coverage summary
if shifts:
    st.markdown("**Weekly Shift Coverage Requirements**")
    coverage = {}
    for s in shifts:
        day = DAY_NAMES[s.day_of_week]
        coverage.setdefault(day, {"min_staff": 0, "max_staff": 0, "count": 0})
        coverage[day]["min_staff"] += s.min_staff
        coverage[day]["max_staff"] += s.max_staff
        coverage[day]["count"] += 1
    rows = [
        {"Day": day, "Shifts": v["count"], "Min Staff Needed": v["min_staff"], "Max Staff": v["max_staff"]}
        for day, v in coverage.items()
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
