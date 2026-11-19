import json
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from shapely.geometry import MultiPoint, mapping
from sqlalchemy.orm import Session

from app.auth.security import optional_user
from app.database.db import get_db
from app.models import Borewell, SalinityRiskAssessment
from app.services.quality import assess_borewell

router = APIRouter(prefix="/api/maps", tags=["maps"])
RAW = Path(__file__).resolve().parents[3] / "data" / "raw"


def _visible(db, viewer):
    q = db.query(Borewell)
    return q if viewer and viewer.role.name == "admin" else q.filter(Borewell.status == "verified")


def _latest_risk(db, b):
    r = db.query(SalinityRiskAssessment).filter_by(borewell_id=b.id).order_by(SalinityRiskAssessment.assessed_on.desc()).first()
    return r


@router.get("/borewells")
def borewells_geojson(bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat"),
                      district: str | None = None, db: Session = Depends(get_db), viewer=Depends(optional_user)):
    q = _visible(db, viewer)
    if district: q = q.filter(Borewell.district.ilike(district))
    if bbox:
        x1, y1, x2, y2 = map(float, bbox.split(","))
        q = q.filter(Borewell.longitude.between(x1, x2), Borewell.latitude.between(y1, y2))
    feats = []
    for b in q.limit(5000):
        last = b.records[-1] if b.records else None
        rk = _latest_risk(db, b)
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [b.longitude, b.latitude]},
            "properties": {"id": b.id, "name": b.name, "village": b.village, "district": b.district,
                "distance_to_coast_km": b.distance_to_coast_km, "origin": b.origin,
                "measured_category": last.category if last else None,   # MEASURED
                "ec_us_cm": last.ec_us_cm if last else None, "sampled_on": str(last.sampled_on) if last else None,
                "record_status": last.status if last else None,
                "risk_category": rk.category if rk else None,           # ASSESSED risk (separate field)
                "risk_confidence": rk.confidence if rk else None}})
    return {"type": "FeatureCollection", "features": feats}


@router.get("/heatmap")
def heatmap(db: Session = Depends(get_db), viewer=Depends(optional_user)):
    """[lat, lon, intensity 0-1] from MEASURED EC (log-scaled 200–10000 µS/cm)."""
    import math
    pts = []
    for b in _visible(db, viewer):
        if b.records and b.records[-1].ec_us_cm:
            v = (math.log10(max(b.records[-1].ec_us_cm, 200)) - math.log10(200)) / (math.log10(10000) - math.log10(200))
            pts.append([b.latitude, b.longitude, round(min(v, 1), 3)])
    return pts


@router.get("/risk-zones")
def risk_zones(db: Session = Depends(get_db), viewer=Depends(optional_user)):
    """Indicative convex hulls around High/Very High risk borewells per district (>=3 points). Not delineated aquifer boundaries."""
    groups = defaultdict(list)
    for b in _visible(db, viewer):
        rk = _latest_risk(db, b) or None
        if rk and rk.category in ("High Risk", "Very High Risk"):
            groups[b.district].append((b.longitude, b.latitude))
    feats = [{"type": "Feature", "geometry": mapping(MultiPoint(p).convex_hull),
              "properties": {"district": d, "n_borewells": len(p), "label": "Indicative risk zone (assessment, not confirmed intrusion)"}}
             for d, p in groups.items() if len(p) >= 3]
    return {"type": "FeatureCollection", "features": feats}


@router.get("/boundaries")
def boundaries(level: str = "districts"):
    """Serves data/raw/<level>.geojson. Add Survey of India / GADM / OSM-derived boundaries there (not bundled for licensing)."""
    p = RAW / f"{level}.geojson"
    if level not in ("districts", "villages", "coastline") or not p.exists():
        raise HTTPException(404, f"Place a {level}.geojson file in data/raw/")
    return json.loads(p.read_text())
