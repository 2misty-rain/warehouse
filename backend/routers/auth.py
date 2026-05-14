from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from schemas import UserCreate, UserLogin, TokenResponse, UserResponse
from crud import get_user_by_username, create_user, get_all_users
from auth import (
    verify_password, create_access_token, get_current_user, require_role
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = get_user_by_username(db, login_data.username)
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    token = create_access_token(data={"sub": user.username, "role": user.role})
    return TokenResponse(
        access_token=token,
        username=user.username,
        role=user.role
    )


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_username(db, user_data.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = create_user(db, user_data.username, user_data.password, user_data.email, user_data.role)
    return user


@router.get("/me", response_model=UserResponse)
def get_me(user=Depends(get_current_user)):
    return user


@router.get("/users", response_model=List[UserResponse])
def list_users(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail="权限不足，仅管理员可查看用户列表")
    return get_all_users(db)
