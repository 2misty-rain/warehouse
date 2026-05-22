"""
LangChain Agent 工厂
每请求创建新的 Agent（因为 db session 唯一）
"""
import logging
from sqlalchemy.orm import Session
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from ai_settings import ai_settings
from .prompts import build_system_prompt, build_system_context
from .tools import get_all_tools
from .memory import create_memory
from .callbacks import LoggingCallbackHandler

logger = logging.getLogger(__name__)
MAX_ITERATIONS = 8


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

        # 2. 获取 db 绑定的工具
        tools = get_all_tools(db)

        # 3. 构建 Prompt
        prompt_text = build_system_prompt(db)  # 动态生成日期
        system_ctx = build_system_context(db)  # 仅告警，不含库存数字
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_text),
            ("system", f"【待处理事项: {system_ctx}】"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("system", "⚠️ 上述仅是待处理告警，不是库存全貌。你必须调用 get_inventory_overview 或 query_inventory 工具查询实时数据库后才能回答。禁止凭任何上下文中的数字回答。"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 4. 创建 Agent
        agent = create_tool_calling_agent(llm, tools, prompt)

        # 5. 创建 Executor + Memory + Callbacks
        chat_history = create_memory(user_id, db)  # BaseChatMessageHistory
        memory = ConversationBufferWindowMemory(
            chat_memory=chat_history,
            k=6,
            return_messages=True,
            memory_key="chat_history",
        )
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            max_iterations=MAX_ITERATIONS,
            verbose=True,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            callbacks=[LoggingCallbackHandler()],
        )

        # 6. 执行
        result = executor.invoke({"input": user_input})
        output = result.get("output", "")

        # 日志记录工具调用情况
        steps = result.get("intermediate_steps", [])
        tool_calls_made = [s[0].tool for s in steps if hasattr(s[0], 'tool')]
        logger.info(f"Agent 完成: {len(output)} chars, {len(tool_calls_made)} tool calls: {tool_calls_made}")

        if not output:
            return {"success": False, "reply": "AI 未生成有效回复，请重试。"}
        return {"success": True, "reply": output}

    except Exception as e:
        logger.error(f"Agent 错误: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return {"success": False, "reply": f"AI 服务异常: {str(e)}"}
