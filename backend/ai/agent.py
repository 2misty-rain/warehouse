"""
LangGraph Agent - ReAct 模式
每请求创建新的 Agent（因为 db session 唯一）
"""
import logging
from functools import partial
from sqlalchemy.orm import Session
from langchain_community.chat_models.tongyi import ChatTongyi
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage

from ai_settings import ai_settings
from .prompts import build_system_prompt, build_system_context
from .tools import get_all_tools
from .memory import create_memory
from .callbacks import LoggingCallbackHandler

logger = logging.getLogger(__name__)
MAX_ITERATIONS = 8


def _patch_tool_func(tool):
    """langgraph 不认 functools.partial，包一层正常函数让 inspect 能工作"""
    if not isinstance(tool.func, partial):
        return
    pf = tool.func
    def wrapper(*args, **kwargs):
        return pf(*args, **kwargs)
    wrapper.__name__ = pf.func.__name__
    tool.func = wrapper


def run(user_input: str, db: Session, user_id: str = "default") -> dict:
    """执行一次 AI 对话，返回 {"success": bool, "reply": str}"""

    try:
        # 1. 创建 LLM（低温度，库存场景需要确定性）
        llm = ChatTongyi(
            model="qwen-plus",
            dashscope_api_key=ai_settings.dashscope_api_key,
            temperature=0.2,
            top_p=0.8,
            streaming=False,
        )

        # 2. 获取 db 绑定的工具（修复 partial 避免 langgraph inspect 报错）
        tools = get_all_tools(db)
        for t in tools:
            _patch_tool_func(t)

        # 3. 构建系统 Prompt
        prompt_text = build_system_prompt(db)
        system_ctx = build_system_context(db)
        system_prompt = (
            f"{prompt_text}\n\n"
            f"【待处理事项: {system_ctx}】\n\n"
            "⚠️ 上述仅是待处理告警，不是库存全貌。你必须调用 get_inventory_overview "
            "或 query_inventory 工具查询实时数据库后才能回答。禁止凭任何上下文中的数字回答。"
        )

        # 4. 加载对话历史
        chat_history = create_memory(user_id, db)
        history_messages = list(chat_history.messages)

        # 5. 创建 ReAct Agent
        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=system_prompt,
        )

        # 6. 执行（历史消息 + 当前用户输入）
        input_messages = history_messages + [HumanMessage(content=user_input)]
        result = agent.invoke(
            {"messages": input_messages},
            config={
                "recursion_limit": MAX_ITERATIONS * 2 + 1,
                "callbacks": [LoggingCallbackHandler()],
            },
        )

        # 7. 提取最终输出
        messages = result.get("messages", [])
        output = ""
        if messages:
            last_msg = messages[-1]
            output = last_msg.content if hasattr(last_msg, 'content') else ""

        # 8. 持久化本轮对话
        chat_history.add_message(HumanMessage(content=user_input))
        if output:
            chat_history.add_message(AIMessage(content=output))

        # 日志记录工具调用情况
        tool_messages = [m for m in messages if hasattr(m, 'tool_calls') and m.tool_calls]
        tool_call_count = sum(len(getattr(m, 'tool_calls', [])) for m in tool_messages)
        logger.info(f"Agent 完成: {len(output)} chars, {tool_call_count} tool calls")

        if not output:
            return {"success": False, "reply": "AI 未生成有效回复，请重试。"}
        return {"success": True, "reply": output}

    except Exception as e:
        logger.error(f"Agent 错误: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return {"success": False, "reply": "AI 服务暂时不可用，请稍后重试。"}
