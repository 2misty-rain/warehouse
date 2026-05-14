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
    return_device, get_overdue_borrows, update_overdue_status
)
from auth import get_optional_user

router = APIRouter(prefix="/borrow", tags=["Borrow"])


def _get_username(request: Request) -> str:
    return getattr(request.state, 'username', 'system')


@router.post("", response_model=BorrowRecordResponse)
def borrow_device(
    request: Request,
    borrow_record: BorrowRecordCreate,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user)
):
    try:
        record = create_borrow_record(db, borrow_record, username=_get_username(request))
        device = db.query(Inventory).filter(Inventory.device_id == borrow_record.device_id).first()
        if device:
            device.borrower = borrow_record.borrower
            if device.device_attribute == '现有库存':
                purpose = (borrow_record.purpose or '').lower()
                if '试用' in purpose:
                    device.device_attribute = '商机试用'
                elif '演示' in purpose or '展示' in purpose:
                    device.device_attribute = '产品演示'
                elif '测试' in purpose or '开发' in purpose or '技术' in purpose:
                    device.device_attribute = '技术开发/测试'
                else:
                    device.device_attribute = '内部试用'
            db.commit()
        return record
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_borrow_records(
    status: Optional[str] = None, search: str = "",
    borrow_date_start: Optional[str] = None, borrow_date_end: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db)
):
    return get_borrow_records(db, status=status, search=search,
                              borrow_date_start=borrow_date_start,
                              borrow_date_end=borrow_date_end,
                              skip=skip, limit=limit)


@router.get("/overdue/list")
def list_overdue_borrows(db: Session = Depends(get_db)):
    overdue_count = update_overdue_status(db)
    overdue_records = get_overdue_borrows(db)
    return {"count": len(overdue_records), "updated": overdue_count, "records": overdue_records}


@router.get("/{record_id}", response_model=BorrowRecordResponse)
def get_borrow_record(record_id: int, db: Session = Depends(get_db)):
    record = get_borrow_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="借用记录不存在")
    return record


@router.delete("/{record_id}")
def delete_borrow_record_endpoint(record_id: int, db: Session = Depends(get_db),
                                  user=Depends(get_optional_user)):
    from crud import delete_borrow_record
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
    user=Depends(get_optional_user)
):
    try:
        record = return_device(db, record_id, return_data, username=_get_username(request))
        if not record:
            raise HTTPException(status_code=404, detail="借用记录不存在")
        return record
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
