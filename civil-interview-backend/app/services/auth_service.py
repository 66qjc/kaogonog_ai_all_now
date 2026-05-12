"""Auth service: login and register"""
from datetime import timedelta
import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.entities import User
from app.schemas.common import RegisterRequest

logger = logging.getLogger(__name__)


def login_user(db: Session, username: str, password: str) -> dict:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        logger.warning(
            "Login failed",
            extra={"event": "auth.login.failed", "username": username, "reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        {"sub": user.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    logger.info(
        "Login succeeded",
        extra={"event": "auth.login.succeeded", "username": user.username, "role": user.role or "user"},
    )
    return {"access_token": token, "token_type": "bearer"}


def register_user(db: Session, data: RegisterRequest) -> dict:
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        logger.warning(
            "Register failed",
            extra={"event": "auth.register.failed", "username": data.username, "reason": "duplicate_username"},
        )
        raise HTTPException(status_code=400, detail="Username already registered")
    user = User(
        username=data.username,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name or data.username,
        email=data.email or "",
    )
    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning(
            "Register failed",
            extra={"event": "auth.register.failed", "username": data.username, "reason": "integrity_error"},
        )
        raise HTTPException(status_code=400, detail="Username already registered") from None
    except SQLAlchemyError:
        db.rollback()
        logger.exception(
            "Register failed",
            extra={"event": "auth.register.failed", "username": data.username, "reason": "database_error"},
        )
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试") from None
    logger.info(
        "Register succeeded",
        extra={"event": "auth.register.succeeded", "username": user.username},
    )
    return {"success": True, "message": "User created successfully"}
