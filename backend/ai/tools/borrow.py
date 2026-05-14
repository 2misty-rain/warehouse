"""借用管理工具"""
from ..tool_registry import register
from schemas import BorrowRecordCreate, BorrowRecordReturn
from crud import create_borrow_record, return_device as crud_return


@register(
    name="create_borrow",
    description="借出设备给某人。设备暂时给某人使用，还会归还。",
    parameters={
        "device_id": {"type": "string", "description": "设备号", "required": True},
        "borrower": {"type": "string", "description": "借用人", "required": True},
        "expected_return_date": {"type": "string", "description": "预计归还日期 YYYY-MM-DD", "required": False},
        "purpose": {"type": "string", "description": "借用目的", "required": False},
        "remarks": {"type": "string", "description": "备注", "required": False}
    }
)
def create_borrow(db, device_id, borrower, expected_return_date=None, purpose=None, remarks=None):
    from models import Inventory
    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not device:
        return {"success": False, "message": f"设备 {device_id} 不存在"}
    if device.borrower:
        return {"success": False, "message": f"设备 {device_id} 已被 {device.borrower} 领用，请先归还"}

    data = {"device_id": device_id, "borrower": borrower, "purpose": purpose or "", "remarks": remarks or ""}
    if expected_return_date:
        from datetime import datetime
        try:
            data["expected_return_date"] = datetime.strptime(expected_return_date, '%Y-%m-%d').date()
        except ValueError:
            pass

    borrow_data = BorrowRecordCreate(**data)
    result = create_borrow_record(db, borrow_data)
    device.borrower = borrower
    if device.device_attribute == '现有库存' and purpose and '试用' in purpose:
        device.device_attribute = '商机试用'
    db.commit()
    return {"success": True, "message": f"已借出 {device_id} → {borrower}"}


@register(
    name="return_borrow",
    description="归还已借出的设备。通过设备号归还。",
    parameters={
        "device_id": {"type": "string", "description": "设备号", "required": True},
        "condition_on_return": {"type": "string", "description": "归还时设备状态", "required": False},
        "remarks": {"type": "string", "description": "备注", "required": False}
    }
)
def return_borrow(db, device_id, condition_on_return=None, remarks=None):
    from models import Inventory, BorrowRecord
    active_record = db.query(BorrowRecord).filter(
        BorrowRecord.device_id == device_id, BorrowRecord.status == 'borrowed'
    ).first()
    if not active_record:
        return {"success": False, "message": f"设备 {device_id} 没有活跃的借用记录"}

    return_data = BorrowRecordReturn(
        condition_on_return=condition_on_return or '', remarks=remarks or '')
    crud_return(db, active_record.id, return_data)

    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if device:
        device.borrower = None
        if device.device_attribute in ('商机试用', '内部试用', '产品演示'):
            device.device_attribute = '现有库存'
        db.commit()
    return {"success": True, "message": f"已归还 {device_id}"}


@register(
    name="query_overdue",
    description="查询所有逾期未还的设备。",
    parameters={}
)
def query_overdue(db):
    from models import BorrowRecord, Inventory
    from datetime import date
    today = date.today()
    records = db.query(BorrowRecord).filter(
        BorrowRecord.status.in_(['borrowed', 'overdue']),
        BorrowRecord.expected_return_date < today
    ).order_by(BorrowRecord.expected_return_date.asc()).limit(20).all()

    if not records:
        return {"success": True, "overdue_count": 0, "items": [], "message": "没有逾期设备"}

    items = []
    for r in records:
        overdue_days = (today - r.expected_return_date).days
        device = db.query(Inventory).filter(Inventory.device_id == r.device_id).first()
        items.append({
            "device_id": r.device_id, "borrower": r.borrower,
            "expected_return_date": r.expected_return_date.strftime("%Y-%m-%d"),
            "overdue_days": overdue_days,
            "version": device.version if device else "-",
            "type": device.type if device else "-"
        })

    return {"success": True, "overdue_count": len(records), "items": items}
