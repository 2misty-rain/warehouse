"""待处理告警工具: 主动查询逾期、试用到期待处理等告警的详细列表"""
from functools import partial
from pydantic import BaseModel
from langchain_core.tools import StructuredTool


class NoInput(BaseModel):
    pass


def _get_pending_alerts(db):
    from models import BorrowRecord, Reminders, Inventory
    from datetime import date, timedelta
    today = date.today()

    # 逾期借用
    overdue_records = db.query(BorrowRecord).filter(
        BorrowRecord.status.in_(['borrowed', 'overdue']),
        BorrowRecord.expected_return_date < today
    ).all()
    overdue_items = [{
        "device_id": r.device_id, "borrower": r.borrower,
        "expected_return_date": str(r.expected_return_date),
        "overdue_days": (today - r.expected_return_date).days,
        "status": r.status
    } for r in overdue_records]

    # 试用到期待处理
    upcoming_trials = db.query(Reminders).filter(
        Reminders.reminder_type == 'trial_period',
        Reminders.is_processed == False,
        Reminders.due_date >= today,
        Reminders.due_date <= today + timedelta(days=7)
    ).all()
    trial_items = [{
        "id": r.id, "device_id": r.device_id or "-",
        "due_date": str(r.due_date), "description": r.description or ""
    } for r in upcoming_trials]

    # 4G未设IoT卡
    unset_iot = db.query(Inventory).filter(
        Inventory.version == '4G',
        (Inventory.iot_card_status == None) | (Inventory.iot_card_status == '')
    ).all()
    iot_items = [{"device_id": d.device_id, "type": d.type or "-"} for d in unset_iot]

    return {
        "success": True,
        "overdue_count": len(overdue_items), "overdue_items": overdue_items,
        "upcoming_trial_count": len(trial_items), "upcoming_trial_items": trial_items,
        "unset_iot_count": len(iot_items), "unset_iot_items": iot_items
    }


def make_alert_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_get_pending_alerts, db),
            name="get_pending_alerts",
            description="获取所有待处理告警的详细列表。包括: 逾期未还设备(含逾期天数)、7天内到期的试用品、4G设备未设IoT卡。用户问'有什么告警/异常/待处理'时使用。",
            args_schema=NoInput,
        ),
    ]
