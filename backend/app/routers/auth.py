import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Organization, Role, User
from ..schemas import Login, Refresh, RegisterCustomer, RegisterOrg, TokenPair, UserOut
from ..security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    login_limiter,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _pair(user: User) -> TokenPair:
    return TokenPair(access_token=create_access_token(user.id), refresh_token=create_refresh_token(user.id))


@router.post("/register-org", response_model=TokenPair, status_code=201)
def register_org(data: RegisterOrg, db: Session = Depends(get_db)):
    """Creates a new tenant and its first admin."""
    if db.scalar(select(Organization).where(Organization.slug == data.org_slug)):
        raise HTTPException(409, "Organization slug already taken")
    org = Organization(name=data.org_name, slug=data.org_slug)
    db.add(org)
    db.flush()
    user = User(org_id=org.id, email=data.email.lower(), full_name=data.full_name, password_hash=hash_password(data.password), role=Role.admin)
    db.add(user)
    db.commit()
    return _pair(user)


@router.post("/register", response_model=TokenPair, status_code=201)
def register_customer(data: RegisterCustomer, db: Session = Depends(get_db)):
    org = db.scalar(select(Organization).where(Organization.slug == data.org_slug))
    if org is None:
        raise HTTPException(404, "Organization not found")
    user = User(org_id=org.id, email=data.email.lower(), full_name=data.full_name, password_hash=hash_password(data.password), role=Role.customer)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered")
    return _pair(user)


@router.post("/login", response_model=TokenPair)
def login(data: Login, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    if not login_limiter.allow(f"login:{ip}", settings.login_rate_limit, settings.login_rate_window_seconds):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts, try again later")
    user = db.scalar(
        select(User).join(Organization).where(Organization.slug == data.org_slug, User.email == data.email.lower())
    )
    # Same error for unknown user and wrong password: no account enumeration.
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return _pair(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(data: Refresh, db: Session = Depends(get_db)):
    try:
        user_id = decode_token(data.refresh_token, "refresh")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    return _pair(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
