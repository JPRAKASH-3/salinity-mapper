import enum
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (JSON, Boolean, CheckConstraint, Column, Date, DateTime, Float,
                        ForeignKey, Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import relationship

from app.database.db import Base


class Origin(str, enum.Enum):
    measured_verified = "measured_verified"
    public_dataset = "public_dataset"
    user_submitted = "user_submitted"
    synthetic_demo = "synthetic_demo"      # demo only, NEVER evidence


class Status(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


def now():
    return datetime.utcnow()


class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True, nullable=False)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(120), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role_id = Column(ForeignKey("user_roles.id"), nullable=False)
    district = Column(String(80))
    phone = Column(String(20))
    email_alerts = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)
    role = relationship("UserRole")


class DataSource(Base):
    __tablename__ = "data_sources"
    id = Column(Integer, primary_key=True)
    name = Column(String(160), unique=True, nullable=False)
    url = Column(String(400))
    spatial_coverage = Column(String(200))
    update_frequency = Column(String(80))
    origin = Column(String(30), nullable=False)
    notes = Column(Text)
    retrieved_on = Column(Date)


class Borewell(Base):
    __tablename__ = "borewells"
    id = Column(Integer, primary_key=True)
    code = Column(String(40), unique=True, nullable=False, index=True)
    name = Column(String(160), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geom = Column(Geometry("POINT", srid=4326, spatial_index=True), nullable=False)
    village = Column(String(120), index=True)
    district = Column(String(80), index=True, nullable=False)
    depth_m = Column(Float)
    elevation_m = Column(Float)
    distance_to_coast_km = Column(Float)
    contributor_id = Column(ForeignKey("users.id"))
    show_contributor = Column(Boolean, default=False)
    origin = Column(String(30), default=Origin.user_submitted.value, nullable=False)
    status = Column(String(20), default=Status.pending.value, nullable=False)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
    records = relationship("WaterQualityRecord", back_populates="borewell",
                           cascade="all, delete-orphan", order_by="WaterQualityRecord.sampled_on")
    __table_args__ = (CheckConstraint("latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180"),)


class WaterQualityRecord(Base):
    __tablename__ = "water_quality_records"
    id = Column(Integer, primary_key=True)
    borewell_id = Column(ForeignKey("borewells.id", ondelete="CASCADE"), index=True, nullable=False)
    sampled_on = Column(Date, nullable=False, index=True)
    ec_us_cm = Column(Float)           # µS/cm @25°C
    tds_mg_l = Column(Float)
    ph = Column(Float)
    chloride_mg_l = Column(Float)
    sodium_mg_l = Column(Float)
    calcium_mg_l = Column(Float)
    magnesium_mg_l = Column(Float)
    sar = Column(Float)
    sampling_method = Column(String(80))
    category = Column(String(20))      # MEASURED classification, not a prediction
    source_id = Column(ForeignKey("data_sources.id"))
    origin = Column(String(30), nullable=False)
    status = Column(String(20), default=Status.pending.value, nullable=False)
    submitted_by = Column(ForeignKey("users.id"))
    created_at = Column(DateTime, default=now)
    borewell = relationship("Borewell", back_populates="records")
    __table_args__ = (
        UniqueConstraint("borewell_id", "sampled_on", "source_id", name="uq_record"),
        CheckConstraint("ec_us_cm IS NULL OR (ec_us_cm >= 0 AND ec_us_cm <= 100000)"),
        CheckConstraint("ph IS NULL OR (ph >= 0 AND ph <= 14)"),
        CheckConstraint("tds_mg_l IS NULL OR tds_mg_l >= 0"),
        CheckConstraint("chloride_mg_l IS NULL OR chloride_mg_l >= 0"),
    )


class GroundwaterLevel(Base):
    __tablename__ = "groundwater_levels"
    id = Column(Integer, primary_key=True)
    borewell_id = Column(ForeignKey("borewells.id", ondelete="CASCADE"), index=True, nullable=False)
    measured_on = Column(Date, nullable=False)
    depth_to_water_m = Column(Float, nullable=False)
    source_id = Column(ForeignKey("data_sources.id"))
    origin = Column(String(30), nullable=False)


class ClimateRecord(Base):
    __tablename__ = "climate_records"
    id = Column(Integer, primary_key=True)
    district = Column(String(80), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    rainfall_mm = Column(Float)
    temperature_c = Column(Float)
    source_id = Column(ForeignKey("data_sources.id"), nullable=False)
    __table_args__ = (UniqueConstraint("district", "date", "source_id", name="uq_climate"),)


class SalinityRiskAssessment(Base):
    __tablename__ = "salinity_risk_assessments"
    id = Column(Integer, primary_key=True)
    borewell_id = Column(ForeignKey("borewells.id", ondelete="CASCADE"), index=True, nullable=False)
    assessed_on = Column(DateTime, default=now)
    score = Column(Float, nullable=False)
    category = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    factors = Column(JSON, nullable=False)
    method_version = Column(String(20), nullable=False)
    kind = Column(String(30), default="risk_assessment")


class PredictionResult(Base):
    __tablename__ = "prediction_results"
    id = Column(Integer, primary_key=True)
    borewell_id = Column(ForeignKey("borewells.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at = Column(DateTime, default=now)
    target = Column(String(10), default="ec_us_cm")
    horizon_days = Column(Integer, nullable=False)
    predicted = Column(Float, nullable=False)
    lower_80 = Column(Float, nullable=False)
    upper_80 = Column(Float, nullable=False)
    predicted_class = Column(String(20))
    model_version = Column(String(40), nullable=False)
    trained_on_synthetic = Column(Boolean, default=False, nullable=False)


class AgriculturalRecommendation(Base):
    __tablename__ = "agricultural_recommendations"
    id = Column(Integer, primary_key=True)
    borewell_id = Column(ForeignKey("borewells.id", ondelete="CASCADE"), index=True)
    record_id = Column(ForeignKey("water_quality_records.id"))
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=now)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("users.id"), index=True)   # null = visible to admins
    borewell_id = Column(ForeignKey("borewells.id", ondelete="CASCADE"))
    kind = Column(String(30), nullable=False)
    basis = Column(String(12), nullable=False)             # "measured" | "predicted"
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)


class UploadedDataset(Base):
    __tablename__ = "uploaded_datasets"
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    uploaded_by = Column(ForeignKey("users.id"))
    origin = Column(String(30), nullable=False)
    rows_accepted = Column(Integer, default=0)
    rows_rejected = Column(Integer, default=0)
    errors = Column(JSON)
    created_at = Column(DateTime, default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("users.id"))
    action = Column(String(60), nullable=False)
    entity = Column(String(60))
    entity_id = Column(Integer)
    detail = Column(JSON)
    created_at = Column(DateTime, default=now)
