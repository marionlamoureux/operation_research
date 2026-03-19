"""Shared Databricks-themed styling for the Streamlit app."""

import streamlit as st

# Databricks brand colors
LAVA_600 = "#FF3621"
LAVA_500 = "#FF5F46"
NAVY_800 = "#1B3139"
NAVY_900 = "#0B2026"
OAT_LIGHT = "#F9F7F4"
OAT_MEDIUM = "#EEEDE9"
GREEN_600 = "#00A972"
YELLOW_600 = "#FFAB00"
BLUE_600 = "#2272B4"
MAROON_600 = "#98102A"

# Plotly chart color sequence matching Databricks palette
CHART_COLORS = [LAVA_600, BLUE_600, GREEN_600, YELLOW_600, LAVA_500, MAROON_600, "#5A6B70", NAVY_800]

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');

    /* Global font override — exclude Material icon spans */
    html, body, [class*="css"], .stMarkdown, .stText,
    .stSelectbox, .stMultiSelect, .stTextInput, .stNumberInput,
    .stCheckbox, .stRadio, .stSlider, .stDateInput, .stTimeInput,
    label, p, div, td, th, li,
    .stDataFrame, .stTable,
    button, input, select, textarea,
    [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"],
    [data-testid="stMetricDelta"],
    .stExpander, [data-testid="stExpander"] summary,
    [data-testid="stForm"] {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 14px !important;
    }

    /* Preserve Material Symbols font for icons */
    span.material-symbols-rounded,
    span.material-symbols-outlined,
    .material-symbols-rounded,
    .material-symbols-outlined,
    [data-testid="stIconMaterial"],
    [class*="material-symbols"] {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
        font-size: 24px !important;
    }

    /* Titles */
    h1 {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #1B3139 !important;
    }

    h2 {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #1B3139 !important;
    }

    h3 {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1.25rem !important;
        font-weight: 500 !important;
        color: #1B3139 !important;
    }

    /* Metric values stay larger */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #1B3139 !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 14px !important;
        font-weight: 500 !important;
        color: #5A6B70 !important;
    }

    /* Primary buttons */
    .stButton > button[kind="primary"],
    button[data-testid="stFormSubmitButton"] {
        background-color: #FF3621 !important;
        border-color: #FF3621 !important;
        color: white !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        border-radius: 6px !important;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: #FF5F46 !important;
        border-color: #FF5F46 !important;
    }

    /* Secondary buttons */
    .stButton > button:not([kind="primary"]) {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        border-radius: 6px !important;
        border-color: #DDD9D3 !important;
        color: #1B3139 !important;
    }

    .stButton > button:not([kind="primary"]):hover {
        border-color: #FF3621 !important;
        color: #FF3621 !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1B3139 !important;
    }

    /* Sidebar text — but NOT material icon spans */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div:not([class*="material"]),
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] li,
    [data-testid="stSidebar"] td,
    [data-testid="stSidebar"] th {
        color: #F9F7F4 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 14px !important;
    }

    [data-testid="stSidebar"] .stRadio label {
        color: #F9F7F4 !important;
    }

    /* Sidebar nav links */
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebar"] nav a {
        color: #F9F7F4 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 14px !important;
        text-transform: capitalize !important;
    }

    /* Sidebar nav link text spans — NOT icon spans */
    [data-testid="stSidebarNav"] a span:not(.material-symbols-rounded):not(.material-symbols-outlined):not([class*="material"]),
    [data-testid="stSidebar"] nav a span:not(.material-symbols-rounded):not(.material-symbols-outlined):not([class*="material"]) {
        color: #F9F7F4 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 14px !important;
        text-transform: capitalize !important;
    }

    [data-testid="stSidebarNav"] a:hover,
    [data-testid="stSidebar"] nav a:hover {
        color: #FF3621 !important;
    }

    [data-testid="stSidebarNav"] a[aria-current="page"],
    [data-testid="stSidebar"] nav a[aria-current="page"] {
        color: #FF3621 !important;
        font-weight: 700 !important;
    }

    /* Cards / Expanders */
    [data-testid="stExpander"] {
        border: 1px solid #DDD9D3 !important;
        border-radius: 8px !important;
        background-color: white !important;
    }

    /* Dividers */
    hr {
        border-color: #EEEDE9 !important;
    }

    /* Data frames */
    .stDataFrame {
        border-radius: 8px !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 14px !important;
    }

    .stTabs [aria-selected="true"] {
        color: #FF3621 !important;
        border-bottom-color: #FF3621 !important;
    }

    /* Download button */
    .stDownloadButton > button {
        background-color: #1B3139 !important;
        color: #F9F7F4 !important;
        border-radius: 6px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
    }

    .stDownloadButton > button:hover {
        background-color: #0B2026 !important;
    }

    /* Success / Warning / Error messages */
    .stSuccess {
        background-color: #E6F7F1 !important;
        border-left-color: #00A972 !important;
    }

    .stWarning {
        background-color: #FFF8E6 !important;
        border-left-color: #FFAB00 !important;
    }

    .stError {
        background-color: #FDE8EB !important;
        border-left-color: #98102A !important;
    }

    /* Form borders */
    [data-testid="stForm"] {
        border: 1px solid #DDD9D3 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        background-color: white !important;
    }

    /* Selectbox, multiselect, text input */
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        border-color: #DDD9D3 !important;
        border-radius: 6px !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    /* Plotly chart backgrounds */
    .js-plotly-plot .plotly .bg {
        fill: white !important;
    }
</style>
"""


def apply_style():
    """Inject Databricks-themed CSS into the Streamlit page."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def plotly_layout_defaults():
    """Return common Plotly layout kwargs for Databricks theme."""
    return dict(
        font=dict(family="DM Sans", size=14, color=NAVY_800),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        colorway=CHART_COLORS,
    )
