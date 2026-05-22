"""报表工具: 周报、库存概览"""
from functools import partial
from pydantic import BaseModel
from langchain_core.tools import StructuredTool


class NoInput(BaseModel):
    pass


def _get_weekly_report(db):
    from crud import get_weekly_report as crud_report
    return crud_report(db)


def _get_inventory_overview(db):
    from models import Inventory, BorrowRecord
    from sqlalchemy import func
    from datetime import date

    total = db.query(Inventory).count()
    available = db.query(Inventory).filter(
        Inventory.borrower == None,
        ~Inventory.device_attribute.in_(['已售出', '组织售卖'])
    ).count()
    borrowed = db.query(Inventory).filter(Inventory.borrower != None).count()
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
    sold_count = db.query(Inventory).filter(
        Inventory.device_attribute.in_(['已售出', '组织售卖'])
    ).count()

    attr_dist = db.query(Inventory.device_attribute, func.count(Inventory.id)).group_by(
        Inventory.device_attribute).all()
    attr_map = {a or "未分类": c for a, c in attr_dist}

    active_iot = db.query(Inventory).filter(
        Inventory.version == '4G', Inventory.iot_card_status == '开卡'
    ).count()

    # 返回每台设备的详细信息
    all_devices = db.query(Inventory).order_by(Inventory.device_id).all()
    devices = [{
        "device_id": d.device_id, "version": d.version or "-",
        "type": d.type or "-", "packaging": d.packaging or "-",
        "device_attribute": d.device_attribute or "未分类",
        "owner": d.owner or "-", "borrower": d.borrower or "-",
        "sales_person": d.sales_person or "-", "iot_card_status": d.iot_card_status or "-"
    } for d in all_devices]

    return {
        "success": True,
        "total": total, "available": available, "borrowed": borrowed,
        "sold": sold_count, "borrow_rate": borrow_rate,
        "wifi_count": wifi_c, "g4_count": g4_c,
        "sleep_count": sleep_c, "fall_count": fall_c,
        "overdue_count": overdue_c, "active_iot_cards": active_iot,
        "attribute_distribution": attr_map,
        "devices": devices
    }


def make_report_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_get_weekly_report, db),
            name="get_weekly_report",
            description="获取本周出库统计报告。",
            args_schema=NoInput,
        ),
        StructuredTool.from_function(
            func=partial(_get_inventory_overview, db),
            name="get_inventory_overview",
            description="库存整体概览。返回总数、借用率、各属性分布、版本分布、每台设备详情。用户问'库存情况/库存概览/盘点'时使用。",
            args_schema=NoInput,
        ),
    ]
