# Databricks notebook source
# MAGIC %md
# MAGIC # Generate Synthetic Data — Hydrometrics & Carbon Capture
# MAGIC
# MAGIC Creates tables in `nef_catalog.neverending` for the Neverending Forest monitoring app.
# MAGIC Run this notebook once to seed the missing tables.

# COMMAND ----------

CATALOG = "nef_catalog"
SCHEMA = "neverending"

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Hydrometrics — hourly sensor readings (6 months)

# COMMAND ----------

import random
from datetime import datetime, timedelta
from pyspark.sql import Row
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, TimestampType
)

random.seed(42)

stations = [
    ("HYDRO-01", "Ruisseau Nord"),
    ("HYDRO-02", "Mare Centrale"),
    ("HYDRO-03", "Source Est"),
]

now = datetime.now()
rows = []
idx = 0

for hour_offset in range(24 * 180):  # 180 days
    ts = now - timedelta(hours=hour_offset)
    day_of_year = ts.timetuple().tm_yday

    for station_id, station_name in stations:
        idx += 1
        base_level = {"HYDRO-01": 45, "HYDRO-02": 30, "HYDRO-03": 55}[station_id]

        # Seasonal pattern: higher in winter/spring, lower in summer
        seasonal = 20 * (1 + 0.8 * abs((day_of_year - 180) / 180))
        rain_event = 40 if random.random() < 0.03 else 0  # 3% chance of rain spike
        level = base_level + seasonal + rain_event + random.gauss(0, 6)
        level = max(5, round(level, 1))

        flow = round(level * 0.02 + random.gauss(0, 0.08), 2)
        flow = max(0.01, flow)

        # Water temp follows air temp with lag
        temp = round(6 + 8 * (1 - abs((day_of_year - 200) / 200)) + random.gauss(0, 0.8), 1)

        if level > 120:
            alert_level = "critical"
        elif level > 80:
            alert_level = "warning"
        else:
            alert_level = "normal"

        rows.append(Row(
            id=f"HM-{idx:06d}",
            station_id=station_id,
            station_name=station_name,
            water_level_cm=float(level),
            flow_rate_m3s=float(flow),
            water_temperature_c=float(temp),
            timestamp=ts,
            alert_level=alert_level,
        ))

hydro_df = spark.createDataFrame(rows)
hydro_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.hydrometrics")
print(f"Created hydrometrics: {hydro_df.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Carbon Capture — monthly zone measurements (2 years)

# COMMAND ----------

from datetime import date

zones = [
    ("Z1", "Parcelle Hetres Nord", 2.1),
    ("Z2", "Parcelle Chenes Est", 1.8),
    ("Z3", "Parcelle Mixte Sud", 2.5),
    ("Z4", "Ripisylve Ruisseau", 1.2),
    ("Z5", "Clairiere Centrale", 1.4),
]

rows = []
idx = 0

for year in [2024, 2025]:
    for month in range(1, 13):
        for zone_id, zone_name, area in zones:
            idx += 1
            months_elapsed = (year - 2024) * 12 + month
            growth_factor = 1 + 0.015 * months_elapsed  # ~1.5% monthly growth

            tree_count = int(area * 820 * growth_factor + random.gauss(0, 15))
            biomass = round(area * 118 * growth_factor + random.gauss(0, 3), 1)
            co2 = round(biomass * 1.83, 1)  # IPCC conversion factor

            rows.append(Row(
                id=f"CC-{idx:04d}",
                zone_id=zone_id,
                zone_name=zone_name,
                area_hectares=float(area),
                biomass_tons=float(biomass),
                co2_sequestered_tons=float(co2),
                tree_count=int(tree_count),
                measurement_date=date(year, month, 1),
            ))

carbon_df = spark.createDataFrame(rows)
carbon_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.carbon_capture")
print(f"Created carbon_capture: {carbon_df.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify

# COMMAND ----------

display(spark.sql(f"SELECT * FROM {CATALOG}.{SCHEMA}.hydrometrics LIMIT 10"))
display(spark.sql(f"SELECT * FROM {CATALOG}.{SCHEMA}.carbon_capture LIMIT 10"))
print("Done! Tables ready for the Neverending Forest app.")
