import csv, io
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.auth.security import current_user, require
from app.database.db import get_db
from app.models import Borewell, Notification, PredictionResult, SalinityRiskAssessment, User, WaterQualityRecord
from app.services.agri import advisory
from app.services.quality import assess_borewell, retest_due

router = APIRouter(prefix="/api", tags=["reports"])
COLS = ["sampled_on", "ec_us_cm", "tds_mg_l", "ph", "chloride_mg_l", "sodium_mg_l", "calcium_mg_l", "magnesium_mg_l", "sar", "category", "origin", "status"]


def _csv(rows, header):
    s = io.StringIO(); w = csv.writer(s); w.writerow(header); w.writerows(rows); return s.getvalue()


@router.get("/reports/borewell/{bid}")
def borewell_report(bid: int, fmt: str = Query("pdf", pattern="^(pdf|csv)$"), db: Session = Depends(get_db), u: User = Depends(current_user)):
    b = db.get(Borewell, bid)
    if not b: raise HTTPException(404, "Not found")
    if fmt == "csv":
        body = _csv([[getattr(r, c) for c in COLS] for r in b.records], COLS)
        return Response(body, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={b.code}.csv"})
    rk = db.query(SalinityRiskAssessment).filter_by(borewell_id=bid).order_by(SalinityRiskAssessment.assessed_on.desc()).first() \
        or None
    pr = db.query(PredictionResult).filter_by(borewell_id=bid).order_by(PredictionResult.created_at.desc()).first()
    st, buf = getSampleStyleSheet(), io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    el = [Paragraph(f"Borewell Water-Quality Report — {b.name}", st["Title"]),
          Paragraph(f"Code {b.code} · {b.village or '-'}, {b.district} · {b.latitude:.5f}, {b.longitude:.5f} · "
                    f"{b.distance_to_coast_km} km from coast (approx.) · record status: {b.status} · origin: {b.origin}", st["Normal"]),
          Spacer(1, 10)]
    recs = [r for r in b.records if r.ec_us_cm is not None]
    if len(recs) >= 2:
        fig, ax = plt.subplots(figsize=(6.5, 2.6)); ax.plot([r.sampled_on for r in recs], [r.ec_us_cm for r in recs], marker="o", color="#087EAD")
        ax.set_ylabel("EC (µS/cm)"); ax.set_title("Measured EC history"); fig.tight_layout()
        img = io.BytesIO(); fig.savefig(img, format="png", dpi=150); plt.close(fig); img.seek(0)
        el += [Image(img, width=16*cm, height=6.4*cm), Spacer(1, 8)]
    data = [["Date", "EC", "TDS", "pH", "Cl", "Class", "Origin", "Status"]] + [
        [str(r.sampled_on), r.ec_us_cm, r.tds_mg_l, r.ph, r.chloride_mg_l, r.category, r.origin, r.status] for r in b.records[-15:]]
    t = Table(data, repeatRows=1); t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B2545")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                                           ("GRID", (0, 0), (-1, -1), .25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    el += [Paragraph("Measured values (units: EC µS/cm, TDS/Cl mg/L)", st["Heading3"]), t, Spacer(1, 8)]
    if rk:
        el.append(Paragraph(f"<b>Risk assessment</b> (heuristic {rk.method_version}; NOT confirmed intrusion): {rk.category}, score {rk.score}, "
                            f"data confidence {rk.confidence}", st["Normal"]))
    if pr:
        el.append(Paragraph(f"<b>AI prediction</b> (not a measurement), {pr.horizon_days} d: EC {pr.predicted:.0f} (80% interval {pr.lower_80:.0f}–{pr.upper_80:.0f}); "
                            f"model {pr.model_version}{' — TRAINED ON SYNTHETIC DATA' if pr.trained_on_synthetic else ''}", st["Normal"]))
    if b.records:
        ad = advisory(b.records[-1].ec_us_cm, b.records[-1].chloride_mg_l, b.records[-1].sar)
        el += [Spacer(1, 6), Paragraph(f"<b>Irrigation advisory:</b> {ad['suitability']}. {ad['disclaimer']}", st["Normal"])]
    el += [Spacer(1, 12), Paragraph(f"Generated {date.today()} by Coastal Salinity Mapper. Sources recorded per sample in the database.", st["Italic"])]
    doc.build(el); buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={b.code}.pdf"})


@router.get("/reports/district/{district}")
def district_report(district: str, db: Session = Depends(get_db), u: User = Depends(require("admin", "researcher"))):
    header = ["code", "name", "village", "distance_km", "latest_date", "ec", "tds", "chloride", "measured_class", "risk_class(assessment)", "risk_confidence", "origin", "status"]
    rows = []
    for b in db.query(Borewell).filter(Borewell.district.ilike(district)):
        r = b.records[-1] if b.records else None
        rk = db.query(SalinityRiskAssessment).filter_by(borewell_id=b.id).order_by(SalinityRiskAssessment.assessed_on.desc()).first()
        rows.append([b.code, b.name, b.village, b.distance_to_coast_km, r and r.sampled_on, r and r.ec_us_cm, r and r.tds_mg_l,
                     r and r.chloride_mg_l, r and r.category, rk and rk.category, rk and rk.confidence, b.origin, b.status])
    return Response(_csv(rows, header), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={district}_report.csv"})


# ---- notifications ----
@router.get("/notifications")
def notifications(db: Session = Depends(get_db), u: User = Depends(current_user)):
    q = db.query(Notification).filter((Notification.user_id == u.id) | ((Notification.user_id.is_(None)) & (u.role.name == "admin")))
    return [{"id": n.id, "kind": n.kind, "basis": n.basis, "message": n.message, "is_read": n.is_read, "created_at": n.created_at,
             "borewell_id": n.borewell_id} for n in q.order_by(Notification.created_at.desc()).limit(100)]


@router.post("/notifications")
def create_notification(body: dict, db: Session = Depends(get_db), u: User = Depends(require("admin"))):
    n = Notification(user_id=body.get("user_id"), borewell_id=body.get("borewell_id"), kind=body.get("kind", "retest"),
                     basis=body.get("basis", "measured"), message=body["message"])
    db.add(n); db.commit(); return {"id": n.id}


@router.post("/notifications/{nid}/read")
def mark_read(nid: int, db: Session = Depends(get_db), u: User = Depends(current_user)):
    n = db.get(Notification, nid)
    if n: n.is_read = True; db.commit()
    return {"ok": True}


@router.post("/notifications/retest-sweep")
def retest_sweep(db: Session = Depends(get_db), u: User = Depends(require("admin"))):
    from app.utils.notify import notify
    due = retest_due(db)
    for b in due:
        notify(db, "retest", "measured", f"{b.name} ({b.district}) has no sample in the last 12 months — retest due.", b.id)
    return {"notified": len(due)}
