from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models

    with engine.begin() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for name in ("admin", "farmer", "researcher", "public"):
            if not db.query(models.UserRole).filter_by(name=name).first():
                db.add(models.UserRole(name=name))
        db.commit()
