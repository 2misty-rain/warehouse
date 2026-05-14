"""
LLM Provider: 调用 DashScope API，解析工具调用
"""
import json
import logging
import requests
from ai_settings import ai_settings

logger = logging.getLogger(__name__)
DASHSCOPE_API_KEY = ai_settings.dashscope_api_key


class AgentResponse:
    """Agent 单次 LLM 调用返回"""
    def __init__(self, content: str = "", tool_calls: list = None, done: bool = False):
        self.content = content or ""      # LLM 文本回复
        self.tool_calls = tool_calls or []  # [{name, arguments}]
        self.done = done                   # 是否完成


def chat(messages: list, tools: list) -> AgentResponse:
    """调用 DashScope API，返回 AgentResponse"""
    if not DASHSCOPE_API_KEY:
        return AgentResponse(content="AI 服务未配置 (DASHSCOPE_API_KEY)", done=True)

    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    headers = {"Authorization": f"Bearer {DASHSCOPE_API_KEY}", "Content-Type": "application/json"}

    payload = {
        "model": "qwen-plus",
        "input": {"messages": messages},
        "parameters": {
            "result_format": "message",
            "temperature": 0.5,
            "top_p": 0.8,
            "max_tokens": 2000
        }
    }
    if tools:
        payload["parameters"]["tools"] = tools
        payload["parameters"]["tool_choice"] = "auto"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        if result.get("output") and result["output"].get("choices"):
            message = result["output"]["choices"][0]["message"]
            content = message.get("content") or ""
            raw_tool_calls = message.get("tool_calls") or []

            tool_calls = []
            for tc in raw_tool_calls:
                if tc.get("type") == "function":
                    func_info = tc.get("function", {})
                    try:
                        args = json.loads(func_info.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append({
                        "id": tc.get("id", f"call_{len(tool_calls)}"),
                        "name": func_info.get("name"),
                        "arguments": args
                    })

            logger.info(f"LLM: content_len={len(content)}, tool_calls={[t['name'] for t in tool_calls]}")

            if tool_calls:
                return AgentResponse(content=content, tool_calls=tool_calls, done=False)
            return AgentResponse(content=content, done=True)

        return AgentResponse(content="AI 服务返回异常", done=True)

    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        return AgentResponse(content=f"AI 服务错误: {str(e)}", done=True)
