import io
import uuid

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from geoalchemy2.elements import WKTElement
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.security import current_user, optional_user, require
from app.config import settings
from app.database.db import get_db
from app.gis.risk import distance_to_coast_km
from app.models import AuditLog, Borewell, DataSource, UploadedDataset, User, WaterQualityRecord
from app.schemas import BorewellIn, WQIn
from app.services.quality import check_alerts, prepare_record

router = APIRouter(prefix="/api", tags=["borewells"])
STAFF = ("admin", "researcher")


def audit(db, u, action, entity, eid, detail=None):
    db.add(AuditLog(user_id=u.id if u else None, action=action, entity=entity, entity_id=eid, detail=detail))


def rec_out(r):
    return {c: getattr(r, c) for c in ("id", "borewell_id", "sampled_on", "ec_us_cm", "tds_mg_l", "ph", "chloride_mg_l", "sodium_mg_l",
            "calcium_mg_l", "magnesium_mg_l", "sar", "category", "origin", "status", "sampling_method", "source_id")}


def bw_out(b, viewer=None, history=False):
    last = b.records[-1] if b.records else None
    d = {c: getattr(b, c) for c in ("id", "code", "name", "latitude", "longitude", "village", "district", "depth_m",
         "elevation_m", "distance_to_coast_km", "origin", "status")}
    d["latest"] = rec_out(last) if last else None
    if b.show_contributor or (viewer and (viewer.id == b.contributor_id or viewer.role.name == "admin")):
        d["contributor_id"] = b.contributor_id           # privacy: hidden unless opted in / owner / admin
    if history:
        d["history"] = [rec_out(r) for r in b.records]
    return d


@router.get("/borewells")
def list_borewells(district: str | None = None, village: str | None = None, q: str | None = None,
                   origin: str | None = None, status: str | None = None,
                   page: int = Query(1, ge=1), size: int = Query(25, ge=1, le=200),
                   db: Session = Depends(get_db), viewer: User | None = Depends(optional_user)):
    qs = db.query(Borewell)
    if not viewer or viewer.role.name not in ("admin",):
        qs = qs.filter(or_(Borewell.status == "verified", Borewell.contributor_id == (viewer.id if viewer else -1)))
    if district: qs = qs.filter(Borewell.district.ilike(district))
    if village: qs = qs.filter(Borewell.village.ilike(f"%{village}%"))
    if origin: qs = qs.filter(Borewell.origin == origin)
    if status: qs = qs.filter(Borewell.status == status)
    if q: qs = qs.filter(or_(Borewell.name.ilike(f"%{q}%"), Borewell.village.ilike(f"%{q}%"), Borewell.code.ilike(f"%{q}%")))
    total = qs.count()
    items = qs.order_by(Borewell.id).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": [bw_out(b, viewer) for b in items]}


@router.post("/borewells", status_code=201)
def create_borewell(body: BorewellIn, db: Session = Depends(get_db), u: User = Depends(current_user)):
    staff = u.role.name in STAFF
    b = Borewell(**body.model_dump(exclude={"code"}), code=body.code or f"BW-{uuid.uuid4().hex[:8].upper()}",
                 geom=WKTElement(f"POINT({body.longitude} {body.latitude})", srid=4326),
                 distance_to_coast_km=distance_to_coast_km(body.latitude, body.longitude),
                 contributor_id=u.id, origin="measured_verified" if staff else "user_submitted",
                 status="verified" if u.role.name == "admin" else "pending")
    db.add(b); db.flush(); audit(db, u, "create", "borewell", b.id); db.commit()
    return bw_out(b, u)


@router.get("/borewells/{bid}")
def get_borewell(bid: int, db: Session = Depends(get_db), viewer: User | None = Depends(optional_user)):
    b = db.get(Borewell, bid)
    if not b or (b.status != "verified" and not (viewer and (viewer.role.name == "admin" or viewer.id == b.contributor_id))):
        raise HTTPException(404, "Not found")
    return bw_out(b, viewer, history=True)


@router.put("/borewells/{bid}")
def update_borewell(bid: int, body: BorewellIn, db: Session = Depends(get_db), u: User = Depends(current_user)):
    b = db.get(Borewell, bid)
    if not b: raise HTTPException(404, "Not found")
    if u.role.name != "admin" and u.id != b.contributor_id: raise HTTPException(403, "Not allowed")
    for k, v in body.model_dump(exclude={"code"}).items(): setattr(b, k, v)
    b.geom = WKTElement(f"POINT({b.longitude} {b.latitude})", srid=4326)
    b.distance_to_coast_km = distance_to_coast_km(b.latitude, b.longitude)
    audit(db, u, "update", "borewell", b.id); db.commit()
    return bw_out(b, u)


@router.delete("/borewells/{bid}", status_code=204)
def delete_borewell(bid: int, db: Session = Depends(get_db), u: User = Depends(require("admin"))):
    b = db.get(Borewell, bid)
    if not b: raise HTTPException(404, "Not found")
    audit(db, u, "delete", "borewell", bid, {"code": b.code}); db.delete(b); db.commit()


# ---------- water quality ----------
def _source(db, name, origin):
    s = db.query(DataSource).filter_by(name=name).first()
    if not s:
        s = DataSource(name=name, origin=origin); db.add(s); db.flush()
    return s


@router.post("/water-quality", status_code=201)
def add_record(body: WQIn, db: Session = Depends(get_db), u: User = Depends(current_user)):
    b = db.get(Borewell, body.borewell_id)
    if not b: raise HTTPException(404, "Borewell not found")
    if all(getattr(body, k) is None for k in ("ec_us_cm", "tds_mg_l", "chloride_mg_l", "ph")):
        raise HTTPException(422, "Provide at least one measurement")
    staff = u.role.name in STAFF
    origin = "measured_verified" if staff else "user_submitted"
    src = _source(db, body.source_name or ("Staff entry" if staff else "Citizen report"), origin)
    r = WaterQualityRecord(**body.model_dump(exclude={"source_name"}), source_id=src.id, origin=origin,
                           status="verified" if u.role.name == "admin" else "pending", submitted_by=u.id)
    prepare_record(r); db.add(r); db.flush(); db.refresh(b)
    check_alerts(db, b, r); audit(db, u, "create", "water_quality_record", r.id); db.commit()
    return rec_out(r)


@router.get("/water-quality")
def list_records(origin: str | None = None, status: str | None = "verified", limit: int = Query(100, le=1000),
                 db: Session = Depends(get_db), u: User = Depends(current_user)):
    q = db.query(WaterQualityRecord)
    if status: q = q.filter_by(status=status)
    if origin: q = q.filter_by(origin=origin)
    return [rec_out(r) for r in q.order_by(WaterQualityRecord.sampled_on.desc()).limit(limit)]


@router.get("/water-quality/{borewell_id}")
def borewell_records(borewell_id: int, db: Session = Depends(get_db), viewer: User | None = Depends(optional_user)):
    return get_borewell(borewell_id, db, viewer)["history"]


@router.post("/water-quality/{rid}/verify")
def verify(rid: int, ok: bool = True, db: Session = Depends(get_db), u: User = Depends(require("admin"))):
    r = db.get(WaterQualityRecord, rid)
    if not r: raise HTTPException(404, "Not found")
    r.status = "verified" if ok else "rejected"; audit(db, u, "verify" if ok else "reject", "water_quality_record", rid)
    db.commit(); return rec_out(r)


REQUIRED = {"borewell_code", "sampled_on", "ec_us_cm"}
NUMERIC = ["ec_us_cm", "tds_mg_l", "ph", "chloride_mg_l", "sodium_mg_l", "calcium_mg_l", "magnesium_mg_l"]


@router.post("/water-quality/upload")
async def upload(file: UploadFile = File(...), origin: str = "public_dataset", source_name: str = "Uploaded dataset",
                 db: Session = Depends(get_db), u: User = Depends(require("admin", "researcher"))):
    if origin not in ("measured_verified", "public_dataset", "user_submitted", "synthetic_demo"):
        raise HTTPException(422, "Invalid origin")
    ext = (file.filename or "").lower().rsplit(".", 1)[-1]
    if ext not in ("csv", "xlsx"): raise HTTPException(415, "Only .csv or .xlsx allowed")
    raw = await file.read()
    if len(raw) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, "File too large")
    df = pd.read_csv(io.BytesIO(raw)) if ext == "csv" else pd.read_excel(io.BytesIO(raw))
    df.columns = [c.strip().lower() for c in df.columns]
    if not REQUIRED <= set(df.columns):
        raise HTTPException(422, f"Missing columns: {sorted(REQUIRED - set(df.columns))}")
    src = _source(db, source_name, origin)
    ok, errors = 0, []
    for i, row in df.iterrows():
        try:
            b = db.query(Borewell).filter_by(code=str(row["borewell_code"])).first()
            if not b: raise ValueError("unknown borewell_code")
            vals = {k: (None if pd.isna(row.get(k)) else float(row[k])) for k in NUMERIC if k in df.columns}
            body = WQIn(borewell_id=b.id, sampled_on=pd.to_datetime(row["sampled_on"]).date(), **vals)  # validates ranges
            if db.query(WaterQualityRecord).filter_by(borewell_id=b.id, sampled_on=body.sampled_on, source_id=src.id).first():
                raise ValueError("duplicate")
            r = WaterQualityRecord(**body.model_dump(exclude={"source_name"}), source_id=src.id, origin=origin,
                                   status="verified" if (u.role.name == "admin" and origin != "user_submitted") else "pending",
                                   submitted_by=u.id)
            prepare_record(r); db.add(r); ok += 1
        except Exception as e:
            errors.append({"row": int(i) + 2, "error": str(e)[:120]})
    db.add(UploadedDataset(filename=file.filename, uploaded_by=u.id, origin=origin, rows_accepted=ok,
                           rows_rejected=len(errors), errors=errors[:50]))
    db.commit()
    return {"accepted": ok, "rejected": len(errors), "errors": errors[:50]}
