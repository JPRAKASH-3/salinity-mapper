
"""Create an admin user and optionally seed synthetic demo borewells.

Synthetic records are marked with origin='synthetic_demo'.
This script is safe to run multiple times.
"""

import argparse
import random
from datetime import date, timedelta

from geoalchemy2.elements import WKTElement

from app.auth.security import hash_password
from app.database.db import SessionLocal, init_db
from app.gis.risk import distance_to_coast_km
from app.models import (
    Borewell,
    DataSource,
    User,
    UserRole,
    WaterQualityRecord,
)
from app.services.climate import TN_DISTRICTS
from app.services.quality import prepare_record


DEMO_SOURCE_NAME = "SYNTHETIC DEMO (not real)"


def create_admin(db, email, password):
    email = email.lower().strip()

    existing = db.query(User).filter_by(email=email).first()

    if existing:
        print(f"Admin already exists: {email}")
        return

    role = db.query(UserRole).filter_by(name="admin").one_or_none()

    if role is None:
        raise RuntimeError(
            "Admin role not found. Check your database roles."
        )

    admin = User(
        email=email,
        full_name="Administrator",
        hashed_password=hash_password(password),
        role_id=role.id,
    )

    db.add(admin)
    db.commit()

    print(f"Admin created: {email}")


def get_demo_source(db):
    src = (
        db.query(DataSource)
        .filter_by(name=DEMO_SOURCE_NAME)
        .first()
    )

    if src:
        print("Existing synthetic data source reused.")
        return src

    src = DataSource(
        name=DEMO_SOURCE_NAME,
        origin="synthetic_demo",
        notes="Randomly generated for UI testing only.",
    )

    db.add(src)
    db.flush()

    print("Synthetic data source created.")

    return src


def seed_demo(db, count):
    random.seed(7)

    src = get_demo_source(db)

    created = 0
    skipped = 0

    districts = list(TN_DISTRICTS.items())

    for i in range(count):

        code = f"DEMO-{i:03d}"

        # Prevent duplicate borewells when rerunning.
        existing = (
            db.query(Borewell)
            .filter_by(code=code)
            .first()
        )

        if existing:
            skipped += 1
            continue

        district, (lat, lon) = random.choice(districts)

        lat += random.uniform(-0.08, 0.08)
        lon += random.uniform(-0.08, 0.08)

        dist = distance_to_coast_km(lat, lon)

        borewell = Borewell(
            code=code,
            name=f"Demo borewell {i}",
            latitude=lat,
            longitude=lon,
            geom=WKTElement(
                f"POINT({lon} {lat})",
                srid=4326,
            ),
            district=district,
            village=f"Demo village {i % 12}",
            depth_m=random.uniform(20, 90),
            elevation_m=random.uniform(1, 40),
            distance_to_coast_km=dist,
            origin="synthetic_demo",
            status="verified",
        )

        db.add(borewell)

        # Insert borewell first to obtain its database ID.
        db.flush()

        base = (
            600
            + 5000 * max(0, 1 - dist / 25)
            * random.uniform(0.5, 1.2)
        )

        for k in range(6):

            ec = max(
                150,
                base
                * (1 + 0.04 * k)
                * random.uniform(0.9, 1.1),
            )

            record = WaterQualityRecord(
                borewell_id=borewell.id,
                sampled_on=(
                    date.today()
                    - timedelta(
                        days=180 * (5 - k)
                        + random.randint(0, 20)
                    )
                ),
                ec_us_cm=round(ec),
                tds_mg_l=round(ec * 0.65),
                chloride_mg_l=round(ec * 0.22),
                ph=round(random.uniform(6.8, 8.2), 1),
                source_id=src.id,
                origin="synthetic_demo",
                status="verified",
            )

            prepare_record(record)
            db.add(record)

        created += 1

    db.commit()

    print("\nDemo seeding completed.")
    print(f"New borewells: {created}")
    print(f"Existing borewells skipped: {skipped}")
    print(f"Water quality records: {created * 6}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--n", type=int, default=60)

    args = parser.parse_args()

    if args.n < 1:
        parser.error("--n must be at least 1")

    init_db()

    db = SessionLocal()

    try:
        create_admin(
            db,
            args.admin_email,
            args.admin_password,
        )

        if args.demo:
            seed_demo(db, args.n)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
