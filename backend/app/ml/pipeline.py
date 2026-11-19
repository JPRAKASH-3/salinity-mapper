"""Salinity forecasting. Trains ONLY on real (non-synthetic) verified data and refuses when data is too thin.
Reports spatial (district/borewell-grouped) AND temporal hold-out metrics plus a persistence baseline,
so the model's skill is shown honestly. Nothing here fabricates accuracy."""
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import (confusion_matrix, f1_score, mean_absolute_error, mean_squared_error,
                             precision_score, r2_score, recall_score)
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier, XGBRegressor

from app.config import settings
from app.gis.risk import MEASURED_LABELS, THRESHOLDS
from app.models import Borewell, ClimateRecord, WaterQualityRecord

MIN_PAIRS, MIN_BOREWELLS = 200, 20
FEATURES = ["ec_now", "chloride_now", "gap_days", "dist_km", "depth_m", "rain90", "m_sin", "m_cos"]
MODEL_DIR = Path(settings.model_dir)


class InsufficientData(Exception):
    pass


def _rain90(climate, district, when):
    c = climate.get(district)
    if c is None:
        return np.nan
    w = c[(c.index > pd.Timestamp(when) - pd.Timedelta(days=90)) & (c.index <= pd.Timestamp(when))]
    return float(w.sum()) if len(w) > 60 else np.nan


def build_pairs(db, allow_synthetic=False):
    q = db.query(WaterQualityRecord, Borewell).join(Borewell).filter(
        WaterQualityRecord.status == "verified", WaterQualityRecord.ec_us_cm.isnot(None))
    if not allow_synthetic:
        q = q.filter(WaterQualityRecord.origin != "synthetic_demo")
    rows = [dict(bid=b.id, district=b.district, date=pd.Timestamp(r.sampled_on), ec=r.ec_us_cm,
                 cl=r.chloride_mg_l, dist=b.distance_to_coast_km, depth=b.depth_m,
                 synth=r.origin == "synthetic_demo") for r, b in q]
    if not rows:
        raise InsufficientData("No eligible verified records.")
    df = pd.DataFrame(rows).sort_values(["bid", "date"])
    clim = {}
    for c in db.query(ClimateRecord).all():
        clim.setdefault(c.district, []).append((c.date, c.rainfall_mm or 0))
    clim = {k: pd.Series(dict(v)).sort_index().rename_axis("d") for k, v in clim.items()}
    for k in clim:
        clim[k].index = pd.to_datetime(clim[k].index)
    out = []
    for _, g in df.groupby("bid"):
        r = g.to_dict("records")
        for a, b in zip(r[:-1], r[1:]):
            gap = (b["date"] - a["date"]).days
            if 30 <= gap <= 450:
                m = b["date"].month
                out.append(dict(bid=a["bid"], district=a["district"], t_next=b["date"], ec_now=a["ec"],
                                chloride_now=a["cl"], gap_days=gap, dist_km=a["dist"], depth_m=a["depth"],
                                rain90=_rain90(clim, a["district"], a["date"]), m_sin=np.sin(2 * np.pi * m / 12),
                                m_cos=np.cos(2 * np.pi * m / 12), ec_next=b["ec"], synth=a["synth"] or b["synth"]))
    return pd.DataFrame(out)


def _reg_metrics(y, p):
    return {"MAE": round(float(mean_absolute_error(y, p)), 1),
            "RMSE": round(float(np.sqrt(mean_squared_error(y, p))), 1), "R2": round(float(r2_score(y, p)), 3)}


def _cls(ec):
    return np.digitize(ec, THRESHOLDS["ec_us_cm"])  # 0..3


def train(db, allow_synthetic=False):
    d = build_pairs(db, allow_synthetic)
    if len(d) < MIN_PAIRS or d.bid.nunique() < MIN_BOREWELLS:
        raise InsufficientData(f"Need >= {MIN_PAIRS} consecutive-sample pairs from >= {MIN_BOREWELLS} borewells; "
                               f"have {len(d)} pairs / {d.bid.nunique()} borewells. Collect or import more real data.")
    synth = bool(d.synth.any())
    X, y = d[FEATURES], np.log1p(d.ec_next)
    mk = lambda: XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8, n_jobs=2)
    # spatial hold-out: whole districts (or borewells if few districts) are unseen in each fold
    groups = d.district if d.district.nunique() >= 4 else d.bid
    gkf = GroupKFold(n_splits=min(5, groups.nunique()))
    oof = np.expm1(cross_val_predict(mk(), X, y, cv=gkf, groups=groups))
    # temporal hold-out: train on earliest 80% of target dates
    d = d.sort_values("t_next"); cut = int(len(d) * .8)
    tr, te = d.iloc[:cut], d.iloc[cut:]
    m_t = mk().fit(tr[FEATURES], np.log1p(tr.ec_next))
    lo_t = GradientBoostingRegressor(loss="quantile", alpha=.1, n_estimators=200, max_depth=3).fit(tr[FEATURES].fillna(-1), np.log1p(tr.ec_next))
    hi_t = GradientBoostingRegressor(loss="quantile", alpha=.9, n_estimators=200, max_depth=3).fit(tr[FEATURES].fillna(-1), np.log1p(tr.ec_next))
    pt = np.expm1(m_t.predict(te[FEATURES]))
    lo, hi = np.expm1(lo_t.predict(te[FEATURES].fillna(-1))), np.expm1(hi_t.predict(te[FEATURES].fillna(-1)))
    cover = float(np.mean((te.ec_next >= lo) & (te.ec_next <= hi)))
    # classification of next-sample EC class
    yc = _cls(d.ec_next.values); le = LabelEncoder().fit(yc)
    metrics = {"trained_at": datetime.utcnow().isoformat(), "n_pairs": int(len(d)), "n_borewells": int(d.bid.nunique()),
               "contains_synthetic": synth, "spatial_holdout": _reg_metrics(np.expm1(y).values, oof),
               "temporal_holdout": _reg_metrics(te.ec_next, pt),
               "baseline_persistence_temporal": _reg_metrics(te.ec_next, te.ec_now),
               "interval_80_coverage_temporal": round(cover, 3)}
    if len(le.classes_) >= 2:
        clf = XGBClassifier(n_estimators=200, max_depth=3, learning_rate=.08)
        pc = le.inverse_transform(cross_val_predict(clf, d[FEATURES], le.transform(yc), cv=gkf,
                                                    groups=(d.district if d.district.nunique() >= 4 else d.bid)))
        labels = list(range(4))
        metrics["classification"] = {"labels": MEASURED_LABELS,
            "precision_macro": round(float(precision_score(yc, pc, average="macro", zero_division=0)), 3),
            "recall_macro": round(float(recall_score(yc, pc, average="macro", zero_division=0)), 3),
            "f1_macro": round(float(f1_score(yc, pc, average="macro", zero_division=0)), 3),
            "confusion_matrix": confusion_matrix(yc, pc, labels=labels).tolist()}
        clf.fit(d[FEATURES], le.transform(yc))
    else:
        clf = None
    final = mk().fit(X, y)
    lo_m = GradientBoostingRegressor(loss="quantile", alpha=.1, n_estimators=200, max_depth=3).fit(X.fillna(-1), y)
    hi_m = GradientBoostingRegressor(loss="quantile", alpha=.9, n_estimators=200, max_depth=3).fit(X.fillna(-1), y)
    version = datetime.utcnow().strftime("v%Y%m%d%H%M") + ("-SYNTHETIC" if synth else "")
    (MODEL_DIR / "trained").mkdir(parents=True, exist_ok=True); (MODEL_DIR / "evaluation").mkdir(parents=True, exist_ok=True)
    joblib.dump({"reg": final, "lo": lo_m, "hi": hi_m, "clf": clf, "le": le, "version": version, "synthetic": synth},
                MODEL_DIR / "trained" / "latest.joblib")
    metrics["model_version"] = version
    (MODEL_DIR / "evaluation" / "latest.json").write_text(json.dumps(metrics, indent=2))
    return metrics


def load_metrics():
    p = MODEL_DIR / "evaluation" / "latest.json"
    return json.loads(p.read_text()) if p.exists() else None


def predict(db, borewell, horizon_days):
    p = MODEL_DIR / "trained" / "latest.joblib"
    if not p.exists():
        raise InsufficientData("No trained model. Train after importing sufficient real verified data.")
    m = joblib.load(p)
    rec = [r for r in borewell.records if r.status == "verified" and r.ec_us_cm is not None]
    if not rec:
        raise InsufficientData("Borewell has no verified EC measurement.")
    last = rec[-1]
    month = (pd.Timestamp(last.sampled_on) + pd.Timedelta(days=horizon_days)).month
    clim = db.query(ClimateRecord).filter(ClimateRecord.district == borewell.district).all()
    rain = np.nan
    if clim:
        s = pd.Series({pd.Timestamp(c.date): c.rainfall_mm or 0 for c in clim}).sort_index()
        rain = _rain90({borewell.district: s}, borewell.district, last.sampled_on)
    x = pd.DataFrame([dict(ec_now=last.ec_us_cm, chloride_now=last.chloride_mg_l, gap_days=horizon_days,
                           dist_km=borewell.distance_to_coast_km, depth_m=borewell.depth_m, rain90=rain,
                           m_sin=np.sin(2 * np.pi * month / 12), m_cos=np.cos(2 * np.pi * month / 12))])[FEATURES]
    mean, lo, hi = (float(np.expm1(m[k].predict(x.fillna(-1) if k != "reg" else x)[0])) for k in ("reg", "lo", "hi"))
    lo, hi = min(lo, mean), max(hi, mean)
    cls = MEASURED_LABELS[int(m["le"].inverse_transform(m["clf"].predict(x))[0])] if m["clf"] is not None else None
    return {"predicted_ec": round(mean, 1), "lower_80": round(lo, 1), "upper_80": round(hi, 1), "predicted_class": cls,
            "model_version": m["version"], "synthetic": m["synthetic"], "label": "AI prediction — not a measurement"}
