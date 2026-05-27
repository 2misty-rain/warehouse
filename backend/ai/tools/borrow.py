"""借用管理工具: 借出、归还、逾期查询"""
from functools import partial
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from datetime import date
from ai.tools.device_attr import norm_attr


class CreateBorrowInput(BaseModel):
    device_id: str = Field(..., description="设备号")
    borrower: str = Field(..., description="借用人姓名")
    expected_return_date: Optional[str] = Field(None, description="预计归还日期 YYYY-MM-DD")
    purpose: Optional[str] = Field(None, description="借用目的(试用/演示/测试等)")
    remarks: Optional[str] = Field(None, description="备注")


class ReturnBorrowInput(BaseModel):
    device_id: str = Field(..., description="设备号")
    condition_on_return: Optional[str] = Field(None, description="归还时设备状态")
    remarks: Optional[str] = Field(None, description="归还备注")


class QueryOverdueInput(BaseModel):
    pass


def _create_borrow(db, device_id: str, borrower: str, expected_return_date=None,
                   purpose=None, remarks=None):
    from models import Inventory, BorrowRecord
    from crud import create_borrow_record

    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not device:
        return {"success": False, "message": f"设备 {device_id} 不存在"}
    if device.device_attribute != '现有库存':
        return {"success": False, "message": f"设备 {device_id} 当前状态为'{device.device_attribute}'，只有'现有库存'设备可被借用"}
    if device.borrower:
        return {"success": False, "message": f"设备 {device_id} 已被 {device.borrower} 借用中"}

    from schemas import BorrowRecordCreate
    record = create_borrow_record(db, BorrowRecordCreate(
        device_id=device_id, borrower=borrower,
        expected_return_date=expected_return_date,
        purpose=purpose, remarks=remarks
    ))
    device.borrower = borrower
    device.device_attribute = '商机试用'
    db.commit()
    return {"success": True, "message": f"已借出 {device_id} → {borrower} (商机试用)", "borrow_id": record.id}


def _return_borrow(db, device_id: str, condition_on_return=None, remarks=None):
    from models import BorrowRecord, Inventory

    record = db.query(BorrowRecord).filter(
        BorrowRecord.device_id == device_id,
        BorrowRecord.status.in_(['borrowed', 'overdue'])
    ).first()
    if not record:
        return {"success": False, "message": f"设备 {device_id} 无活跃借用记录"}

    record.status = 'returned'
    record.actual_return_date = date.today()
    if condition_on_return: record.condition_on_return = condition_on_return
    if remarks: record.remarks = f"{record.remarks or ''}\n归还备注: {remarks}"

    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if device:
        device.borrower = None
        device.device_attribute = '现有库存'
        device.owner = None
        device.sales_person = None
        device.supplementary_info = None
        device.remarks = ''
        device.delivery_date = None
    db.commit()
    return {"success": True, "message": f"已归还 {device_id}，已重置为现有库存"}


def _query_overdue(db):
    from models import BorrowRecord, Inventory
    today = date.today()
    overdue = db.query(BorrowRecord).filter(
        BorrowRecord.status.in_(['borrowed', 'overdue']),
        BorrowRecord.expected_return_date < today
    ).all()
    items = []
    for r in overdue[:20]:
        device = db.query(Inventory).filter(Inventory.device_id == r.device_id).first()
        items.append({
            "borrow_id": r.id, "device_id": r.device_id,
            "borrower": r.borrower, "expected_return_date": str(r.expected_return_date),
            "overdue_days": (today - r.expected_return_date).days,
            "device_attribute": norm_attr(device.device_attribute) if device else "-"
        })
    return {"overdue_count": len(overdue), "items": items, "success": True}


def make_borrow_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_create_borrow, db),
            name="create_borrow",
            description="借出设备给某人。设备暂时给某人使用，还会归还。",
            args_schema=CreateBorrowInput,
        ),
        StructuredTool.from_function(
            func=partial(_return_borrow, db),
            name="return_borrow",
            description="归还已借出的设备。通过设备号归还。",
            args_schema=ReturnBorrowInput,
        ),
        StructuredTool.from_function(
            func=partial(_query_overdue, db),
            name="query_overdue",
            description="查询所有逾期未还的设备列表。",
            args_schema=QueryOverdueInput,
        ),
    ]
