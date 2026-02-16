import random
from datetime import datetime, timedelta, date
from typing import List, Optional
from models import (
    FaunaDetection, FloraDetection, HydroMetric, CarbonCapture, AlertLevel
)

# Forest bounding box — 9 hectares in Bourgogne-Franche-Comte, France
# Center: 47°15'54.5"N 5°35'15.1"E
LAT_MIN, LAT_MAX = 47.2635, 47.2668
LNG_MIN, LNG_MAX = 5.5855, 5.5895

FAUNA_SPECIES = [
    ("Sus scrofa", "Sanglier"),
    ("Capreolus capreolus", "Chevreuil"),
    ("Vulpes vulpes", "Renard roux"),
    ("Meles meles", "Blaireau"),
    ("Martes martes", "Martre des pins"),
    ("Sciurus vulgaris", "Ecureuil roux"),
    ("Lepus europaeus", "Lievre d'Europe"),
    ("Buteo buteo", "Buse variable"),
    ("Dendrocopos major", "Pic epeiche"),
    ("Strix aluco", "Chouette hulotte"),
]

FLORA_SPECIES = [
    ("Fagus sylvatica", "Hetre commun"),
    ("Quercus robur", "Chene pedoncule"),
    ("Castanea sativa", "Chataignier"),
    ("Betula pendula", "Bouleau verruqueux"),
    ("Ilex aquifolium", "Houx commun"),
    ("Pteridium aquilinum", "Fougere aigle"),
    ("Hedera helix", "Lierre grimpant"),
    ("Anemone nemorosa", "Anemone des bois"),
    ("Hyacinthoides non-scripta", "Jacinthe des bois"),
    ("Digitalis purpurea", "Digitale pourpre"),
]

CAMERA_IDS = ["CAM-N01", "CAM-N02", "CAM-S01", "CAM-S02", "CAM-E01", "CAM-W01"]

HYDRO_STATIONS = [
    ("HYDRO-01", "Ruisseau Nord"),
    ("HYDRO-02", "Mare Centrale"),
    ("HYDRO-03", "Source Est"),
]

CARBON_ZONES = [
    ("Z1", "Parcelle Hetres Nord", 2.1),
    ("Z2", "Parcelle Chenes Est", 1.8),
    ("Z3", "Parcelle Mixte Sud", 2.5),
    ("Z4", "Ripisylve Ruisseau", 1.2),
    ("Z5", "Clairiere Centrale", 1.4),
]


def _rand_coord():
    return (
        random.uniform(LAT_MIN, LAT_MAX),
        random.uniform(LNG_MIN, LNG_MAX),
    )


class MockBackend:

    def __init__(self):
        random.seed(42)
        self._fauna = self._generate_fauna(200)
        self._flora = self._generate_flora(60)
        self._hydro = self._generate_hydro(24 * 30)  # 30 days hourly
        self._carbon = self._generate_carbon()

    # ── Fauna ──────────────────────────────────────────────

    def _generate_fauna(self, n: int) -> List[FaunaDetection]:
        now = datetime.now()
        detections = []
        for i in range(n):
            species, common = random.choice(FAUNA_SPECIES)
            lat, lng = _rand_coord()
            ts = now - timedelta(hours=random.randint(0, 24 * 30))
            detections.append(FaunaDetection(
                id=f"FD-{i+1:04d}",
                species=species,
                common_name=common,
                confidence=round(random.uniform(0.55, 0.99), 2),
                camera_id=random.choice(CAMERA_IDS),
                latitude=lat,
                longitude=lng,
                timestamp=ts,
                image_path=None,
            ))
        return sorted(detections, key=lambda d: d.timestamp, reverse=True)

    def get_fauna_detections(self, days: int = 30) -> List[FaunaDetection]:
        cutoff = datetime.now() - timedelta(days=days)
        return [d for d in self._fauna if d.timestamp >= cutoff]

    def get_fauna_stats(self) -> dict:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_detections = [d for d in self._fauna if d.timestamp >= today]
        all_species = set(d.common_name for d in self._fauna)
        camera_counts = {}
        for d in self._fauna:
            camera_counts[d.camera_id] = camera_counts.get(d.camera_id, 0) + 1
        most_active = max(camera_counts, key=camera_counts.get) if camera_counts else "N/A"
        return {
            "detections_today": len(today_detections),
            "unique_species": len(all_species),
            "most_active_camera": most_active,
            "latest_detection": self._fauna[0].timestamp.strftime("%H:%M") if self._fauna else "N/A",
            "species_distribution": {d.common_name: 0 for d in self._fauna},
        }

    def get_species_distribution(self) -> dict:
        dist = {}
        for d in self._fauna:
            dist[d.common_name] = dist.get(d.common_name, 0) + 1
        return dist

    # ── Flora ──────────────────────────────────────────────

    def _generate_flora(self, n: int) -> List[FloraDetection]:
        now = datetime.now()
        detections = []
        for i in range(n):
            species, common = random.choice(FLORA_SPECIES)
            lat, lng = _rand_coord()
            detections.append(FloraDetection(
                id=f"FL-{i+1:04d}",
                species=species,
                common_name=common,
                confidence=round(random.uniform(0.60, 0.98), 2),
                latitude=lat,
                longitude=lng,
                timestamp=now - timedelta(days=random.randint(0, 90)),
                image_path=None,
            ))
        return sorted(detections, key=lambda d: d.timestamp, reverse=True)

    def get_flora_detections(self) -> List[FloraDetection]:
        return self._flora

    def identify_flora(self, image_bytes: bytes, lat: float, lng: float) -> FloraDetection:
        """Simulate flora identification from an uploaded image."""
        species, common = random.choice(FLORA_SPECIES)
        return FloraDetection(
            id=f"FL-NEW-{random.randint(1000,9999)}",
            species=species,
            common_name=common,
            confidence=round(random.uniform(0.70, 0.97), 2),
            latitude=lat,
            longitude=lng,
            timestamp=datetime.now(),
        )

    # ── Hydrometrics ───────────────────────────────────────

    def _generate_hydro(self, n: int) -> List[HydroMetric]:
        now = datetime.now()
        readings = []
        for i in range(n):
            station_id, station_name = random.choice(HYDRO_STATIONS)
            base_level = {"HYDRO-01": 45, "HYDRO-02": 30, "HYDRO-03": 55}[station_id]
            # Add seasonal variation and noise
            day_offset = i // 24
            seasonal = 15 * (1 + 0.5 * (day_offset % 30) / 30)
            level = base_level + seasonal + random.gauss(0, 8)
            level = max(5, level)

            if level > 120:
                alert = AlertLevel.CRITICAL
            elif level > 80:
                alert = AlertLevel.WARNING
            else:
                alert = AlertLevel.NORMAL

            readings.append(HydroMetric(
                id=f"HM-{i+1:05d}",
                station_id=station_id,
                station_name=station_name,
                water_level_cm=round(level, 1),
                flow_rate_m3s=round(level * 0.02 + random.gauss(0, 0.1), 2),
                water_temperature_c=round(8 + 6 * (day_offset % 365) / 365 + random.gauss(0, 1), 1),
                timestamp=now - timedelta(hours=i),
                alert_level=alert,
            ))
        return sorted(readings, key=lambda r: r.timestamp, reverse=True)

    def get_hydro_readings(self, hours: int = 48) -> List[HydroMetric]:
        cutoff = datetime.now() - timedelta(hours=hours)
        return [r for r in self._hydro if r.timestamp >= cutoff]

    def get_hydro_stats(self) -> dict:
        latest = {}
        for r in self._hydro:
            if r.station_id not in latest:
                latest[r.station_id] = r
        active_alerts = sum(
            1 for r in latest.values() if r.alert_level != AlertLevel.NORMAL
        )
        avg_level = sum(r.water_level_cm for r in latest.values()) / max(len(latest), 1)
        avg_flow = sum(r.flow_rate_m3s for r in latest.values()) / max(len(latest), 1)
        avg_temp = sum(r.water_temperature_c for r in latest.values()) / max(len(latest), 1)
        return {
            "avg_water_level_cm": round(avg_level, 1),
            "avg_flow_rate_m3s": round(avg_flow, 2),
            "avg_water_temp_c": round(avg_temp, 1),
            "active_alerts": active_alerts,
        }

    def get_hydro_alerts(self) -> List[HydroMetric]:
        return [r for r in self._hydro if r.alert_level != AlertLevel.NORMAL]

    # ── Carbon Capture ─────────────────────────────────────

    def _generate_carbon(self) -> List[CarbonCapture]:
        records = []
        idx = 0
        for year_offset in range(2):
            for month in range(1, 13):
                for zone_id, zone_name, area in CARBON_ZONES:
                    idx += 1
                    # Trees grow, CO2 increases over time
                    growth = 1 + 0.02 * (year_offset * 12 + month)
                    tree_count = int(area * 800 * growth + random.gauss(0, 20))
                    biomass = round(area * 120 * growth + random.gauss(0, 5), 1)
                    co2 = round(biomass * 1.83, 1)  # ~1.83 tons CO2 per ton biomass
                    records.append(CarbonCapture(
                        id=f"CC-{idx:04d}",
                        zone_id=zone_id,
                        zone_name=zone_name,
                        area_hectares=area,
                        biomass_tons=biomass,
                        co2_sequestered_tons=co2,
                        tree_count=tree_count,
                        measurement_date=date(2024 + year_offset, month, 1),
                    ))
        return sorted(records, key=lambda r: r.measurement_date, reverse=True)

    def get_carbon_data(self, months: int = 24) -> List[CarbonCapture]:
        cutoff = date.today() - timedelta(days=months * 30)
        return [r for r in self._carbon if r.measurement_date >= cutoff]

    def get_carbon_stats(self) -> dict:
        # Latest month per zone
        latest = {}
        for r in self._carbon:
            if r.zone_id not in latest:
                latest[r.zone_id] = r
        total_co2 = sum(r.co2_sequestered_tons for r in latest.values())
        total_biomass = sum(r.biomass_tons for r in latest.values())
        total_area = sum(r.area_hectares for r in latest.values())
        total_trees = sum(r.tree_count for r in latest.values())
        return {
            "total_co2_tons": round(total_co2, 1),
            "total_biomass_tons": round(total_biomass, 1),
            "co2_per_hectare": round(total_co2 / total_area, 1) if total_area else 0,
            "total_trees": total_trees,
        }
