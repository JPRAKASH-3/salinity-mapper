from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.security import current_user, hash_password, make_token, verify_password
from app.database.db import get_db
from app.models import User, UserRole
from app.schemas import RegisterIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=body.email.lower()).first():
        raise HTTPException(409, "Email already registered")
    role = db.query(UserRole).filter_by(name=body.role).one()
    u = User(email=body.email.lower(), full_name=body.full_name, hashed_password=hash_password(body.password),
             role_id=role.id, district=body.district)
    db.add(u); db.commit(); db.refresh(u)
    return {"access_token": make_token(u), "token_type": "bearer"}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=form.username.lower()).first()
    if not u or not verify_password(form.password, u.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": make_token(u), "token_type": "bearer"}


@router.get("/profile")
def profile(u: User = Depends(current_user)):
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role.name,
            "district": u.district, "email_alerts": u.email_alerts}


@router.put("/profile")
def update_profile(body: dict, u: User = Depends(current_user), db: Session = Depends(get_db)):
    for k in ("full_name", "district", "phone", "email_alerts"):
        if k in body:
            setattr(u, k, body[k])
    db.commit()
    return {"ok": True}
