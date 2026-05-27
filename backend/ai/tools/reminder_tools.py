"""提醒管理工具: 查询、创建、处理提醒"""
from functools import partial
from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool


class QueryRemindersInput(BaseModel):
    is_processed: Optional[bool] = Field(None, description="是否已处理: true=已处理, false=未处理, 不传=全部")
    reminder_type: Optional[str] = Field(None, description="提醒类型: trial_period(试用到期待处理)")

class CreateReminderInput(BaseModel):
    device_id: str = Field(..., description="设备号(必填)")
    reminder_type: str = Field("trial_period", description="提醒类型: trial_period/iot_card_expiry/custom")
    due_date: str = Field(..., description="到期日期 YYYY-MM-DD")
    description: Optional[str] = Field(None, description="提醒描述")

class ProcessReminderInput(BaseModel):
    reminder_id: int = Field(..., description="提醒ID")
    is_processed: bool = Field(True, description="是否标记为已处理")


def _query_reminders(db, is_processed=None, reminder_type=None):
    from crud import get_reminders
    records = get_reminders(db, is_processed=is_processed)
    items = [{
        "id": r.id, "device_id": r.device_id or "-",
        "reminder_type": r.reminder_type or "-",
        "due_date": str(r.due_date) if r.due_date else "-",
        "description": r.description or "", "is_processed": r.is_processed
    } for r in records]
    if reminder_type:
        items = [i for i in items if i["reminder_type"] == reminder_type]
    return {"success": True, "total": len(items), "items": items}

def _create_reminder(db, device_id: str, reminder_type: str, due_date: str, description=None):
    from schemas import ReminderCreate
    from crud import create_reminder as crud_create_reminder
    from datetime import datetime
    r = ReminderCreate(
        device_id=device_id, reminder_type=reminder_type,
        due_date=datetime.strptime(due_date, "%Y-%m-%d").date(),
        description=description or ""
    )
    result = crud_create_reminder(db, r)
    return {"success": True, "message": f"已创建提醒 (ID: {result.id})", "id": result.id}

def _process_reminder(db, reminder_id: int, is_processed: bool):
    from crud import update_reminder_status
    result = update_reminder_status(db, reminder_id, is_processed)
    if not result:
        return {"success": False, "message": f"提醒 {reminder_id} 不存在"}
    return {"success": True, "message": f"提醒 {reminder_id} 已标记为{'已处理' if is_processed else '未处理'}"}


def make_reminder_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_query_reminders, db),
            name="query_reminders",
            description="查询提醒列表。用户问'有什么提醒/待处理提醒/试用到期的设备'时使用。可筛选已处理/未处理状态和提醒类型。",
            args_schema=QueryRemindersInput,
        ),
        StructuredTool.from_function(
            func=partial(_create_reminder, db),
            name="create_reminder",
            description="创建新提醒。给设备设置试用到期待处理提醒或其他自定义提醒。",
            args_schema=CreateReminderInput,
        ),
        StructuredTool.from_function(
            func=partial(_process_reminder, db),
            name="process_reminder",
            description="处理提醒，标记为已处理或未处理。用户说'处理这个提醒/标记为已处理'时使用。",
            args_schema=ProcessReminderInput,
        ),
    ]
