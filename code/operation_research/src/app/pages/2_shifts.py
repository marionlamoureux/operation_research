"""Shift configuration page: define shift templates and view the weekly grid."""

import streamlit as st
import plotly.graph_objects as go
from models import DAY_NAMES, ShiftSchema
from style import apply_style, plotly_layout_defaults, CHART_COLORS

st.set_page_config(page_title="Shifts", page_icon="\U0001f552", layout="wide")
apply_style()

st.title("Shift Configuration")

backend = st.session_state.get("backend")
if not backend:
    st.error("Backend not initialized. Go to the Home page first.")
    st.stop()

skills = backend.list_skills()
skill_map = {s.id: s.name for s in skills}
skill_names = [s.name for s in skills]
shifts = backend.list_shifts()

# ---- Visual week view ----
st.subheader("Weekly Shift Overview")

if shifts:
    fig = go.Figure()

    shift_type_colors = {}
    color_idx = 0

    for s in shifts:
        base_name = s.name.split(" (")[0] if " (" in s.name else s.name
        if base_name not in shift_type_colors:
            shift_type_colors[base_name] = CHART_COLORS[color_idx % len(CHART_COLORS)]
            color_idx += 1

        start_parts = s.start_time.split(":")
        end_parts = s.end_time.split(":")
        start_h = int(start_parts[0]) + int(start_parts[1]) / 60
        end_h = int(end_parts[0]) + int(end_parts[1]) / 60

        fig.add_trace(go.Bar(
            x=[end_h - start_h],
            y=[DAY_NAMES[s.day_of_week]],
            base=start_h,
            orientation="h",
            name=base_name,
            marker_color=shift_type_colors[base_name],
            text=f"{s.name}<br>{s.start_time}-{s.end_time}<br>Staff: {s.min_staff}-{s.max_staff}",
            textposition="inside",
            textfont=dict(family="DM Sans", size=12, color="white"),
            showlegend=False,
            hovertemplate=f"<b>{s.name}</b><br>{s.start_time} - {s.end_time}<br>Staff: {s.min_staff}-{s.max_staff}<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Hour of Day", range=[0, 24], dtick=2),
        yaxis=dict(categoryorder="array", categoryarray=list(reversed(DAY_NAMES))),
        height=400,
        margin=dict(l=100, r=20, t=20, b=40),
        **plotly_layout_defaults(),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No shifts defined yet. Add shifts below.")

st.divider()

# ---- Shift list ----
st.subheader(f"Shift Definitions ({len(shifts)})")

shifts_by_day = {}
for s in shifts:
    shifts_by_day.setdefault(s.day_of_week, []).append(s)

for day in range(7):
    day_shifts = shifts_by_day.get(day, [])
    if not day_shifts:
        continue
    with st.expander(f"{DAY_NAMES[day]} — {len(day_shifts)} shifts"):
        for s in day_shifts:
            req_skills_str = ", ".join(skill_map.get(sid, "?") for sid in s.required_skill_ids)
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.write(f"**{s.name}** | {s.start_time} - {s.end_time}")
            c2.write(f"Staff: {s.min_staff}-{s.max_staff} | Skills: {req_skills_str or 'Any'}")
            if c3.button("Delete", key=f"del_shift_{s.id}"):
                backend.delete_shift(s.id)
                st.rerun()

st.divider()

# ---- Add single shift ----
st.subheader("Add Shift")
with st.form("add_shift_form"):
    name = st.text_input("Shift name (e.g., 'Morning')")
    day = st.selectbox("Day", options=list(range(7)), format_func=lambda d: DAY_NAMES[d])
    c1, c2 = st.columns(2)
    start_time = c1.time_input("Start time")
    end_time = c2.time_input("End time")
    c3, c4 = st.columns(2)
    min_staff = c3.number_input("Min staff", value=1, min_value=1, max_value=20)
    max_staff = c4.number_input("Max staff", value=3, min_value=1, max_value=20)
    req_skills = st.multiselect("Required skills", options=skill_names)

    if st.form_submit_button("Add Shift") and name:
        req_skill_ids = [s.id for s in skills if s.name in req_skills]
        new_shift = ShiftSchema(
            name=name,
            day_of_week=day,
            start_time=start_time.strftime("%H:%M"),
            end_time=end_time.strftime("%H:%M"),
            min_staff=min_staff,
            max_staff=max_staff,
            required_skill_ids=req_skill_ids,
        )
        backend.create_shift(new_shift)
        st.success(f"Added shift: {name}")
        st.rerun()

st.divider()

# ---- Bulk shift creation ----
st.subheader("Bulk Create Shifts")
with st.form("bulk_shift_form"):
    st.markdown("Create the same shift across multiple days.")
    bulk_name = st.text_input("Shift name template")
    bulk_days = st.multiselect("Days", options=DAY_NAMES, default=DAY_NAMES[:5])
    bc1, bc2 = st.columns(2)
    bulk_start = bc1.time_input("Start time", key="bulk_start")
    bulk_end = bc2.time_input("End time", key="bulk_end")
    bc3, bc4 = st.columns(2)
    bulk_min = bc3.number_input("Min staff", value=1, min_value=1, max_value=20, key="bulk_min")
    bulk_max = bc4.number_input("Max staff", value=3, min_value=1, max_value=20, key="bulk_max")
    bulk_skills = st.multiselect("Required skills", options=skill_names, key="bulk_skills")

    if st.form_submit_button("Create Shifts") and bulk_name:
        req_skill_ids = [s.id for s in skills if s.name in bulk_skills]
        count = 0
        for day_name in bulk_days:
            d = DAY_NAMES.index(day_name)
            shift = ShiftSchema(
                name=f"{bulk_name} ({day_name[:3]})",
                day_of_week=d,
                start_time=bulk_start.strftime("%H:%M"),
                end_time=bulk_end.strftime("%H:%M"),
                min_staff=bulk_min,
                max_staff=bulk_max,
                required_skill_ids=req_skill_ids,
            )
            backend.create_shift(shift)
            count += 1
        st.success(f"Created {count} shifts")
        st.rerun()
