from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import require
from app.database.db import get_db
from app.ml import pipeline
from app.models import Borewell, PredictionResult
from app.schemas import PredictIn

router = APIRouter(prefix="/api/ml", tags=["ml"])
ELIGIBLE = ("admin", "researcher", "farmer")


@router.post("/train")
def train(allow_synthetic: bool = False, db: Session = Depends(get_db), u=Depends(require("admin"))):
    try:
        return pipeline.train(db, allow_synthetic)
    except pipeline.InsufficientData as e:
        raise HTTPException(422, str(e))


@router.post("/predict")
def predict(body: PredictIn, db: Session = Depends(get_db), u=Depends(require(*ELIGIBLE))):
    b = db.get(Borewell, body.borewell_id)
    if not b: raise HTTPException(404, "Borewell not found")
    try:
        out = pipeline.predict(db, b, body.horizon_days)
    except pipeline.InsufficientData as e:
        raise HTTPException(422, str(e))
    db.add(PredictionResult(borewell_id=b.id, horizon_days=body.horizon_days, predicted=out["predicted_ec"],
           lower_80=out["lower_80"], upper_80=out["upper_80"], predicted_class=out["predicted_class"],
           model_version=out["model_version"], trained_on_synthetic=out["synthetic"]))
    db.commit()
    return out


@router.get("/predictions/{borewell_id}")
def predictions(borewell_id: int, db: Session = Depends(get_db), u=Depends(require(*ELIGIBLE))):
    rows = db.query(PredictionResult).filter_by(borewell_id=borewell_id).order_by(PredictionResult.created_at.desc()).limit(50)
    return [{"created_at": r.created_at, "horizon_days": r.horizon_days, "predicted_ec": r.predicted, "lower_80": r.lower_80,
             "upper_80": r.upper_80, "predicted_class": r.predicted_class, "model_version": r.model_version,
             "trained_on_synthetic": r.trained_on_synthetic, "label": "AI prediction — not a measurement"} for r in rows]


@router.get("/model-performance")
def performance(u=Depends(require(*ELIGIBLE))):
    m = pipeline.load_metrics()
    if not m:
        return {"trained": False, "message": "No model trained yet. Requires sufficient real verified data; no accuracy is shown until then."}
    return {"trained": True, **m}
