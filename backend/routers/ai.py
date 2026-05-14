"""AI 对话路由: 使用 ReAct Agent"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import logging

from database import get_db
from schemas import AIParseRequest
from ai.agent import run as agent_run
from ai.history import clear_history

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])


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
