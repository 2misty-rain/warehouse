"""报表工具: 周报、库存概览"""
from ..tool_registry import register


@register(
    name="get_weekly_report",
    description="获取本周出库统计报告。",
    parameters={}
)
def get_weekly_report(db):
    from crud import get_weekly_report as crud_report
    return crud_report(db)


@register(
    name="get_inventory_overview",
    description="库存整体概览。总数、借用率、各属性分布、型号分布、预警信息。用户问'库存情况/库存概览/盘点'时使用。",
    parameters={}
)
def get_inventory_overview(db):
    from models import Inventory, BorrowRecord
    from sqlalchemy import func
    from datetime import date

    total = db.query(Inventory).count()
    available = db.query(Inventory).filter(Inventory.borrower == None).count()
    borrowed = total - available
    borrow_rate = round((borrowed / total * 100), 1) if total > 0 else 0

    wifi_c = db.query(Inventory).filter(Inventory.version == "WiFi").count()
    g4_c = db.query(Inventory).filter(Inventory.version == "4G").count()
    sleep_c = db.query(Inventory).filter(Inventory.type == "睡眠").count()
    fall_c = db.query(Inventory).filter(Inventory.type == "跌倒").count()

    today = date.today()
    overdue_c = db.query(BorrowRecord).filter(
        BorrowRecord.status.in_(['borrowed', 'overdue']),
        BorrowRecord.expected_return_date < today
    ).count()

    attr_dist = db.query(Inventory.device_attribute, func.count(Inventory.id)).group_by(
        Inventory.device_attribute).all()
    attr_map = {a or "未分类": c for a, c in attr_dist}

    active_iot = db.query(Inventory).filter(
        Inventory.version == '4G', Inventory.iot_card_status == '开卡'
    ).count()

    return {
        "success": True,
        "total": total, "available": available, "borrowed": borrowed,
        "borrow_rate": borrow_rate, "overdue_count": overdue_c,
        "wifi_count": wifi_c, "g4_count": g4_c,
        "sleep_count": sleep_c, "fall_count": fall_c,
        "attribute_distribution": attr_map,
        "active_iot_cards": active_iot
    }
