"""Authentication endpoints: register, login, refresh."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.exceptions import ConflictError, PermissionDeniedError

from database import get_db
from config import settings
from services.auth.dependency import get_current_user
from models.user import User
from schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, UserResponse
from services.auth.password import hash_password, verify_password
from services.auth.jwt import JWTError, create_access_token, create_refresh_token, decode_token

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password."""
    if settings.auth_provider == "supabase":
        raise HTTPException(403, "Public registration is disabled. Contact the instance administrator.")
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise ConflictError("Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse(id=str(user.id), email=user.email, name=user.name)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password, returns JWT tokens."""
    if settings.auth_provider == "supabase":
        from services.auth.supabase import exchange_token
        return await exchange_token("password", {"email": body.email, "password": body.password})
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise PermissionDeniedError("Account disabled")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using a valid refresh token."""
    if settings.auth_provider == "supabase":
        from services.auth.supabase import exchange_token
        return await exchange_token("refresh_token", {"refresh_token": body.refresh_token})
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except HTTPException:
        raise
    except (JWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserResponse)
async def current_user(user: User = Depends(get_current_user)):
    return UserResponse(id=str(user.id), email=user.email, name=user.name)


@router.post("/logout", status_code=204)
async def logout(request: Request, user: User = Depends(get_current_user)):
    if settings.auth_provider == "supabase":
        from services.auth.supabase import auth_request
        await auth_request("POST", "logout?scope=local", token=request.headers["authorization"].split(" ", 1)[1])
