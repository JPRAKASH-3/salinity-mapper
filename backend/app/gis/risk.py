"""Measured classification + intrusion RISK scoring.

Thresholds are configurable defaults (see THRESHOLDS). They are screening values
loosely based on BIS IS 10500 (drinking water) and FAO Irrigation & Drainage
Paper 29 (Ayers & Westcot). Weights in WEIGHTS are expert heuristics and MUST be
calibrated/validated by a hydrogeologist before any decision use.
EC or TDS alone never proves seawater intrusion; this module outputs a RISK score.
"""
import math

import numpy as np
from shapely.geometry import LineString, Point

METHOD_VERSION = "risk-v1-heuristic"
THRESHOLDS = {                       # upper bounds of Low / Moderate / Elevated, else High
    "ec_us_cm": [750, 2250, 5000],
    "tds_mg_l": [500, 1500, 3000],
    "chloride_mg_l": [250, 600, 1000],
}
MEASURED_LABELS = ["Low", "Moderate", "Elevated", "High"]
WEIGHTS = {"distance": .20, "ec": .25, "chloride": .20, "trend": .10,
           "level": .10, "elevation": .05, "rainfall": .05, "na_cl": .05}
RISK_CUTS = [(25, "Low Risk"), (50, "Moderate Risk"), (75, "High Risk")]

# Generalised, APPROXIMATE Tamil Nadu coastline (lat, lon). Replace with an OSM / Natural Earth
# coastline in PostGIS (ST_Distance on geography) for production accuracy.
_TN_COAST = [(13.42, 80.32), (13.08, 80.29), (12.62, 80.20), (11.93, 79.84), (11.74, 79.78),
             (11.43, 79.78), (10.77, 79.85), (10.30, 79.87), (10.34, 79.38), (9.74, 79.01),
             (9.29, 79.31), (9.18, 79.42), (9.28, 78.90), (8.76, 78.15), (8.49, 78.12), (8.08, 77.55)]
_COAST = LineString([(lon, lat) for lat, lon in _TN_COAST])


def classify(value, key):
    if value is None:
        return None
    for i, cut in enumerate(THRESHOLDS[key]):
        if value <= cut:
            return MEASURED_LABELS[i]
    return MEASURED_LABELS[-1]


def worst_category(ec=None, tds=None, chloride=None):
    cats = [classify(v, k) for v, k in ((ec, "ec_us_cm"), (tds, "tds_mg_l"), (chloride, "chloride_mg_l")) if v is not None]
    return max(cats, key=MEASURED_LABELS.index) if cats else None


def distance_to_coast_km(lat, lon):
    """Approximate planar distance (local equirectangular scaling)."""
    k = math.cos(math.radians(lat))
    scaled = LineString([(x * k, y) for x, y in _COAST.coords])
    return round(scaled.distance(Point(lon * k, lat)) * 111.32, 2)


def sar(na_mg_l, ca_mg_l, mg_mg_l):
    if None in (na_mg_l, ca_mg_l, mg_mg_l):
        return None
    na, ca, mg = na_mg_l / 22.99, ca_mg_l / 20.04, mg_mg_l / 12.15   # meq/L
    return round(na / math.sqrt((ca + mg) / 2), 2) if (ca + mg) > 0 else None


def na_cl_molar(na_mg_l, cl_mg_l):
    if not na_mg_l or not cl_mg_l:
        return None
    return (na_mg_l / 22.99) / (cl_mg_l / 35.45)


def _clip(x):
    return float(min(1, max(0, x)))


def ec_trend_pct_per_year(dates, ec):
    """Theil-Sen slope as % of mean EC per year. Needs >=4 points over >=1 year."""
    from scipy.stats import theilslopes
    if len(ec) < 4:
        return None
    t = np.array([(d - dates[0]).days / 365.25 for d in dates])
    if t[-1] < 1:
        return None
    slope = theilslopes(ec, t)[0]
    return float(100 * slope / np.mean(ec))


def compute_risk(distance_km=None, ec=None, chloride=None, trend_pct_yr=None,
                 depth_to_water_m=None, elevation_m=None, rainfall_anomaly_pct=None,
                 na_cl=None, verified=True):
    sub = {
        "distance": None if distance_km is None else _clip(1 - distance_km / 25),
        "ec": None if ec is None else _clip((ec - 500) / 5500),
        "chloride": None if chloride is None else _clip((chloride - 100) / 900),
        "trend": None if trend_pct_yr is None else _clip(trend_pct_yr / 20),
        "level": None if depth_to_water_m is None else _clip((depth_to_water_m - 3) / 17),
        "elevation": None if elevation_m is None else _clip(1 - elevation_m / 20),
        "rainfall": None if rainfall_anomaly_pct is None else _clip(-rainfall_anomaly_pct / 50),
        "na_cl": None if (na_cl is None or (chloride or 0) < 250) else _clip(1 - abs(na_cl - 0.86) / 0.5),
    }
    avail = {k: v for k, v in sub.items() if v is not None}
    if not avail:
        return None
    wsum = sum(WEIGHTS[k] for k in avail)
    score = 100 * sum(WEIGHTS[k] * v for k, v in avail.items()) / wsum
    confidence = wsum / sum(WEIGHTS.values())
    if not verified:
        confidence *= 0.7
    cat = next((c for cut, c in RISK_CUTS if score < cut), "Very High Risk")
    factors = {k: {"subscore": round(v, 3), "weight": WEIGHTS[k]} for k, v in avail.items()}
    missing = [k for k in WEIGHTS if k not in avail]
    return {"score": round(score, 1), "category": cat, "confidence": round(confidence, 2),
            "factors": factors, "missing_inputs": missing, "method_version": METHOD_VERSION,
            "label": "Risk assessment — not confirmed saltwater intrusion"}


def detect_anomaly(ec_series):
    """Flag latest EC if robust z-score > 3.5 (MAD) or >50% jump vs previous sample."""
    if len(ec_series) < 4:
        return None
    x = np.array(ec_series, float)
    med = np.median(x[:-1])
    mad = np.median(np.abs(x[:-1] - med)) or 1e-9
    z = 0.6745 * (x[-1] - med) / mad
    jump = (x[-1] - x[-2]) / x[-2] * 100 if x[-2] else 0
    return {"robust_z": round(float(z), 2), "jump_pct": round(float(jump), 1),
            "anomalous": bool(abs(z) > 3.5 or abs(jump) > 50)}
