# Coastal Saltwater Intrusion & Borewell Salinity Mapper

Full-stack GIS + ML platform for coastal groundwater salinity (starting with Tamil Nadu).
FastAPI · PostgreSQL/PostGIS · React + TypeScript + Leaflet · XGBoost/scikit-learn.

## Run locally
```bash
docker compose up -d db                       # PostGIS
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env     # set SECRET_KEY
python -m scripts.seed_demo --admin-email you@x.org --admin-password 'StrongPass123' --demo   # --demo = SYNTHETIC UI data
uvicorn app.main:app --reload                 # http://localhost:8000/docs
cd ../frontend && npm install && npm run dev  # http://localhost:5173
pytest backend/tests                          # unit tests (risk, SAR, blending, anomaly)
```
After seeding: sign in as admin → Admin → "Assess all borewells". Optional: `POST /api/climate/ingest?district=Cuddalore&start=2020-01-01&end=2024-12-31` (NASA POWER, no key).

## Data integrity rules built in
- Every sample stores origin (`measured_verified | public_dataset | user_submitted | synthetic_demo`), source, date, units, status.
- Measured class, risk assessment and AI prediction are separate fields/labels everywhere (UI, alerts, PDF).
- ML refuses to train below 200 consecutive-sample pairs / 20 borewells, ignores synthetic data unless `?allow_synthetic=true` (model then stamped SYNTHETIC). Reported metrics: spatial + temporal hold-out vs a "no change" baseline; nothing is hard-coded.
- Dashboard numbers are computed from the DB.

## Known gaps / next steps (honest status)
- Coastline is a generalised polyline; load an OSM/Natural Earth coastline into PostGIS (`ST_Distance` on geography) for accuracy. Put `districts.geojson` / `villages.geojson` in `data/raw/` for boundary layers.
- Risk weights are expert heuristics; calibrate with hydrogeologists + real data. Thresholds are in `app/gis/risk.py`.
- Not yet built: Alembic migrations, SMS gateway, IoT ingestion, district/village PDF (CSV exists), user-management UI, Redis caching, e2e tests. IMD/ERA5/Copernicus need manual download/credentials → use `/api/climate/upload`.
- Deploy: frontend → Vercel (`VITE_API_URL`=backend URL), backend → Render (start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`), DB → managed Postgres with PostGIS (Supabase/Neon/Render).
- Not executed end-to-end in the authoring sandbox (no network/DB): run the steps above and report issues.
"# salinity-mapper" 
