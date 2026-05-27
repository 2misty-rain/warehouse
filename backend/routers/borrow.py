from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Inventory, BorrowRecord
from schemas import (
    BorrowRecordCreate, BorrowRecordReturn, BorrowRecordResponse
)
from crud import (
    create_borrow_record, get_borrow_records, get_borrow_record_by_id,
    return_device, get_overdue_borrows, update_overdue_status,
    delete_borrow_record
)
from auth import get_current_user

router = APIRouter(prefix="/borrow", tags=["Borrow"])


def _get_username(request: Request) -> str:
    return getattr(request.state, 'username', 'system')


@router.post("", response_model=BorrowRecordResponse)
def borrow_device(
    request: Request,
    borrow_record: BorrowRecordCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        device = db.query(Inventory).filter(
            Inventory.device_id == borrow_record.device_id
        ).with_for_update().first()
        if not device:
            raise ValueError(f"设备 {borrow_record.device_id} 不存在")
        if device.device_attribute != '现有库存':
            raise ValueError(f"设备 {borrow_record.device_id} 当前状态为'{device.device_attribute}'，只有'现有库存'设备可被借用")
        if device.borrower:
            raise ValueError(f"设备 {borrow_record.device_id} 已被 {device.borrower} 借用中")

        record = create_borrow_record(db, borrow_record, username=_get_username(request))
        device.borrower = borrow_record.borrower
        device.device_attribute = '商机试用'
        db.commit()
        return record
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_borrow_records(
    status: Optional[str] = None, search: str = "",
    borrow_date_start: Optional[str] = None, borrow_date_end: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return get_borrow_records(db, status=status, search=search,
                              borrow_date_start=borrow_date_start,
                              borrow_date_end=borrow_date_end,
                              skip=skip, limit=limit)


@router.get("/overdue/list")
def list_overdue_borrows(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """只读查询逾期列表（不修改状态）"""
    overdue_records = get_overdue_borrows(db)
    return {"count": len(overdue_records), "records": overdue_records}


@router.post("/overdue/refresh")
def refresh_overdue_status(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """主动刷新逾期状态"""
    count = update_overdue_status(db)
    return {"updated": count, "message": f"已刷新，{count} 条记录标记为逾期"}


@router.get("/{record_id}", response_model=BorrowRecordResponse)
def get_borrow_record(record_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    record = get_borrow_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="借用记录不存在")
    return record


@router.delete("/{record_id}")
def delete_borrow_record_endpoint(record_id: int, db: Session = Depends(get_db),
                                  user=Depends(get_current_user)):
    try:
        ok = delete_borrow_record(db, record_id)
        if not ok:
            raise HTTPException(status_code=404, detail="借用记录不存在")
        db.commit()
        return {"message": "借用记录删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{record_id}/return", response_model=BorrowRecordResponse)
def return_borrowed_device(
    request: Request,
    record_id: int,
    return_data: BorrowRecordReturn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        record = return_device(db, record_id, return_data, username=_get_username(request))
        if not record:
            raise HTTPException(status_code=404, detail="借用记录不存在")
        return record
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
