"""设备分配工具"""
from functools import partial
from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool


class SmartAssignInput(BaseModel):
    device_id: str = Field(..., description="设备号")
    assign_type: str = Field(..., description="分配类型: 商机试用/内部试用/产品演示/技术开发测试/特殊占用/现有库存/异常处理")
    target_owner: Optional[str] = Field(None, description="甲方/客户/组织")
    borrower: Optional[str] = Field(None, description="领用人")
    expected_return_date: Optional[str] = Field(None, description="预计归还日期 YYYY-MM-DD。商机试用必填")
    sales_person: Optional[str] = Field(None, description="销售人员")
    delivery_date: Optional[str] = Field(None, description="交付日期 YYYY-MM-DD")
    remarks: Optional[str] = Field(None, description="备注")


def _smart_assign(db, device_id: str, assign_type: str, target_owner=None, borrower=None,
                  expected_return_date=None, sales_person=None, delivery_date=None, remarks=None):
    from models import Inventory, BorrowRecord, Reminders

    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not device:
        return {"success": False, "message": f"设备 {device_id} 不存在"}

    if assign_type == '商机试用' and not expected_return_date:
        return {"success": False, "message": "商机试用必须提供预计归还日期"}

    device.device_attribute = assign_type
    if target_owner: device.owner = target_owner
    if borrower: device.borrower = borrower
    if sales_person: device.sales_person = sales_person
    if delivery_date: device.delivery_date = delivery_date
    if remarks: device.remarks = f"{device.remarks or ''}\n{remarks}"

    # 商机试用自动创建借用记录和提醒
    if assign_type == '商机试用' and borrower and expected_return_date:
        borrow = BorrowRecord(
            device_id=device_id, borrower=borrower,
            expected_return_date=expected_return_date,
            purpose=f"商机试用: {remarks or ''}", status='borrowed'
        )
        db.add(borrow)

        reminder = Reminders(
            device_id=device_id, reminder_type='trial_period',
            due_date=expected_return_date,
            description=f"设备 {device_id} 商机试用到期待处理"
        )
        db.add(reminder)

    db.commit()
    return {"success": True, "message": f"已分配 {device_id} → {assign_type}"}


def make_assign_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_smart_assign, db),
            name="smart_assign_device",
            description="智能设备分配。将设备分配为试用/演示/开发等状态。'XX设备给XX试用了'→商机试用。注意：售卖场景用 sell_device。",
            args_schema=SmartAssignInput,
        ),
    ]
