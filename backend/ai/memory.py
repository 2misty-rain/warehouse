"""
对话记忆管理：LangChain BaseChatMessageHistory 包装现有 DB
"""
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)
WINDOW_SIZE = 12  # 保留最近 6 轮对话（每轮 user+assistant 共 2 条）


class InventoryChatMessageHistory(BaseChatMessageHistory):
    """包装 conversation_history 表的 LangChain 记忆"""

    def __init__(self, user_id: str, db: Session):
        self._user_id = user_id
        self._db = db
        self._messages: list = []
        self._load_from_db()

    def _load_from_db(self):
        try:
            from crud import load_conversation_history
            records = load_conversation_history(self._db, self._user_id, limit=WINDOW_SIZE)
            for r in records:
                if r["role"] == "user":
                    self._messages.append(HumanMessage(content=r["content"]))
                else:
                    self._messages.append(AIMessage(content=r["content"]))
        except Exception as e:
            logger.debug(f"加载对话历史失败: {e}")

    @property
    def messages(self) -> list:
        return self._messages

    def add_message(self, message) -> None:
        self._messages.append(message)
        # 限制窗口大小
        if len(self._messages) > WINDOW_SIZE * 2:
            self._messages = self._messages[-(WINDOW_SIZE * 2):]
        # 持久化到 DB
        try:
            from crud import save_conversation_history
            role = "user" if isinstance(message, HumanMessage) else "assistant"
            save_conversation_history(self._db, self._user_id, role, message.content)
        except Exception as e:
            logger.debug(f"对话持久化失败: {e}")

    def clear(self) -> None:
        self._messages.clear()


def create_memory(user_id: str, db: Session) -> InventoryChatMessageHistory:
    """创建记忆实例"""
    return InventoryChatMessageHistory(user_id, db)
