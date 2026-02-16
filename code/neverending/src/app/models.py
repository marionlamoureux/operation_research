from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import Enum
from typing import Optional


class AlertLevel(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class FaunaDetection(BaseModel):
    id: str
    species: str
    common_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    camera_id: str
    latitude: float
    longitude: float
    timestamp: datetime
    image_path: Optional[str] = None


class FloraDetection(BaseModel):
    id: str
    species: str
    common_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    latitude: float
    longitude: float
    timestamp: datetime
    image_path: Optional[str] = None


class HydroMetric(BaseModel):
    id: str
    station_id: str
    station_name: str
    water_level_cm: float
    flow_rate_m3s: float
    water_temperature_c: float
    timestamp: datetime
    alert_level: AlertLevel = AlertLevel.NORMAL


class CarbonCapture(BaseModel):
    id: str
    zone_id: str
    zone_name: str
    area_hectares: float
    biomass_tons: float
    co2_sequestered_tons: float
    tree_count: int
    measurement_date: date
