"""
LangChain 回调：日志记录 + 操作审计
"""
import logging
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


class LoggingCallbackHandler(BaseCallbackHandler):
    """记录 LLM 调用和工具执行"""

    def on_llm_start(self, serialized, prompts, **kwargs):
        logger.info(f"LLM 调用开始 (prompts: {sum(len(p) for p in prompts)} chars)")

    def on_llm_end(self, response, **kwargs):
        logger.info(f"LLM 调用完成")

    def on_llm_error(self, error, **kwargs):
        logger.error(f"LLM 调用失败: {error}")

    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized.get("name", "unknown")
        logger.info(f"Tool 开始: {name}")

    def on_tool_end(self, output, **kwargs):
        logger.info(f"Tool 完成: {output.get('success', 'N/A') if isinstance(output, dict) else 'ok'}")

    def on_tool_error(self, error, **kwargs):
        logger.error(f"Tool 失败: {error}")

    def on_agent_action(self, action, **kwargs):
        logger.info(f"Agent 动作: {action.tool}({action.tool_input})")

    def on_agent_finish(self, finish, **kwargs):
        logger.info(f"Agent 完成: {len(finish.return_values.get('output', ''))} chars")
