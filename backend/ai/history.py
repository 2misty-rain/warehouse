"""
对话历史管理：内存 + 数据库双存储
"""
import logging

logger = logging.getLogger(__name__)

conversation_histories = {}


def get_history(db, user_id: str = "default", limit: int = 20) -> list:
    """获取对话历史，内存优先，数据库兜底"""
    mem = conversation_histories.get(user_id, [])
    if mem:
        return mem
    if db:
        try:
            from crud import load_conversation_history
            db_history = load_conversation_history(db, user_id, limit=limit)
            if db_history:
                conversation_histories[user_id] = db_history
                return db_history
        except Exception as e:
            logger.debug(f"从数据库恢复对话历史失败: {e}")
    return []


def add_to_history(db, user_id: str, role: str, content: str):
    """添加消息到历史"""
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []
    conversation_histories[user_id].append({"role": role, "content": content})
    if len(conversation_histories[user_id]) > 40:
        conversation_histories[user_id] = conversation_histories[user_id][-40:]
    try:
        from crud import save_conversation_history
        save_conversation_history(db, user_id, role, content)
    except Exception as e:
        logger.debug(f"对话持久化失败: {e}")


def clear_history(user_id: str):
    """清空对话历史"""
    if user_id in conversation_histories:
        del conversation_histories[user_id]
