from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.gis import risk
from app.models import (Borewell, ClimateRecord, GroundwaterLevel, SalinityRiskAssessment,
                        User, UserRole, WaterQualityRecord)
from app.utils.notify import notify

RETEST_DAYS = 365


def prepare_record(rec: WaterQualityRecord):
    rec.sar = risk.sar(rec.sodium_mg_l, rec.calcium_mg_l, rec.magnesium_mg_l)
    rec.category = risk.worst_category(rec.ec_us_cm, rec.tds_mg_l, rec.chloride_mg_l)


def check_alerts(db: Session, b: Borewell, rec: WaterQualityRecord):
    admins = db.query(User).join(UserRole).filter(UserRole.name == "admin").all()
    if rec.category in ("Elevated", "High"):
        notify(db, "measured_exceedance", "measured",
               f"{b.name} ({b.district}) measured {rec.category} salinity on {rec.sampled_on} "
               f"(EC {rec.ec_us_cm}, TDS {rec.tds_mg_l}, Cl {rec.chloride_mg_l}); status: {rec.status}.",
               b.id, admins or None)
    hist = [r.ec_us_cm for r in b.records if r.ec_us_cm is not None]
    an = risk.detect_anomaly(hist)
    if an and an["anomalous"]:
        notify(db, "rapid_change", "measured",
               f"{b.name}: EC changed {an['jump_pct']}% vs previous sample (robust z={an['robust_z']}).",
               b.id, admins or None)


def assess_borewell(db: Session, b: Borewell, persist=True):
    recs = [r for r in b.records if r.status != "rejected" and r.ec_us_cm is not None]
    last = b.records[-1] if b.records else None
    if not last:
        return None
    gw = db.query(GroundwaterLevel).filter_by(borewell_id=b.id).order_by(GroundwaterLevel.measured_on.desc()).first()
    trend = risk.ec_trend_pct_per_year([r.sampled_on for r in recs], [r.ec_us_cm for r in recs]) if recs else None
    since = date.today() - timedelta(days=365)
    rain_now = db.query(ClimateRecord).filter(ClimateRecord.district == b.district, ClimateRecord.date >= since).all()
    anomaly = None
    if rain_now:   # compare last-12-month total with the district's long-term mean annual total
        allr = db.query(ClimateRecord).filter(ClimateRecord.district == b.district).all()
        yrs = {r.date.year for r in allr}
        if len(yrs) >= 3:
            mean_annual = sum(r.rainfall_mm or 0 for r in allr) / len(yrs)
            anomaly = 100 * (sum(r.rainfall_mm or 0 for r in rain_now) - mean_annual) / mean_annual if mean_annual else None
    out = risk.compute_risk(
        distance_km=b.distance_to_coast_km, ec=last.ec_us_cm, chloride=last.chloride_mg_l, trend_pct_yr=trend,
        depth_to_water_m=gw.depth_to_water_m if gw else None, elevation_m=b.elevation_m,
        rainfall_anomaly_pct=anomaly, na_cl=risk.na_cl_molar(last.sodium_mg_l, last.chloride_mg_l),
        verified=last.status == "verified")
    if out and persist:
        db.add(SalinityRiskAssessment(borewell_id=b.id, score=out["score"], category=out["category"],
                                      confidence=out["confidence"], factors=out["factors"],
                                      method_version=out["method_version"]))
        db.commit()
    return out


def retest_due(db: Session):
    cutoff = date.today() - timedelta(days=RETEST_DAYS)
    return [b for b in db.query(Borewell).all() if not b.records or b.records[-1].sampled_on < cutoff]
