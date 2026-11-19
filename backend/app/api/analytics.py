from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.auth.security import optional_user, require
from app.database.db import get_db
from app.models import (Borewell, ClimateRecord, DataSource, GroundwaterLevel, SalinityRiskAssessment,
                        WaterQualityRecord)
from app.services import climate as climate_svc
from app.services.agri import advisory, blending
from app.services.quality import assess_borewell, retest_due

router = APIRouter(prefix="/api", tags=["analytics"])


def _latest_risk_map(db):
    sub = db.query(SalinityRiskAssessment.borewell_id, func.max(SalinityRiskAssessment.assessed_on).label("m")).group_by(
        SalinityRiskAssessment.borewell_id).subquery()
    rows = db.query(SalinityRiskAssessment).join(sub, (SalinityRiskAssessment.borewell_id == sub.c.borewell_id) &
                                                 (SalinityRiskAssessment.assessed_on == sub.c.m)).all()
    return {r.borewell_id: r for r in rows}


@router.get("/analytics/overview")
def overview(db: Session = Depends(get_db), viewer=Depends(optional_user)):
    """All numbers computed live from stored records; includes origin breakdown so synthetic data is visible."""
    risks = _latest_risk_map(db)
    cats = defaultdict(int)
    for r in risks.values(): cats[r.category] += 1
    dist = defaultdict(int)
    for (c,) in db.query(WaterQualityRecord.category).filter(WaterQualityRecord.status == "verified"): dist[c or "Unclassified"] += 1
    origin = dict(db.query(Borewell.origin, func.count()).group_by(Borewell.origin).all())
    return {"total_borewells": db.query(Borewell).count(),
            "verified_samples": db.query(WaterQualityRecord).filter_by(status="verified").count(),
            "risk_low": cats["Low Risk"], "risk_moderate": cats["Moderate Risk"],
            "risk_high": cats["High Risk"] + cats["Very High Risk"], "unassessed": db.query(Borewell).count() - len(risks),
            "requiring_retest": len(retest_due(db)), "measured_distribution": dist, "borewells_by_origin": origin,
            "contains_synthetic_demo": origin.get("synthetic_demo", 0) > 0}


@router.post("/analytics/assess-all")
def assess_all(db: Session = Depends(get_db), u=Depends(require("admin", "researcher"))):
    n = 0
    for b in db.query(Borewell).filter_by(status="verified"):
        if assess_borewell(db, b): n += 1
    return {"assessed": n}


@router.get("/analytics/districts")
def districts(db: Session = Depends(get_db)):
    q = db.query(Borewell.district, func.count(func.distinct(Borewell.id)), func.avg(WaterQualityRecord.ec_us_cm),
                 func.avg(WaterQualityRecord.tds_mg_l), func.avg(WaterQualityRecord.chloride_mg_l)
                 ).join(WaterQualityRecord, isouter=True).filter(Borewell.status == "verified").group_by(Borewell.district)
    risks = _latest_risk_map(db); by = defaultdict(lambda: defaultdict(int))
    for b in db.query(Borewell).filter_by(status="verified"):
        if b.id in risks: by[b.district][risks[b.id].category] += 1
    return [{"district": d, "borewells": n, "avg_ec": ec and round(ec), "avg_tds": t and round(t), "avg_chloride": c and round(c),
             "risk_counts": by[d]} for d, n, ec, t, c in q]


@router.get("/analytics/historical")
def historical(district: str | None = None, borewell_id: int | None = None, freq: str = Query("month", pattern="^(month|year)$"),
               db: Session = Depends(get_db)):
    q = db.query(extract("year", WaterQualityRecord.sampled_on).label("y"),
                 extract("month", WaterQualityRecord.sampled_on).label("m") if freq == "month" else func.literal(1).label("m"),
                 func.avg(WaterQualityRecord.ec_us_cm), func.avg(WaterQualityRecord.tds_mg_l), func.count()
                 ).join(Borewell).filter(WaterQualityRecord.status == "verified")
    if district: q = q.filter(Borewell.district.ilike(district))
    if borewell_id: q = q.filter(Borewell.id == borewell_id)
    rows = q.group_by("y", "m").order_by("y", "m").all()
    return [{"period": f"{int(y)}-{int(m):02d}" if freq == "month" else str(int(y)), "avg_ec": ec and round(ec, 1),
             "avg_tds": t and round(t, 1), "n": n} for y, m, ec, t, n in rows]


@router.get("/analytics/rainfall-vs-salinity")
def rain_vs_sal(district: str, db: Session = Depends(get_db)):
    """Monthly rainfall and mean EC for a district, plus Spearman correlation when >=12 paired months. Association != causation."""
    rain = {(int(y), int(m)): r for y, m, r in db.query(extract("year", ClimateRecord.date), extract("month", ClimateRecord.date),
            func.sum(ClimateRecord.rainfall_mm)).filter(ClimateRecord.district.ilike(district)).group_by(1, 2)}
    ec = {(int(y), int(m)): e for y, m, e in db.query(extract("year", WaterQualityRecord.sampled_on), extract("month", WaterQualityRecord.sampled_on),
          func.avg(WaterQualityRecord.ec_us_cm)).join(Borewell).filter(Borewell.district.ilike(district), WaterQualityRecord.status == "verified").group_by(1, 2)}
    keys = sorted(set(rain) | set(ec)); paired = [k for k in keys if k in rain and k in ec]; rho = None
    if len(paired) >= 12:
        from scipy.stats import spearmanr
        rho = round(float(spearmanr([rain[k] for k in paired], [ec[k] for k in paired])[0]), 3)
    return {"series": [{"period": f"{y}-{m:02d}", "rainfall_mm": rain.get((y, m)), "avg_ec": ec.get((y, m))} for y, m in keys],
            "paired_months": len(paired), "spearman_rho": rho}


# ---- climate ----
@router.get("/climate/rainfall")
def rainfall(district: str | None = None, db: Session = Depends(get_db)):
    q = db.query(ClimateRecord.district, extract("year", ClimateRecord.date), extract("month", ClimateRecord.date),
                 func.sum(ClimateRecord.rainfall_mm), ClimateRecord.source_id).group_by(1, 2, 3, 5).order_by(1, 2, 3)
    if district: q = q.filter(ClimateRecord.district.ilike(district))
    src = {s.id: s for s in db.query(DataSource)}
    return [{"district": d, "period": f"{int(y)}-{int(m):02d}", "rainfall_mm": round(r or 0, 1), "source": src[s].name,
             "update_frequency": src[s].update_frequency, "coverage": src[s].spatial_coverage} for d, y, m, r, s in q]


@router.get("/climate/temperature")
def temperature(district: str | None = None, db: Session = Depends(get_db)):
    q = db.query(ClimateRecord.district, extract("year", ClimateRecord.date), extract("month", ClimateRecord.date),
                 func.avg(ClimateRecord.temperature_c)).filter(ClimateRecord.temperature_c.isnot(None)).group_by(1, 2, 3).order_by(1, 2, 3)
    if district: q = q.filter(ClimateRecord.district.ilike(district))
    return [{"district": d, "period": f"{int(y)}-{int(m):02d}", "avg_temp_c": round(t, 2)} for d, y, m, t in q]


@router.post("/climate/ingest")
def ingest(district: str, start: date, end: date, db: Session = Depends(get_db), u=Depends(require("admin"))):
    if district not in climate_svc.TN_DISTRICTS: raise HTTPException(422, "Unknown district")
    try:
        return {"inserted": climate_svc.ingest_nasa_power(db, district, start, end)}
    except Exception as e:
        raise HTTPException(502, f"NASA POWER request failed: {e}")


@router.post("/climate/upload")
async def climate_upload(source_name: str, file: UploadFile = File(...), db: Session = Depends(get_db), u=Depends(require("admin", "researcher"))):
    """CSV columns: district,date,rainfall_mm,temperature_c — for IMD / ERA5 / Copernicus exports."""
    import io, pandas as pd
    df = pd.read_csv(io.BytesIO(await file.read()))
    src = climate_svc.source(db, dict(name=source_name, url=None, spatial_coverage="As provided", update_frequency="Manual upload", origin="public_dataset"))
    n = 0
    for r in df.itertuples():
        db.add(ClimateRecord(district=r.district, date=pd.to_datetime(r.date).date(), rainfall_mm=r.rainfall_mm,
                             temperature_c=getattr(r, "temperature_c", None), source_id=src.id)); n += 1
    db.commit(); return {"inserted": n}


# ---- agriculture ----
@router.get("/agri/advisory/{borewell_id}")
def agri(borewell_id: int, db: Session = Depends(get_db)):
    b = db.get(Borewell, borewell_id)
    if not b or not b.records: raise HTTPException(404, "No data")
    r = b.records[-1]
    return {"borewell": b.name, "based_on_sample": str(r.sampled_on), "record_status": r.status, **advisory(r.ec_us_cm, r.chloride_mg_l, r.sar)}


@router.get("/agri/blend")
def blend(ec_saline: float, ec_fresh: float, target_ec: float):
    out = blending(ec_saline, ec_fresh, target_ec)
    if not out: raise HTTPException(422, "Need ec_fresh < target_ec <= ec_saline")
    return out
