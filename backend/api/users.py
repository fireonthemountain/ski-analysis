"""Minimal caller identification (ledger task ski-analysis-2).

Not authentication: the client states who it is in the ``X-User-Id`` header
(default ``anonymous``) and records are stored under that id instead of a
hardcoded one. Real accounts/JWT are PRODUCTION_ROADMAP work.
"""
import re
import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from config import DEFAULT_USER
from database import User, get_db

_NAMESPACE = uuid.UUID("6f1c1c0e-5d43-4c5e-9a53-0f6d4d8a3b11")
_VALID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,49}$")


def user_uuid(name: str) -> uuid.UUID:
    """Stable UUID for a user name (same name -> same id on every machine)."""
    return uuid.uuid5(_NAMESPACE, name.lower())


def get_current_user(x_user_id: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    name = (x_user_id or "").strip() or DEFAULT_USER
    if not _VALID.match(name):
        raise HTTPException(status_code=400, detail="X-User-Id must be 1-50 characters: letters, digits, . _ @ -")
    uid = user_uuid(name)
    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        user = User(id=uid, username=name.lower(), email=f"{uid.hex}@users.invalid",
                    hashed_password="!")          # no password login exists; '!' can never match a hash
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
