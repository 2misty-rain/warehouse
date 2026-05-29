"""
工具箱路由 — 账号管理
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from auth import get_current_user

router = APIRouter(prefix="/toolbox", tags=["Toolbox"])

IDC_URL = "mysql+pymysql://root:123456@localhost/wechat_idc"


def _get_idc():
    return create_engine(IDC_URL)


# ============== 请求模型 ==============

class AccountCreate(BaseModel):
    organization_id: int = Field(..., description="所属机构ID")
    account: str = Field(..., min_length=3, max_length=50, description="登录账号")
    display_name: str = Field(..., min_length=1, max_length=50, description="显示名称")
    password: str = Field(..., min_length=6, max_length=64, description="密码(至少6位)")
    phone_number: Optional[str] = Field(None, max_length=20, description="手机号")
    remark: Optional[str] = Field(None, max_length=100, description="备注")


class AccountUpdate(BaseModel):
    display_name: Optional[str] = None
    password: Optional[str] = None
    phone_number: Optional[str] = None
    remark: Optional[str] = None


class AccountResetToken(BaseModel):
    """重置 access_token"""


# ============== API ==============

class OrgCreate(BaseModel):
    organization_name: str
    organization_short_name: str
    title: Optional[str] = None
    organization_nature: Optional[int] = 1
    province_code: Optional[str] = None
    city_code: Optional[str] = None
    region_code: Optional[str] = None
    address: Optional[str] = None
    center_lng: Optional[float] = None
    center_lat: Optional[float] = None


@router.post("/organizations/create")
def create_organization(req: OrgCreate, user=Depends(get_current_user)):
    """创建新机构"""
    idc = _get_idc()
    now = datetime.utcnow()
    with idc.connect() as conn:
        existing = conn.execute(text(
            "SELECT id FROM life_radar_organization WHERE organization_short_name=:n AND del_flag=0"
        ), {"n": req.organization_short_name}).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail=f"简称'{req.organization_short_name}'已存在")

        conn.execute(text("""
            INSERT INTO life_radar_organization
            (organization_name, organization_short_name, title, organization_nature,
             province_code, city_code, region_code, address, center_lng, center_lat, created_time, del_flag)
            VALUES (:n,:s,:t,:nat,:p,:c,:r,:a,:lng,:lat,:ct,0)
        """), {
            "n": req.organization_name, "s": req.organization_short_name, "t": req.title or "",
            "nat": req.organization_nature or 1, "p": req.province_code or "", "c": req.city_code or "",
            "r": req.region_code or "", "a": req.address or "",
            "lng": req.center_lng, "lat": req.center_lat,
            "ct": now.strftime("%Y-%m-%d %H:%M:%S"),
        })
        conn.commit()
    return {"success": True, "message": f"机构'{req.organization_short_name}'创建成功"}


@router.get("/organizations")
def list_organizations(search: Optional[str] = None, user=Depends(get_current_user)):
    """获取机构列表（从生命雷达机构表）"""
    idc = _get_idc()
    with idc.connect() as conn:
        if search:
            rows = conn.execute(text(
                "SELECT id, organization_short_name, organization_name, title, address "
                "FROM life_radar_organization WHERE del_flag=0 AND "
                "(organization_name LIKE :s OR organization_short_name LIKE :s) "
                "ORDER BY id"
            ), {"s": f"%{search}%"}).fetchall()
        else:
            rows = conn.execute(text(
                "SELECT id, organization_short_name, organization_name, title, address "
                "FROM life_radar_organization WHERE del_flag=0 ORDER BY id"
            )).fetchall()

    orgs = []
    for r in rows:
        orgs.append({
            "id": r[0],
            "short_name": r[1] or "",
            "name": r[2] or "",
            "title": r[3] or "",
            "address": r[4] or "",
        })
    return {"success": True, "organizations": orgs}


@router.get("/organizations/{org_id}")
def get_organization(org_id: int, user=Depends(get_current_user)):
    """获取机构详情及下属账号"""
    idc = _get_idc()
    with idc.connect() as conn:
        org = conn.execute(text(
            "SELECT id, organization_short_name, organization_name, title, address, "
            "center_lng, center_lat, defend_days, none_defend_days "
            "FROM life_radar_organization WHERE id=:id AND del_flag=0"
        ), {"id": org_id}).fetchone()
        if not org:
            raise HTTPException(status_code=404, detail="机构不存在")

        accounts = conn.execute(text(
            "SELECT id, account, display_name, phone_number, remark, created_time, "
            "access_token, access_token_expiry_time "
            "FROM life_radar_account WHERE organization_id=:oid AND del_flag=0 ORDER BY id"
        ), {"oid": org_id}).fetchall()

    return {
        "success": True,
        "organization": {
            "id": org[0],
            "short_name": org[1],
            "name": org[2],
            "title": org[3],
            "address": org[4],
            "lng": float(org[5]) if org[5] else None,
            "lat": float(org[6]) if org[6] else None,
            "defend_days": org[7] or 0,
            "none_defend_days": org[8] or 0,
        },
        "accounts": [
            {
                "id": a[0],
                "account": a[1],
                "display_name": a[2],
                "phone_number": a[3] or "",
                "remark": a[4] or "",
                "created_time": a[5].strftime("%Y-%m-%d %H:%M") if a[5] else "",
                "has_token": bool(a[6]),
                "token_expiry": a[7].strftime("%Y-%m-%d %H:%M") if a[7] else "",
            }
            for a in accounts
        ],
    }


@router.post("/accounts")
def create_account(req: AccountCreate, user=Depends(get_current_user)):
    """创建账号"""
    idc = _get_idc()
    now = datetime.utcnow()

    # 验证机构存在
    with idc.connect() as conn:
        org = conn.execute(text(
            "SELECT id FROM life_radar_organization WHERE id=:id AND del_flag=0"
        ), {"id": req.organization_id}).fetchone()
        if not org:
            raise HTTPException(status_code=404, detail="机构不存在")

        # 检查账号是否重复
        dup = conn.execute(text(
            "SELECT id FROM life_radar_account WHERE account=:acc AND del_flag=0"
        ), {"acc": req.account}).fetchone()
        if dup:
            raise HTTPException(status_code=400, detail=f"账号 '{req.account}' 已存在")

        # 密码 MD5
        pwd_md5 = hashlib.md5(req.password.encode()).hexdigest()

        # 生成 access_token
        access_token = secrets.token_urlsafe(32)
        token_expiry = now + timedelta(days=365)

        conn.execute(text("""
            INSERT INTO life_radar_account
            (organization_id, account, display_name, password, phone_number, remark,
             created_by, created_time, access_token, access_token_expiry_time, del_flag)
            VALUES (:oid, :acc, :dn, :pw, :ph, :rm, :cb, :ct, :tok, :texp, 0)
        """), {
            "oid": req.organization_id,
            "acc": req.account,
            "dn": req.display_name,
            "pw": pwd_md5,
            "ph": req.phone_number or "",
            "rm": req.remark or "",
            "cb": 1,
            "ct": now.strftime("%Y-%m-%d %H:%M:%S"),
            "tok": access_token,
            "texp": token_expiry.strftime("%Y-%m-%d %H:%M:%S"),
        })
        conn.commit()

    return {
        "success": True,
        "message": f"账号 '{req.account}' 创建成功",
        "account": req.account,
        "display_name": req.display_name,
        "access_token": access_token,
    }


@router.put("/accounts/{account_id}")
def update_account(account_id: int, req: AccountUpdate, user=Depends(get_current_user)):
    """更新账号信息"""
    idc = _get_idc()
    now = datetime.utcnow()

    with idc.connect() as conn:
        existing = conn.execute(text(
            "SELECT id, account FROM life_radar_account WHERE id=:id AND del_flag=0"
        ), {"id": account_id}).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="账号不存在")

        updates = []
        params = {"id": account_id, "ut": now.strftime("%Y-%m-%d %H:%M:%S")}

        if req.display_name is not None:
            updates.append("display_name = :dn")
            params["dn"] = req.display_name
        if req.password is not None:
            updates.append("password = :pw")
            params["pw"] = hashlib.md5(req.password.encode()).hexdigest()
        if req.phone_number is not None:
            updates.append("phone_number = :ph")
            params["ph"] = req.phone_number
        if req.remark is not None:
            updates.append("remark = :rm")
            params["rm"] = req.remark

        if updates:
            updates.append("updated_time = :ut")
            conn.execute(text(
                f"UPDATE life_radar_account SET {', '.join(updates)} WHERE id = :id"
            ), params)
            conn.commit()

    return {"success": True, "message": "账号已更新"}


@router.post("/accounts/{account_id}/reset-token")
def reset_account_token(account_id: int, user=Depends(get_current_user)):
    """重置 access_token"""
    idc = _get_idc()
    now = datetime.utcnow()
    new_token = secrets.token_urlsafe(32)
    token_expiry = now + timedelta(days=365)

    with idc.connect() as conn:
        existing = conn.execute(text(
            "SELECT id FROM life_radar_account WHERE id=:id AND del_flag=0"
        ), {"id": account_id}).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="账号不存在")

        conn.execute(text(
            "UPDATE life_radar_account SET access_token=:tok, access_token_expiry_time=:texp, updated_time=:ut WHERE id=:id"
        ), {
            "tok": new_token,
            "texp": token_expiry.strftime("%Y-%m-%d %H:%M:%S"),
            "ut": now.strftime("%Y-%m-%d %H:%M:%S"),
            "id": account_id,
        })
        conn.commit()

    return {"success": True, "access_token": new_token}


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, user=Depends(get_current_user)):
    """软删除账号"""
    idc = _get_idc()
    with idc.connect() as conn:
        existing = conn.execute(text(
            "SELECT id FROM life_radar_account WHERE id=:id AND del_flag=0"
        ), {"id": account_id}).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="账号不存在")

        conn.execute(text(
            "UPDATE life_radar_account SET del_flag=1 WHERE id=:id"
        ), {"id": account_id})
        conn.commit()

    return {"success": True, "message": "账号已删除"}
