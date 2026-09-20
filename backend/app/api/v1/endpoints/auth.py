from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.auth import get_current_active_user, require_roles
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdateRole,
    LoginRequest,
    Token
)

router = APIRouter()


@router.post(
    "/login",
    response_model=Token,
    summary="Local authentication login",
    description="Authenticates local user credentials and issues a cryptographically signed HMAC-SHA256 JWT access token."
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
) -> Token:
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact an administrator."
        )

    token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )

    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user
    )


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Creates a new local user account and automatically signs them in, returning a JWT access token."
)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db)
) -> Token:
    # Check if username exists
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with username '{payload.username}' already exists."
        )

    # Check if email exists
    if payload.email:
        existing_email = db.query(User).filter(User.email == payload.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email '{payload.email}' already exists."
            )

    role_str = payload.role.value if hasattr(payload.role, "value") else str(payload.role)
    hashed_pw = get_password_hash(payload.password)
    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_pw,
        role=role_str,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(
        data={"sub": new_user.username, "role": new_user.role}
    )

    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=new_user
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile and role",
    description="Returns the profile and privilege level for the currently authenticated user."
)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    return current_user


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all users (Admin only)",
    description="Lists all local accounts and their assigned RBAC roles."
)
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN"))
) -> List[UserResponse]:
    return db.query(User).order_by(User.created_at.asc()).all()


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (Admin only)",
    description="Creates a new local user with specified role and salted bcrypt password hash."
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN"))
) -> UserResponse:
    # Check for existing username
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with username '{payload.username}' already exists."
        )

    # Check for existing email if provided
    if payload.email:
        existing_email = db.query(User).filter(User.email == payload.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email '{payload.email}' already exists."
            )

    hashed_pw = get_password_hash(payload.password)
    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_pw,
        role=payload.role.value if hasattr(payload.role, "value") else str(payload.role),
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Update user role (Admin only)",
    description="Elevates or restricts the RBAC role of a local user."
)
def update_user_role(
    user_id: str,
    payload: UserUpdateRole,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found."
        )

    # Prevent demoting the last admin
    if user.role == "ADMIN" and payload.role != "ADMIN":
        admin_count = db.query(User).filter(User.role == "ADMIN", User.is_active == True).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last remaining active administrator."
            )

    user.role = payload.role.value if hasattr(payload.role, "value") else str(payload.role)
    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/users/{user_id}",
    summary="Delete user (Admin only)",
    description="Deletes a user account. Prevents deleting own active account or the last remaining administrator."
)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN"))
):
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own active administrator account."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found."
        )

    if user.role == "ADMIN":
        admin_count = db.query(User).filter(User.role == "ADMIN", User.is_active == True).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last remaining active administrator."
            )

    db.delete(user)
    db.commit()
    return {"status": "SUCCESS", "message": f"User '{user.username}' successfully deleted."}
