"""销售和统计分析工具"""
from ..tool_registry import register


@register(
    name="sell_device",
    description="销售出库。设备永久卖出不再归还。当用户说'卖给/出售/卖了'时使用。",
    parameters={
        "device_id": {"type": "string", "description": "设备号", "required": True},
        "customer": {"type": "string", "description": "客户名称/甲方", "required": True},
        "sales_person": {"type": "string", "description": "销售人员", "required": False},
        "delivery_date": {"type": "string", "description": "销售日期 YYYY-MM-DD", "required": False},
        "remarks": {"type": "string", "description": "备注", "required": False}
    }
)
def sell_device(db, device_id, customer, sales_person=None, delivery_date=None, remarks=None):
    from models import Inventory, BorrowRecord
    from datetime import datetime

    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not device:
        return {"success": False, "message": f"设备 {device_id} 不存在"}

    active_borrow = db.query(BorrowRecord).filter(
        BorrowRecord.device_id == device_id, BorrowRecord.status == 'borrowed'
    ).first()
    if active_borrow:
        active_borrow.status = 'terminated'
        active_borrow.remarks = f"设备已售出给{customer}，借用终止"
        active_borrow.actual_return_date = datetime.utcnow()

    device.borrower = None
    device.sales_person = sales_person or ''
    device.device_attribute = '组织售卖'
    device.owner = customer

    if delivery_date:
        try:
            device.delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
        except ValueError:
            device.delivery_date = datetime.utcnow().date()
    else:
        device.delivery_date = datetime.utcnow().date()

    device.remarks = f"{device.remarks or ''} | 已售给{customer}"
    if sales_person:
        device.remarks += f" 销售:{sales_person}"
    if delivery_date:
        device.remarks += f" 日期:{delivery_date}"

    db.commit()
    return {"success": True, "message": f"已售出 {device_id} → {customer}"}


@register(
    name="analyze_sales",
    description="销售统计分析。回答'卖了多少台/哪些客户买了/WiFi和4G各卖了多少'等。",
    parameters={
        "time_range": {"type": "string", "description": "时间范围: 本周/本月/本季度/今年/全部", "required": False},
        "group_by": {"type": "string", "description": "分组: owner/version/type", "required": False}
    }
)
def analyze_sales(db, time_range="全部", group_by=None):
    from crud import get_sales_analysis
    return get_sales_analysis(db, time_range=time_range, group_by=group_by)
