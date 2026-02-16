import os
from datetime import datetime, timedelta, date
from typing import List, Optional
from databricks import sql
from databricks.sdk.core import Config
from models import (
    FaunaDetection, FloraDetection, HydroMetric, CarbonCapture, AlertLevel
)


class RealBackend:

    def __init__(self):
        self.catalog = os.getenv("DATABRICKS_CATALOG", "nef_catalog")
        self.schema = os.getenv("DATABRICKS_SCHEMA", "neverending")
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID environment variable is required")
        self.config = Config()
        self._connection = None

    def _get_connection(self):
        if self._connection is None:
            self._connection = sql.connect(
                server_hostname=self.config.host,
                http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
                credentials_provider=lambda: self.config.authenticate,
            )
        return self._connection

    def _execute(self, query: str) -> List[dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def _table(self, name: str) -> str:
        return f"{self.catalog}.{self.schema}.{name}"

    # ── Fauna ──────────────────────────────────────────────

    def get_fauna_detections(self, days: int = 30) -> List[FaunaDetection]:
        rows = self._execute(f"""
            SELECT * FROM {self._table('fauna_detections')}
            WHERE timestamp >= CURRENT_TIMESTAMP() - INTERVAL {days} DAY
            ORDER BY timestamp DESC
        """)
        return [FaunaDetection(**r) for r in rows]

    def get_fauna_stats(self) -> dict:
        row = self._execute(f"""
            SELECT
                COUNT(CASE WHEN timestamp >= CURRENT_DATE() THEN 1 END) AS detections_today,
                COUNT(DISTINCT common_name) AS unique_species,
                MAX(timestamp) AS latest_ts
            FROM {self._table('fauna_detections')}
        """)[0]
        camera_row = self._execute(f"""
            SELECT camera_id, COUNT(*) AS cnt
            FROM {self._table('fauna_detections')}
            GROUP BY camera_id ORDER BY cnt DESC LIMIT 1
        """)
        return {
            "detections_today": row["detections_today"],
            "unique_species": row["unique_species"],
            "most_active_camera": camera_row[0]["camera_id"] if camera_row else "N/A",
            "latest_detection": row["latest_ts"].strftime("%H:%M") if row["latest_ts"] else "N/A",
        }

    def get_species_distribution(self) -> dict:
        rows = self._execute(f"""
            SELECT common_name, COUNT(*) AS cnt
            FROM {self._table('fauna_detections')}
            GROUP BY common_name ORDER BY cnt DESC
        """)
        return {r["common_name"]: r["cnt"] for r in rows}

    # ── Flora ──────────────────────────────────────────────

    def get_flora_detections(self) -> List[FloraDetection]:
        rows = self._execute(f"""
            SELECT * FROM {self._table('flora_detections')}
            ORDER BY timestamp DESC LIMIT 100
        """)
        return [FloraDetection(**r) for r in rows]

    def identify_flora(self, image_bytes: bytes, lat: float, lng: float) -> FloraDetection:
        # In production, this would call a Model Serving endpoint
        # For now, return a placeholder
        return FloraDetection(
            id="FL-PENDING",
            species="Identification pending",
            common_name="Pending",
            confidence=0.0,
            latitude=lat,
            longitude=lng,
            timestamp=datetime.now(),
        )

    # ── Hydrometrics ───────────────────────────────────────

    def get_hydro_readings(self, hours: int = 48) -> List[HydroMetric]:
        rows = self._execute(f"""
            SELECT * FROM {self._table('hydrometrics')}
            WHERE timestamp >= CURRENT_TIMESTAMP() - INTERVAL {hours} HOUR
            ORDER BY timestamp DESC
        """)
        return [HydroMetric(**r) for r in rows]

    def get_hydro_stats(self) -> dict:
        rows = self._execute(f"""
            WITH latest AS (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY station_id ORDER BY timestamp DESC) AS rn
                FROM {self._table('hydrometrics')}
            )
            SELECT
                ROUND(AVG(water_level_cm), 1) AS avg_water_level_cm,
                ROUND(AVG(flow_rate_m3s), 2) AS avg_flow_rate_m3s,
                ROUND(AVG(water_temperature_c), 1) AS avg_water_temp_c,
                SUM(CASE WHEN alert_level != 'normal' THEN 1 ELSE 0 END) AS active_alerts
            FROM latest WHERE rn = 1
        """)
        return rows[0] if rows else {
            "avg_water_level_cm": 0, "avg_flow_rate_m3s": 0,
            "avg_water_temp_c": 0, "active_alerts": 0,
        }

    def get_hydro_alerts(self) -> List[HydroMetric]:
        rows = self._execute(f"""
            SELECT * FROM {self._table('hydrometrics')}
            WHERE alert_level != 'normal'
            ORDER BY timestamp DESC LIMIT 100
        """)
        return [HydroMetric(**r) for r in rows]

    # ── Carbon Capture ─────────────────────────────────────

    def get_carbon_data(self, months: int = 24) -> List[CarbonCapture]:
        rows = self._execute(f"""
            SELECT * FROM {self._table('carbon_capture')}
            WHERE measurement_date >= ADD_MONTHS(CURRENT_DATE(), -{months})
            ORDER BY measurement_date DESC
        """)
        return [CarbonCapture(**r) for r in rows]

    def get_carbon_stats(self) -> dict:
        rows = self._execute(f"""
            WITH latest AS (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY zone_id ORDER BY measurement_date DESC) AS rn
                FROM {self._table('carbon_capture')}
            )
            SELECT
                ROUND(SUM(co2_sequestered_tons), 1) AS total_co2_tons,
                ROUND(SUM(biomass_tons), 1) AS total_biomass_tons,
                ROUND(SUM(co2_sequestered_tons) / SUM(area_hectares), 1) AS co2_per_hectare,
                SUM(tree_count) AS total_trees
            FROM latest WHERE rn = 1
        """)
        return rows[0] if rows else {
            "total_co2_tons": 0, "total_biomass_tons": 0,
            "co2_per_hectare": 0, "total_trees": 0,
        }

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None
