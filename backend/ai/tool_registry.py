"""
工具注册表：装饰器注册 + 统一分发
"""
import logging
from typing import Callable

logger = logging.getLogger(__name__)

_registry: dict[str, dict] = {}


def register(name: str, description: str, parameters: dict):
    """装饰器：注册一个AI工具"""
    def decorator(func: Callable):
        _registry[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": func
        }
        return func
    return decorator


def get_tool_definitions() -> list:
    """返回 OpenAI 兼容的工具定义列表"""
    tools = []
    for name, info in _registry.items():
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": info["description"],
                "parameters": {
                    "type": "object",
                    "properties": info["parameters"],
                    "required": [k for k, v in info["parameters"].items() if v.get("required", False)]
                }
            }
        })
    return tools


def execute_tool(db, name: str, args: dict) -> dict:
    """执行一个工具调用"""
    info = _registry.get(name)
    if not info:
        return {"success": False, "message": f"未知工具: {name}"}
    try:
        logger.info(f"Execute tool: {name}({args})")
        result = info["handler"](db, **args)
        logger.info(f"Tool result: {name} -> success={result.get('success', 'N/A')}")
        return result
    except Exception as e:
        logger.error(f"Tool error: {name}: {e}")
        return {"success": False, "message": f"执行 {name} 失败: {str(e)}"}
