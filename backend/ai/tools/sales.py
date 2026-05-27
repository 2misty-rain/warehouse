"""销售和统计分析工具"""
from functools import partial
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool


class SellDeviceInput(BaseModel):
    device_id: str = Field(..., description="设备号")
    customer: str = Field(..., description="客户名称/甲方")
    sales_person: Optional[str] = Field(None, description="销售人员")
    delivery_date: Optional[str] = Field(None, description="销售日期 YYYY-MM-DD")
    remarks: Optional[str] = Field(None, description="备注")


class AnalyzeSalesInput(BaseModel):
    time_range: Optional[str] = Field("全部", description="时间范围: 本周/本月/本季度/今年/全部")
    group_by: Optional[str] = Field(None, description="分组: owner/version/type")


def _sell_device(db, device_id: str, customer: str, sales_person=None,
                 delivery_date=None, remarks=None):
    from models import Inventory, BorrowRecord

    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not device:
        return {"success": False, "message": f"设备 {device_id} 不存在"}

    # 终止活跃借用
    active = db.query(BorrowRecord).filter(
        BorrowRecord.device_id == device_id,
        BorrowRecord.status.in_(['borrowed', 'overdue'])
    ).first()
    if active:
        active.status = 'terminated'
        active.remarks = f"{active.remarks or ''}\n(因售卖终止)"

    device.device_attribute = '商机交付'
    device.owner = customer
    if sales_person:
        device.sales_person = sales_person
    device.borrower = None
    device.delivery_date = delivery_date or datetime.utcnow().strftime('%Y-%m-%d')
    extra = f" | 销售: {sales_person}" if sales_person else ""
    device.remarks = f"{device.remarks or ''}\n[售出] → {customer}{extra}"
    db.commit()
    return {"success": True, "message": f"已售出 {device_id} → {customer}"}


def _analyze_sales(db, time_range="全部", group_by=None):
    from crud import get_sales_analysis
    return get_sales_analysis(db, time_range=time_range, group_by=group_by)


def make_sales_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_sell_device, db),
            name="sell_device",
            description="销售出库。设备永久卖出不再归还。当用户说'卖给/出售/卖了'时使用。",
            args_schema=SellDeviceInput,
        ),
        StructuredTool.from_function(
            func=partial(_analyze_sales, db),
            name="analyze_sales",
            description="销售统计分析。回答'卖了多少台/哪些客户买了/WiFi和4G各卖了多少'等问题。",
            args_schema=AnalyzeSalesInput,
        ),
    ]
