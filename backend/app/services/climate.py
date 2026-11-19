"""Climate ingestion. NASA POWER needs no API key. IMD / ERA5 / Copernicus require manual download
or credentials -> import their exports through POST /api/climate/upload (CSV: district,date,rainfall_mm,temperature_c)."""
from datetime import date, datetime

import requests
from sqlalchemy.orm import Session

from app.models import ClimateRecord, DataSource

TN_DISTRICTS = {  # approximate centroids (lat, lon)
    "Tiruvallur": (13.14, 79.91), "Chennai": (13.08, 80.27), "Chengalpattu": (12.69, 79.98),
    "Villupuram": (11.94, 79.49), "Cuddalore": (11.75, 79.77), "Mayiladuthurai": (11.10, 79.65),
    "Nagapattinam": (10.77, 79.84), "Thanjavur": (10.79, 79.14), "Tiruvarur": (10.77, 79.64),
    "Pudukkottai": (10.38, 78.82), "Ramanathapuram": (9.37, 78.83), "Thoothukudi": (8.76, 78.13),
    "Tirunelveli": (8.73, 77.70), "Kanniyakumari": (8.18, 77.43)}
NASA = dict(name="NASA POWER (PRECTOTCORR, T2M)", url="https://power.larc.nasa.gov/",
            spatial_coverage="Global, 0.5° grid cell at point", update_frequency="Daily (few-day latency)",
            origin="public_dataset")


def source(db: Session, meta=NASA) -> DataSource:
    s = db.query(DataSource).filter_by(name=meta["name"]).first()
    if not s:
        s = DataSource(**meta, retrieved_on=date.today())
        db.add(s); db.flush()
    return s


def ingest_nasa_power(db: Session, district: str, start: date, end: date) -> int:
    lat, lon = TN_DISTRICTS[district]
    r = requests.get("https://power.larc.nasa.gov/api/temporal/daily/point", timeout=60, params={
        "parameters": "PRECTOTCORR,T2M", "community": "AG", "latitude": lat, "longitude": lon,
        "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "format": "JSON"})
    r.raise_for_status()
    p = r.json()["properties"]["parameter"]
    src, n = source(db), 0
    for d, rain in p["PRECTOTCORR"].items():
        if rain is None or rain < 0:   # NASA uses -999 for missing
            continue
        dt = datetime.strptime(d, "%Y%m%d").date()
        if db.query(ClimateRecord).filter_by(district=district, date=dt, source_id=src.id).first():
            continue
        t = p["T2M"].get(d)
        db.add(ClimateRecord(district=district, date=dt, rainfall_mm=rain,
                             temperature_c=None if t is None or t < -90 else t, source_id=src.id))
        n += 1
    db.commit()
    return n
