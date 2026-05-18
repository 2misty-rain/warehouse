from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from database import get_db
from models import User
from schemas import UserCreate, UserLogin, TokenResponse, UserResponse
from crud import get_user_by_username, create_user, get_all_users
from auth import (
    verify_password, create_access_token, get_current_user, hash_password
)

router = APIRouter(prefix="/auth", tags=["Auth"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


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
    """注册新账号，强制角色为 operator（不允许自选 admin）"""
    existing = get_user_by_username(db, user_data.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    # 强制 role=operator，防止提权
    user = create_user(db, user_data.username, user_data.password, user_data.email, "operator")
    return user


@router.get("/me", response_model=UserResponse)
def get_me(user=Depends(get_current_user)):
    return user


@router.get("/users", response_model=List[UserResponse])
def list_users(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail="权限不足，仅管理员可查看用户列表")
    return get_all_users(db)


@router.put("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改当前用户密码"""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度不能少于6位")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"success": True, "message": "密码修改成功"}


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    data: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """管理员编辑用户信息"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="权限不足，仅管理员可管理用户")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if data.email is not None:
        target_user.email = data.email
    if data.role is not None:
        if data.role not in ('admin', 'operator', 'viewer'):
            raise HTTPException(status_code=400, detail="无效的角色")
        target_user.role = data.role
    if data.is_active is not None:
        target_user.is_active = data.is_active
    if data.password:
        if len(data.password) < 6:
            raise HTTPException(status_code=400, detail="密码长度不能少于6位")
        target_user.hashed_password = hash_password(data.password)

    db.commit()
    db.refresh(target_user)
    return {"success": True, "message": "用户信息已更新"}
