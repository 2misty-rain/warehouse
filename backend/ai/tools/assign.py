"""设备分配工具: smart_assign_device"""
from ..tool_registry import register


@register(
    name="smart_assign_device",
    description="智能设备分配。将设备分配为试用/演示/开发等状态。'XX设备给XX试用了'→商机试用。'内部试用'→内部试用。注意：售卖场景用 sell_device 工具。",
    parameters={
        "device_id": {"type": "string", "description": "设备号", "required": True},
        "assign_type": {"type": "string", "description": "分配类型: 商机试用/内部试用/产品演示/技术开发测试/特殊占用/现有库存/异常处理", "required": True},
        "target_owner": {"type": "string", "description": "甲方/客户/组织", "required": False},
        "borrower": {"type": "string", "description": "领用人", "required": False},
        "expected_return_date": {"type": "string", "description": "预计归还日期 YYYY-MM-DD。商机试用必填", "required": False},
        "sales_person": {"type": "string", "description": "销售人员", "required": False},
        "delivery_date": {"type": "string", "description": "交付日期 YYYY-MM-DD", "required": False},
        "remarks": {"type": "string", "description": "备注", "required": False}
    }
)
def smart_assign_device(db, device_id, assign_type, target_owner=None, borrower=None,
                        expected_return_date=None, sales_person=None, delivery_date=None, remarks=None):
    from models import Inventory
    from schemas import BorrowRecordCreate, ReminderCreate
    from crud import create_borrow_record, create_reminder
    from datetime import datetime

    if assign_type == '商机试用' and not expected_return_date:
        return {"success": False, "message": "商机试用需要归还日期，请提供预计归还时间（如'下周五'、'3天后'）", "needs_return_date": True}

    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not device:
        return {"success": False, "message": f"设备 {device_id} 不存在"}

    device.device_attribute = assign_type
    if delivery_date:
        try:
            device.delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
        except ValueError:
            device.delivery_date = datetime.utcnow().date()
    else:
        device.delivery_date = datetime.utcnow().date()

    if target_owner: device.owner = target_owner
    if borrower: device.borrower = borrower
    if sales_person: device.sales_person = sales_person
    if remarks: device.remarks = f"{device.remarks or ''} | {remarks}"

    if assign_type == '商机试用' and expected_return_date:
        try:
            return_date = datetime.strptime(expected_return_date, '%Y-%m-%d').date()
            bd = BorrowRecordCreate(device_id=device_id, borrower=borrower or '未知',
                                    expected_return_date=return_date,
                                    purpose=f"商机试用-{target_owner or '未知甲方'}",
                                    remarks=remarks or '')
            create_borrow_record(db, bd)
            rem = ReminderCreate(device_id=device_id, reminder_type='trial_period',
                                 due_date=return_date,
                                 description=f"商机试用到期: {target_owner or '未知'}")
            create_reminder(db, rem)
        except ValueError:
            pass

    db.commit()
    return {"success": True, "message": f"设备 {device_id} 已设置为 {assign_type}"}
