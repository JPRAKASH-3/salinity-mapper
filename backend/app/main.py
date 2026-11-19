import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import analytics, auth, borewells, maps, ml, reports
from app.config import settings
from app.database.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])
app = FastAPI(title="Coastal Saltwater Intrusion & Borewell Salinity Mapper", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_methods=["*"], allow_headers=["*"])
if settings.secret_key == "dev-only-change-me":
    logging.warning("SECRET_KEY is the dev default — set a strong value in production")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    resp = await call_next(request)
    logging.getLogger("access").info("%s %s -> %s", request.method, request.url.path, resp.status_code)
    return resp


for r in (auth, borewells, maps, ml, analytics, reports):
    app.include_router(r.router)
