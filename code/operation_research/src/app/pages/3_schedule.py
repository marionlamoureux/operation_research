"""Schedule generation page: run the OR-Tools solver, view and export results."""

import io
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from models import DAY_NAMES, ScheduleRunSchema
from solver import SolverInput, solve_schedule

st.set_page_config(page_title="Schedule", page_icon="\U0001f4ca", layout="wide")
st.title("\U0001f4ca Schedule Generator")

backend = st.session_state.get("backend")
if not backend:
    st.error("Backend not initialized. Go to the Home page first.")
    st.stop()

employees = backend.list_employees()
shifts = backend.list_shifts()
skills = backend.list_skills()
skill_map = {s.id: s.name for s in skills}
emp_map = {e.id: e for e in employees}
shift_map = {s.id: s for s in shifts}

# ---- Solver parameters ----
st.subheader("Optimization Parameters")
col1, col2, col3 = st.columns(3)
week_start = col1.date_input("Week starting", value=date.today() - timedelta(days=date.today().weekday()))
max_time = col2.number_input("Max solver time (seconds)", value=30, min_value=5, max_value=300)
fairness_weight = col3.slider("Fairness weight", min_value=0, max_value=100, value=10,
                              help="Higher = more balanced distribution, lower = maximize coverage")

run_name = st.text_input("Schedule run name", value=f"Week of {week_start.isoformat()}")

# ---- Run solver ----
if st.button("Run Optimizer", type="primary", disabled=not employees or not shifts):
    with st.spinner("Solving schedule optimization..."):
        solver_input = SolverInput(
            employees=employees,
            shifts=shifts,
            max_time_seconds=max_time,
            fairness_weight=fairness_weight,
        )
        result = solve_schedule(solver_input)

    # Save run
    run = ScheduleRunSchema(
        name=run_name,
        week_start_date=week_start.isoformat(),
        status=result.status,
        solver_time_seconds=result.solver_time_seconds,
        objective_value=result.objective_value,
        assignments=result.assignments,
    )
    backend.save_schedule_run(run)
    st.session_state["last_run_id"] = run.id

    if result.status in ("optimal", "feasible"):
        st.success(f"Solution found ({result.status}) in {result.solver_time_seconds}s — {len(result.assignments)} assignments")
    else:
        st.error(f"Solver status: {result.status}. {result.stats.get('message', '')}")

if not employees:
    st.warning("Add employees on the Employees page first.")
if not shifts:
    st.warning("Add shifts on the Shifts page first.")

st.divider()

# ---- Display results ----
last_run_id = st.session_state.get("last_run_id")
runs = backend.list_schedule_runs()

if runs:
    st.subheader("Schedule Results")

    run_options = {r.id: f"{r.name} ({r.status})" for r in reversed(runs)}
    selected_run_id = st.selectbox(
        "Select run",
        options=list(run_options.keys()),
        format_func=lambda x: run_options[x],
        index=0,
    )
    run = backend.get_schedule_run(selected_run_id)

    if run and run.assignments:
        # Stats row
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Status", run.status.upper())
        s2.metric("Solver Time", f"{run.solver_time_seconds or 0:.1f}s")
        s3.metric("Assignments", len(run.assignments))
        s4.metric("Objective", f"{run.objective_value or 0:.0f}")

        # Build assignment DataFrame
        rows = []
        for e_id, s_id in run.assignments:
            emp = emp_map.get(e_id)
            shift = shift_map.get(s_id)
            if emp and shift:
                rows.append({
                    "Employee": emp.name,
                    "Shift": shift.name,
                    "Day": DAY_NAMES[shift.day_of_week],
                    "Day #": shift.day_of_week,
                    "Start": shift.start_time,
                    "End": shift.end_time,
                    "Skills Required": ", ".join(skill_map.get(sid, "") for sid in shift.required_skill_ids),
                })
        df = pd.DataFrame(rows)

        if not df.empty:
            # Weekly calendar heatmap
            st.markdown("**Weekly Schedule Grid**")
            pivot = df.groupby(["Employee", "Day"]).size().reset_index(name="Shifts")
            pivot_table = pivot.pivot(index="Employee", columns="Day", values="Shifts").fillna(0)
            # Reorder columns to Mon-Sun
            day_order = [d for d in DAY_NAMES if d in pivot_table.columns]
            pivot_table = pivot_table[day_order]

            fig_heat = px.imshow(
                pivot_table.values,
                x=pivot_table.columns.tolist(),
                y=pivot_table.index.tolist(),
                color_continuous_scale="Blues",
                aspect="auto",
                labels=dict(color="Shifts"),
            )
            fig_heat.update_layout(height=max(300, len(pivot_table) * 40))
            st.plotly_chart(fig_heat, use_container_width=True)

            # Shifts per employee bar chart
            st.markdown("**Shifts per Employee (Fairness)**")
            emp_counts = df["Employee"].value_counts().sort_values()
            fig_bar = px.bar(
                x=emp_counts.values,
                y=emp_counts.index,
                orientation="h",
                labels={"x": "Number of Shifts", "y": "Employee"},
                color=emp_counts.values,
                color_continuous_scale="Viridis",
            )
            fig_bar.update_layout(height=max(300, len(emp_counts) * 35), showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

            # Detailed assignments table
            st.markdown("**Detailed Assignments**")
            display_df = df.sort_values(["Day #", "Start", "Employee"]).drop(columns=["Day #"])
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Export
            st.markdown("**Export**")
            csv = display_df.to_csv(index=False)
            st.download_button(
                "Download Schedule CSV",
                data=csv,
                file_name=f"schedule_{run.week_start_date}.csv",
                mime="text/csv",
            )

    elif run:
        st.warning(f"Run '{run.name}' has no assignments (status: {run.status}).")

    # Run history
    st.divider()
    st.subheader("Run History")
    history_rows = [
        {
            "Name": r.name,
            "Status": r.status,
            "Assignments": len(r.assignments),
            "Solver Time (s)": r.solver_time_seconds or 0,
            "Objective": r.objective_value or 0,
        }
        for r in reversed(runs)
    ]
    st.dataframe(history_rows, use_container_width=True, hide_index=True)
