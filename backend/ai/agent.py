"""
InventoryAgent: ReAct 循环编排器
用户输入 → LLM推理 → 调工具 → 观察结果 → 再推理 → 最终回复
"""
import json
import logging
from .provider import chat as llm_chat
from .tool_registry import get_tool_definitions, execute_tool
from .prompts import build_system_prompt, build_system_context
from .history import get_history, add_to_history

logger = logging.getLogger(__name__)
MAX_ITERATIONS = 8

# 确认类话语检测模式 — 防止 LLM 向用户请求确认
_CONFIRM_PATTERNS = [
    "请确认", "我将执行", "是否继续", "确认吗", "是否执行",
    "要我执行", "为您执行", "帮你执行", "需要确认", "您确认",
    "确认一下", "确认后", "确认执行", "确认操作",
]


def _is_confirmation_text(text: str) -> bool:
    """检测 LLM 回复是否在向用户请求确认（而非直接执行或返回结果）"""
    if not text:
        return False
    t = text.strip()
    for p in _CONFIRM_PATTERNS:
        if p in t:
            return True
    # 短文本以问号结尾且不含数据，大概率是确认请求
    if len(t) < 40 and t.endswith("？") and "设备" not in t:
        return True
    return False


def run(db, user_input: str, user_id: str = "default") -> dict:
    """执行一次AI对话，支持多轮工具调用"""

    system_prompt = build_system_prompt(db)
    system_ctx = build_system_context(db)
    history = get_history(db, user_id, limit=6)
    tools = get_tool_definitions()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"【实时数据】{system_ctx}"},
    ]
    for msg in history:
        messages.append(msg)
    messages.append({"role": "user", "content": user_input})

    try:
        for iteration in range(MAX_ITERATIONS):
            response = llm_chat(messages, tools)

            if response.tool_calls:
                logger.info(f"Iteration {iteration + 1}: {len(response.tool_calls)} tool calls: {[t['name'] for t in response.tool_calls]}")
                assistant_msg = {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)}
                        }
                        for tc in response.tool_calls
                    ]
                }
                messages.append(assistant_msg)
                for tc in response.tool_calls:
                    result = execute_tool(db, tc["name"], tc["arguments"])
                    result_text = json.dumps(result, ensure_ascii=False, default=str)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result_text
                    })
                continue

            # 没有工具调用，LLM 给出最终回复
            if response.done:
                reply = response.content

                # 兜底检测：如果 LLM 输出了确认类话语，自动重试
                if _is_confirmation_text(reply):
                    logger.info(f"Iteration {iteration + 1}: 检测到确认文本，自动重试")
                    messages.append({
                        "role": "user",
                        "content": "不要确认，直接执行。请立即调用工具完成操作，返回结果。"
                    })
                    continue

                if not reply:
                    reply = "操作已完成。"
                add_to_history(db, user_id, "user", user_input)
                add_to_history(db, user_id, "assistant", reply)
                return {"success": True, "reply": reply, "data": {"iterations": iteration + 1}}

        logger.warning(f"Agent exceeded {MAX_ITERATIONS} iterations")
        return {"success": False, "reply": "处理步骤过多，请简化您的问题再试。"}

    except Exception as e:
        logger.error(f"Agent error: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return {"success": False, "reply": f"处理出错: {str(e)}"}
