from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database.db import get_db
from app.models import User

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    return bcrypt.checkpw(p.encode()[:72], h.encode())


def make_token(user: User) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user.id), "role": user.role.name, "exp": exp}, settings.secret_key, "HS256")


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        uid = int(jwt.decode(token, settings.secret_key, ["HS256"])["sub"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    u = db.get(User, uid)
    if not u or not u.is_active:
        raise HTTPException(401, "Inactive user")
    return u


def optional_user(token: str | None = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)),
                  db: Session = Depends(get_db)):
    return current_user(token, db) if token else None


def require(*roles):
    def dep(u: User = Depends(current_user)):
        if u.role.name not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return u
    return dep
