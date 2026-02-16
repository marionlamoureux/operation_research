import os
import base64
import dash
from dash import dcc, html, dash_table, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ── Backend toggle ─────────────────────────────────────────
USE_MOCK = os.getenv("USE_MOCK_BACKEND", "true").lower() == "true"

if USE_MOCK:
    from backend_mock import MockBackend
    backend = MockBackend()
else:
    from backend_real import RealBackend
    backend = RealBackend()

# ── App init ───────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Neverending Forest",
)

COLORS = {
    "forest": "#2D6A4F",
    "leaf": "#52B788",
    "earth": "#8B6914",
    "water": "#219EBC",
    "alert": "#E63946",
    "warm": "#F4A261",
    "light": "#F0F4F0",
    "dark": "#1B4332",
}

# Forest center coordinates
FOREST_CENTER = {"lat": 48.6370, "lon": -1.5090}


# ── Components ─────────────────────────────────────────────

def stat_card(title, value, icon, color="forest"):
    hex_color = COLORS.get(color, color)
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div([
                    html.H6(title, className="text-muted mb-1",
                             style={"fontSize": "0.8rem"}),
                    html.H3(str(value), className="mb-0",
                             style={"color": hex_color}),
                ], className="flex-grow-1"),
                html.Div([
                    html.I(className=f"fas {icon} fa-2x",
                           style={"color": hex_color, "opacity": 0.6}),
                ], className="ms-3"),
            ], className="d-flex align-items-center"),
        ], className="p-3"),
    ], className="shadow-sm mb-3", style={"borderLeft": f"4px solid {hex_color}"})


def create_navbar():
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.I(className="fas fa-tree me-2", style={"fontSize": "1.5rem"}),
                    dbc.NavbarBrand("Neverending Forest", className="ms-1 fw-bold"),
                ], width="auto"),
            ], align="center", className="g-0"),
            dbc.Nav([
                dbc.NavItem(dbc.NavLink(
                    [html.I(className="fas fa-paw me-1"), "Fauna"],
                    href="/", active="exact")),
                dbc.NavItem(dbc.NavLink(
                    [html.I(className="fas fa-leaf me-1"), "Flora"],
                    href="/flora", active="exact")),
                dbc.NavItem(dbc.NavLink(
                    [html.I(className="fas fa-water me-1"), "Hydro"],
                    href="/hydro", active="exact")),
                dbc.NavItem(dbc.NavLink(
                    [html.I(className="fas fa-cloud me-1"), "Carbon"],
                    href="/carbon", active="exact")),
            ], navbar=True, className="ms-auto"),
        ], fluid=True),
        color=COLORS["dark"],
        dark=True,
        className="mb-4",
    )


# ══════════════════════════════════════════════════════════
# TAB 1 — FAUNA DETECTIONS
# ══════════════════════════════════════════════════════════

def fauna_layout():
    stats = backend.get_fauna_stats()
    return dbc.Container([
        html.H4("Fauna Detections — Trail Cameras",
                className="mb-3", style={"color": COLORS["dark"]}),
        dbc.Row([
            dbc.Col(stat_card("Detections Today", stats["detections_today"],
                              "fa-camera", "forest"), md=3),
            dbc.Col(stat_card("Unique Species", stats["unique_species"],
                              "fa-paw", "leaf"), md=3),
            dbc.Col(stat_card("Most Active Camera", stats["most_active_camera"],
                              "fa-video", "earth"), md=3),
            dbc.Col(stat_card("Latest Detection", stats["latest_detection"],
                              "fa-clock", "water"), md=3),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Detections Over Time"),
                    dbc.CardBody(dcc.Graph(id="fauna-timeline")),
                ], className="shadow-sm"),
            ], md=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Species Distribution"),
                    dbc.CardBody(dcc.Graph(id="fauna-species-pie")),
                ], className="shadow-sm"),
            ], md=4),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Detection Map"),
                    dbc.CardBody(dcc.Graph(id="fauna-map")),
                ], className="shadow-sm"),
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Recent Detections"),
                    dbc.CardBody(html.Div(id="fauna-table")),
                ], className="shadow-sm"),
            ], md=6),
        ]),
        dcc.Interval(id="fauna-interval", interval=60_000, n_intervals=0),
    ], fluid=True)


@callback(
    [Output("fauna-timeline", "figure"),
     Output("fauna-species-pie", "figure"),
     Output("fauna-map", "figure"),
     Output("fauna-table", "children")],
    Input("fauna-interval", "n_intervals"),
)
def update_fauna(_):
    detections = backend.get_fauna_detections(days=30)
    df = pd.DataFrame([d.model_dump() for d in detections])

    # Timeline
    if not df.empty:
        df["date"] = pd.to_datetime(df["timestamp"]).dt.date
        daily = df.groupby("date").size().reset_index(name="count")
        fig_time = px.area(daily, x="date", y="count",
                           color_discrete_sequence=[COLORS["forest"]])
        fig_time.update_layout(margin=dict(t=10, b=30, l=40, r=10), height=280,
                               xaxis_title="", yaxis_title="Detections")
    else:
        fig_time = go.Figure()

    # Species pie
    dist = backend.get_species_distribution()
    fig_pie = px.pie(values=list(dist.values()), names=list(dist.keys()),
                     color_discrete_sequence=px.colors.qualitative.Set3)
    fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280,
                          showlegend=True, legend=dict(font=dict(size=10)))

    # Map
    if not df.empty:
        fig_map = px.scatter_mapbox(
            df, lat="latitude", lon="longitude", color="common_name",
            hover_data=["confidence", "camera_id", "timestamp"],
            zoom=15, center=FOREST_CENTER, height=350,
        )
        fig_map.update_layout(mapbox_style="open-street-map",
                              margin=dict(t=0, b=0, l=0, r=0),
                              legend=dict(font=dict(size=9)))
    else:
        fig_map = go.Figure()

    # Table
    if not df.empty:
        table_df = df[["common_name", "confidence", "camera_id", "timestamp"]].head(15)
        table_df["confidence"] = table_df["confidence"].apply(lambda x: f"{x:.0%}")
        table_df["timestamp"] = pd.to_datetime(table_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
        table = dash_table.DataTable(
            data=table_df.to_dict("records"),
            columns=[
                {"name": "Species", "id": "common_name"},
                {"name": "Confidence", "id": "confidence"},
                {"name": "Camera", "id": "camera_id"},
                {"name": "Time", "id": "timestamp"},
            ],
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "8px", "fontSize": "0.85rem"},
            style_header={"backgroundColor": COLORS["dark"], "color": "white",
                          "fontWeight": "bold"},
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": COLORS["light"]}
            ],
        )
    else:
        table = html.P("No detections yet.", className="text-muted")

    return fig_time, fig_pie, fig_map, table


# ══════════════════════════════════════════════════════════
# TAB 2 — FLORA IDENTIFICATION
# ══════════════════════════════════════════════════════════

def flora_layout():
    return dbc.Container([
        html.H4("Flora Identification",
                className="mb-3", style={"color": COLORS["dark"]}),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Upload Photo for Identification"),
                    dbc.CardBody([
                        dcc.Upload(
                            id="flora-upload",
                            children=html.Div([
                                html.I(className="fas fa-cloud-upload-alt fa-3x mb-2",
                                       style={"color": COLORS["leaf"]}),
                                html.P("Drag & drop or click to upload a photo"),
                            ], className="text-center py-4"),
                            style={
                                "borderWidth": "2px", "borderStyle": "dashed",
                                "borderColor": COLORS["leaf"], "borderRadius": "10px",
                                "cursor": "pointer",
                            },
                        ),
                        dbc.Row([
                            dbc.Col(dbc.Input(id="flora-lat", type="number",
                                              placeholder="Latitude",
                                              value=FOREST_CENTER["lat"], step=0.0001), md=5),
                            dbc.Col(dbc.Input(id="flora-lng", type="number",
                                              placeholder="Longitude",
                                              value=FOREST_CENTER["lon"], step=0.0001), md=5),
                            dbc.Col(dbc.Button("Identify", id="flora-identify-btn",
                                               color="success", className="w-100"), md=2),
                        ], className="mt-3"),
                    ]),
                ], className="shadow-sm"),
                html.Div(id="flora-result", className="mt-3"),
            ], md=5),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Detection Locations"),
                    dbc.CardBody(dcc.Graph(id="flora-map")),
                ], className="shadow-sm"),
            ], md=7),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Recent Identifications"),
                    dbc.CardBody(html.Div(id="flora-gallery")),
                ], className="shadow-sm"),
            ]),
        ]),
    ], fluid=True)


@callback(
    Output("flora-map", "figure"),
    Output("flora-gallery", "children"),
    Input("url", "pathname"),
)
def update_flora_static(_):
    detections = backend.get_flora_detections()
    df = pd.DataFrame([d.model_dump() for d in detections])

    if not df.empty:
        fig = px.scatter_mapbox(
            df, lat="latitude", lon="longitude", color="common_name",
            hover_data=["species", "confidence"],
            zoom=15, center=FOREST_CENTER, height=400,
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig.update_layout(mapbox_style="open-street-map",
                          margin=dict(t=0, b=0, l=0, r=0))
    else:
        fig = go.Figure()

    # Gallery as cards
    cards = []
    for d in detections[:12]:
        cards.append(dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H6(d.common_name, className="mb-1"),
                    html.Small(d.species, className="text-muted fst-italic"),
                    html.Br(),
                    dbc.Badge(f"{d.confidence:.0%}", color="success", className="mt-1"),
                ], className="p-2"),
            ], className="shadow-sm mb-2"),
            md=2, sm=4, xs=6,
        ))

    return fig, dbc.Row(cards) if cards else html.P("No identifications yet.", className="text-muted")


@callback(
    Output("flora-result", "children"),
    Input("flora-identify-btn", "n_clicks"),
    [State("flora-upload", "contents"),
     State("flora-lat", "value"),
     State("flora-lng", "value")],
    prevent_initial_call=True,
)
def identify_flora(n_clicks, contents, lat, lng):
    if not contents:
        return dbc.Alert("Please upload a photo first.", color="warning")

    # Decode image
    content_type, content_string = contents.split(",")
    image_bytes = base64.b64decode(content_string)
    lat = lat or FOREST_CENTER["lat"]
    lng = lng or FOREST_CENTER["lon"]

    result = backend.identify_flora(image_bytes, float(lat), float(lng))

    return dbc.Card([
        dbc.CardBody([
            html.H5("Identification Result", className="mb-2"),
            html.Div([
                html.Img(src=contents, style={"maxHeight": "120px", "borderRadius": "8px"},
                         className="me-3"),
                html.Div([
                    html.H5(result.common_name, style={"color": COLORS["forest"]}),
                    html.P(result.species, className="fst-italic text-muted mb-1"),
                    dbc.Progress(value=result.confidence * 100,
                                 label=f"{result.confidence:.0%}",
                                 color="success", className="mb-1"),
                    html.Small(f"Location: {result.latitude:.4f}, {result.longitude:.4f}"),
                ]),
            ], className="d-flex align-items-start"),
        ]),
    ], className="shadow-sm border-success")


# ══════════════════════════════════════════════════════════
# TAB 3 — HYDROMETRICS
# ══════════════════════════════════════════════════════════

def hydro_layout():
    stats = backend.get_hydro_stats()
    return dbc.Container([
        html.H4("Hydrometrics Monitoring",
                className="mb-3", style={"color": COLORS["dark"]}),
        dbc.Row([
            dbc.Col(stat_card("Water Level", f'{stats["avg_water_level_cm"]} cm',
                              "fa-water", "water"), md=3),
            dbc.Col(stat_card("Flow Rate", f'{stats["avg_flow_rate_m3s"]} m3/s',
                              "fa-tachometer-alt", "forest"), md=3),
            dbc.Col(stat_card("Water Temp", f'{stats["avg_water_temp_c"]} C',
                              "fa-thermometer-half", "warm"), md=3),
            dbc.Col(stat_card("Active Alerts", stats["active_alerts"],
                              "fa-exclamation-triangle", "alert"), md=3),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Water Level & Flow Rate (48h)"),
                    dbc.CardBody(dcc.Graph(id="hydro-timeline")),
                ], className="shadow-sm"),
            ], md=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Water Level Gauge"),
                    dbc.CardBody(dcc.Graph(id="hydro-gauge")),
                ], className="shadow-sm"),
            ], md=4),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Alert History"),
                    dbc.CardBody(html.Div(id="hydro-alerts-table")),
                ], className="shadow-sm"),
            ]),
        ]),
        dcc.Interval(id="hydro-interval", interval=60_000, n_intervals=0),
    ], fluid=True)


@callback(
    [Output("hydro-timeline", "figure"),
     Output("hydro-gauge", "figure"),
     Output("hydro-alerts-table", "children")],
    Input("hydro-interval", "n_intervals"),
)
def update_hydro(_):
    readings = backend.get_hydro_readings(hours=48)
    df = pd.DataFrame([r.model_dump() for r in readings])

    # Dual-axis timeline
    if not df.empty:
        fig_time = go.Figure()
        fig_time.add_trace(go.Scatter(
            x=df["timestamp"], y=df["water_level_cm"],
            name="Water Level (cm)", line=dict(color=COLORS["water"], width=2),
        ))
        fig_time.add_trace(go.Scatter(
            x=df["timestamp"], y=df["flow_rate_m3s"],
            name="Flow Rate (m3/s)", yaxis="y2",
            line=dict(color=COLORS["forest"], width=2, dash="dot"),
        ))
        # Threshold line
        fig_time.add_hline(y=150, line_dash="dash", line_color=COLORS["alert"],
                           annotation_text="Alert threshold (150 cm)")
        fig_time.update_layout(
            yaxis=dict(title="Water Level (cm)"),
            yaxis2=dict(title="Flow Rate (m3/s)", overlaying="y", side="right"),
            margin=dict(t=30, b=30, l=50, r=50), height=300,
            legend=dict(orientation="h", y=-0.2),
        )
    else:
        fig_time = go.Figure()

    # Gauge
    stats = backend.get_hydro_stats()
    level = stats["avg_water_level_cm"]
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=level,
        title={"text": "Avg Water Level (cm)"},
        gauge=dict(
            axis=dict(range=[0, 200]),
            bar=dict(color=COLORS["water"]),
            steps=[
                dict(range=[0, 80], color="#D8F3DC"),
                dict(range=[80, 120], color="#F4A261"),
                dict(range=[120, 200], color="#E63946"),
            ],
            threshold=dict(line=dict(color="red", width=3), thickness=0.8, value=150),
        ),
    ))
    fig_gauge.update_layout(margin=dict(t=40, b=20, l=30, r=30), height=300)

    # Alerts table
    alerts = backend.get_hydro_alerts()
    if alerts:
        alert_data = []
        for a in alerts[:20]:
            alert_data.append({
                "Station": a.station_name,
                "Level (cm)": a.water_level_cm,
                "Alert": a.alert_level.value.upper(),
                "Time": a.timestamp.strftime("%Y-%m-%d %H:%M"),
            })
        table = dash_table.DataTable(
            data=alert_data,
            columns=[{"name": c, "id": c} for c in alert_data[0].keys()],
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "8px", "fontSize": "0.85rem"},
            style_header={"backgroundColor": COLORS["dark"], "color": "white",
                          "fontWeight": "bold"},
            style_data_conditional=[
                {"if": {"filter_query": '{Alert} = "CRITICAL"'},
                 "backgroundColor": "#FECDD3", "color": COLORS["alert"]},
                {"if": {"filter_query": '{Alert} = "WARNING"'},
                 "backgroundColor": "#FEF3C7", "color": "#92400E"},
            ],
        )
    else:
        table = html.P("No alerts.", className="text-muted")

    return fig_time, fig_gauge, table


# ══════════════════════════════════════════════════════════
# TAB 4 — CARBON CAPTURE
# ══════════════════════════════════════════════════════════

def carbon_layout():
    stats = backend.get_carbon_stats()
    return dbc.Container([
        html.H4("Carbon Capture & Sequestration",
                className="mb-3", style={"color": COLORS["dark"]}),
        dbc.Row([
            dbc.Col(stat_card("CO2 Sequestered", f'{stats["total_co2_tons"]} t',
                              "fa-cloud", "forest"), md=3),
            dbc.Col(stat_card("Total Biomass", f'{stats["total_biomass_tons"]} t',
                              "fa-tree", "leaf"), md=3),
            dbc.Col(stat_card("CO2 / Hectare", f'{stats["co2_per_hectare"]} t/ha',
                              "fa-chart-bar", "earth"), md=3),
            dbc.Col(stat_card("Tree Count", f'{stats["total_trees"]:,}',
                              "fa-seedling", "forest"), md=3),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("CO2 Sequestration by Zone (Latest)"),
                    dbc.CardBody(dcc.Graph(id="carbon-bar")),
                ], className="shadow-sm"),
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("CO2 Sequestration Trend"),
                    dbc.CardBody(dcc.Graph(id="carbon-trend")),
                ], className="shadow-sm"),
            ], md=6),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Biomass by Zone Over Time"),
                    dbc.CardBody(dcc.Graph(id="carbon-biomass")),
                ], className="shadow-sm"),
            ]),
        ]),
    ], fluid=True)


@callback(
    [Output("carbon-bar", "figure"),
     Output("carbon-trend", "figure"),
     Output("carbon-biomass", "figure")],
    Input("url", "pathname"),
)
def update_carbon(_):
    data = backend.get_carbon_data(months=24)
    df = pd.DataFrame([d.model_dump() for d in data])

    # Bar chart — latest month per zone
    if not df.empty:
        latest_date = df["measurement_date"].max()
        latest = df[df["measurement_date"] == latest_date]
        fig_bar = px.bar(
            latest, x="zone_name", y="co2_sequestered_tons",
            color="zone_name",
            color_discrete_sequence=[COLORS["forest"], COLORS["leaf"],
                                     COLORS["earth"], COLORS["water"], COLORS["warm"]],
        )
        fig_bar.update_layout(margin=dict(t=10, b=40, l=40, r=10), height=300,
                              xaxis_title="", yaxis_title="CO2 (tons)",
                              showlegend=False)
        fig_bar.update_xaxes(tickangle=-30)
    else:
        fig_bar = go.Figure()

    # Trend line — total CO2 per month
    if not df.empty:
        monthly = df.groupby("measurement_date")["co2_sequestered_tons"].sum().reset_index()
        monthly = monthly.sort_values("measurement_date")
        fig_trend = px.line(monthly, x="measurement_date", y="co2_sequestered_tons",
                            color_discrete_sequence=[COLORS["forest"]])
        fig_trend.update_layout(margin=dict(t=10, b=30, l=40, r=10), height=300,
                                xaxis_title="", yaxis_title="Total CO2 (tons)")

        # National average reference line (~7.2 t/ha for French forests)
        total_ha = 9.0
        national_avg = 7.2 * total_ha
        fig_trend.add_hline(y=national_avg, line_dash="dash",
                            line_color=COLORS["warm"],
                            annotation_text=f"National avg ({national_avg:.0f} t for {total_ha} ha)")
    else:
        fig_trend = go.Figure()

    # Biomass stacked area by zone
    if not df.empty:
        fig_bio = px.area(
            df.sort_values("measurement_date"),
            x="measurement_date", y="biomass_tons", color="zone_name",
            color_discrete_sequence=[COLORS["forest"], COLORS["leaf"],
                                     COLORS["earth"], COLORS["water"], COLORS["warm"]],
        )
        fig_bio.update_layout(margin=dict(t=10, b=30, l=40, r=10), height=300,
                              xaxis_title="", yaxis_title="Biomass (tons)",
                              legend=dict(font=dict(size=10)))
    else:
        fig_bio = go.Figure()

    return fig_bar, fig_trend, fig_bio


# ══════════════════════════════════════════════════════════
# ROUTING
# ══════════════════════════════════════════════════════════

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    create_navbar(),
    html.Div(id="page-content", style={"minHeight": "85vh"}),
    html.Footer(
        html.Small("Neverending Forest Monitoring System",
                   className="text-muted"),
        className="text-center py-3",
    ),
], style={"backgroundColor": COLORS["light"], "minHeight": "100vh"})


@callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def display_page(pathname):
    if pathname == "/flora":
        return flora_layout()
    elif pathname == "/hydro":
        return hydro_layout()
    elif pathname == "/carbon":
        return carbon_layout()
    return fauna_layout()


if __name__ == "__main__":
    port = int(os.getenv("DATABRICKS_APP_PORT", "8050"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
