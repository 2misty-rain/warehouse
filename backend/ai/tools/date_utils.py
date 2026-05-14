"""日期解析工具"""
import re
from datetime import date, timedelta
from ..tool_registry import register


@register(
    name="resolve_date",
    description="将自然语言日期表达式解析为 YYYY-MM-DD 格式。支持：下周五、3天后、本月15号、5月6日、明天等。",
    parameters={
        "expression": {"type": "string", "description": "日期表达式", "required": True}
    }
)
def resolve_date(db, expression):
    result = _parse(expression)
    return {"success": True, "date": result.get("date"), "display": result.get("display")}


def _parse(expression: str) -> dict:
    today = date.today()
    expr = expression.strip()

    weekday_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6,
                   "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3, "星期五": 4, "星期六": 5, "星期日": 6}

    # 下周X
    for name, wd in weekday_map.items():
        if f"下周{name}" in expr or f"下个{name}" in expr:
            days_ahead = (wd - today.weekday()) % 7
            if days_ahead <= 0: days_ahead += 7
            t = today + timedelta(days=days_ahead)
            return {"date": t.strftime("%Y-%m-%d"), "display": f"下周{name}({t.strftime('%Y-%m-%d')})"}

    # X月X日
    m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]', expr)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        try:
            t = today.replace(month=month, day=day)
            return {"date": t.strftime("%Y-%m-%d"), "display": f"{month}月{day}日({t.strftime('%Y-%m-%d')})"}
        except ValueError:
            return {"date": None, "display": f"无效日期: {month}月{day}日"}

    # X天后
    m = re.search(r'(\d+)\s*天[后之]', expr)
    if m:
        t = today + timedelta(days=int(m.group(1)))
        return {"date": t.strftime("%Y-%m-%d"), "display": f"{m.group(1)}天后({t.strftime('%Y-%m-%d')})"}

    # 本月N号
    m = re.search(r'本月(\d+)[号日]', expr)
    if m:
        try:
            t = today.replace(day=int(m.group(1)))
            return {"date": t.strftime("%Y-%m-%d"), "display": f"本月{m.group(1)}号"}
        except ValueError:
            return {"date": None, "display": "日期无效"}

    # 简单词
    simple = {"今天": 0, "明天": 1, "后天": 2, "昨天": -1, "前天": -2}
    for name, offset in simple.items():
        if name in expr:
            t = today + timedelta(days=offset)
            return {"date": t.strftime("%Y-%m-%d"), "display": f"{name}({t.strftime('%Y-%m-%d')})"}

    return {"date": None, "display": f"无法解析: {expression}"}
