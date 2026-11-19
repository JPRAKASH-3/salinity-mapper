from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)
    role: str = Field(default="public", pattern="^(farmer|researcher|public)$")  # admin is never self-assigned
    district: Optional[str] = None


class BorewellIn(BaseModel):
    code: Optional[str] = None
    name: str = Field(min_length=2, max_length=160)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    village: Optional[str] = None
    district: str
    depth_m: Optional[float] = Field(default=None, ge=0, le=2000)
    elevation_m: Optional[float] = None
    show_contributor: bool = False


class WQIn(BaseModel):
    borewell_id: int
    sampled_on: date
    ec_us_cm: Optional[float] = Field(default=None, ge=0, le=100000)
    tds_mg_l: Optional[float] = Field(default=None, ge=0, le=100000)
    ph: Optional[float] = Field(default=None, ge=0, le=14)
    chloride_mg_l: Optional[float] = Field(default=None, ge=0)
    sodium_mg_l: Optional[float] = Field(default=None, ge=0)
    calcium_mg_l: Optional[float] = Field(default=None, ge=0)
    magnesium_mg_l: Optional[float] = Field(default=None, ge=0)
    sampling_method: Optional[str] = None
    source_name: Optional[str] = None


class PredictIn(BaseModel):
    borewell_id: int
    horizon_days: int = Field(default=180, ge=30, le=450)
