"""出库预约路由"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from schemas import ReservationCreate, ReservationApprove, ReservationReject
from crud import (
    create_reservation, get_reservations, get_reservation_by_id,
    approve_reservation, fulfill_reservation, reject_reservation,
    get_pending_reservations_count
)
from auth import get_current_user

router = APIRouter(prefix="/reservation", tags=["Reservation"])


def _get_username(request: Request) -> str:
    return getattr(request.state, 'username', 'system')


@router.post("")
def submit_reservation(
    request: Request,
    data: ReservationCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """提交出库预约申请（任何登录用户）"""
    try:
        reservation = create_reservation(
            db, data.model_dump(), applicant=_get_username(request)
        )
        return {"success": True, "message": "申请已提交", "id": reservation.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_reservations(
    request: Request,
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """列表：admin看全部，operator只看自己的"""
    username = _get_username(request)
    role = getattr(request.state, 'role', 'viewer')

    if role == 'admin':
        applicant = None  # 看全部
    else:
        applicant = username  # 只看自己的

    return get_reservations(db, applicant=applicant, status=status, skip=skip, limit=limit)


@router.get("/pending-count")
def pending_count(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """待处理申请数（admin仪表盘用）"""
    return {"count": get_pending_reservations_count(db)}


@router.get("/{reservation_id}")
def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    reservation = get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="申请不存在")
    return reservation


@router.post("/{reservation_id}/approve")
def approve(
    request: Request,
    reservation_id: int,
    data: ReservationApprove,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """管理员审批通过 + 分配设备号 + 自动执行出库"""
    role = getattr(request.state, 'role', 'viewer')
    if role != 'admin':
        raise HTTPException(status_code=403, detail="仅管理员可审批")

    try:
        approve_reservation(
            db, reservation_id,
            assigned_devices=data.assigned_devices,
            admin_username=_get_username(request),
            admin_remarks=data.admin_remarks
        )
        # 审批通过后立即执行出库
        result = fulfill_reservation(db, reservation_id, _get_username(request))
        return {
            "success": True,
            "message": f"审批完成，已出库 {len(result['fulfilled'])} 台设备",
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{reservation_id}/reject")
def reject(
    request: Request,
    reservation_id: int,
    data: ReservationReject,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """管理员驳回申请"""
    role = getattr(request.state, 'role', 'viewer')
    if role != 'admin':
        raise HTTPException(status_code=403, detail="仅管理员可审批")

    try:
        reject_reservation(
            db, reservation_id,
            admin_username=_get_username(request),
            admin_remarks=data.admin_remarks
        )
        return {"success": True, "message": "申请已驳回"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
