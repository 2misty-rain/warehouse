"""AI 对话路由: 使用 ReAct Agent"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import date, timedelta
import logging

from database import get_db
from schemas import AIParseRequest
from ai.agent import run as agent_run
from ai.history import clear_history
from models import Inventory, BorrowRecord, Reminders

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/suggestions")
def ai_suggestions(db: Session = Depends(get_db)):
    """根据实时库存状态生成智能建议"""
    today = date.today()
    suggestions = []

    # 检查逾期设备
    overdue_count = db.query(BorrowRecord).filter(
        BorrowRecord.status.in_(['borrowed', 'overdue']),
        BorrowRecord.expected_return_date < today
    ).count()
    if overdue_count > 0:
        suggestions.append({"text": f"当前有{overdue_count}台设备逾期未还，查看详情？", "type": "query"})

    # 检查即将到期的试用
    upcoming_trial = db.query(Reminders).filter(
        Reminders.reminder_type == 'trial_period',
        Reminders.is_processed == False,
        Reminders.due_date >= today,
        Reminders.due_date <= today + timedelta(days=7)
    ).count()
    if upcoming_trial > 0:
        suggestions.append({"text": f"未来7天有{upcoming_trial}台设备试用即将到期", "type": "query"})

    # 检查4G设备未设置IoT卡
    unset_iot_4g = db.query(Inventory).filter(
        Inventory.version == '4G',
        (Inventory.iot_card_status == None) | (Inventory.iot_card_status == '')
    ).count()
    if unset_iot_4g > 0:
        suggestions.append({"text": f"有{unset_iot_4g}台4G设备未设置IoT卡状态", "type": "query"})

    # 检查可用库存不足（少于5台）
    available = db.query(Inventory).filter(Inventory.borrower == None).count()
    if available < 5:
        suggestions.append({"text": f"可用库存仅剩{available}台，需要补充吗？", "type": "query"})

    # 查询类的默认建议
    suggestions.append({"text": "当前库存情况如何？", "type": "query"})
    suggestions.append({"text": "截止到现在卖了多少台设备？", "type": "query"})
    suggestions.append({"text": "本周出库了多少设备？", "type": "query"})

    # 操作类的默认建议
    suggestions.append({"text": "设备 DEV001 给某客户试用了，预计下周五还回", "type": "operation"})
    suggestions.append({"text": "设备 DEV001 的物联网卡开卡了", "type": "operation"})

    return {"success": True, "suggestions": suggestions}


@router.post("/chat")
def ai_chat(request: AIParseRequest, db: Session = Depends(get_db)):
    """AI 对话: 自然语言 → Agent 多轮推理 → 直接操作数据库 → 返回结果"""
    try:
        user_id = getattr(request, 'user_id', 'default') or 'default'
        result = agent_run(db, request.user_input, user_id)
        return result
    except Exception as e:
        logger.error(f"AI对话错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-history")
def clear_chat_history(user_id: str = "default"):
    """清空对话历史"""
    clear_history(user_id)
    return {"success": True, "message": "对话历史已清空"}
