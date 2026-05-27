"""日期解析工具"""
import re
from datetime import date, timedelta
from functools import partial
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

TODAY_WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class ResolveDateInput(BaseModel):
    expression: str = Field(..., description="日期表达式，如: 下周五、3天后、本月15号、5月6日、明天 etcs")


def _resolve_date(db, expression: str):
    """自然语言日期 → YYYY-MM-DD（每次调用动态计算 today）"""
    result = _parse(expression, today=date.today())
    if result.get("date"):
        return {"success": True, "date": result["date"], "display": result["display"]}
    return {"success": False, "date": None, "message": f"无法解析日期: {expression}"}


def _parse(expression: str, today: date = None) -> dict:
    if today is None:
        today = date.today()
    t = expression.strip()

    simple = {"今天": 0, "明天": 1, "后天": 2, "昨天": -1, "前天": -2}
    if t in simple:
        d = today + timedelta(days=simple[t])
        return {"date": d.strftime("%Y-%m-%d"), "display": t}

    m = re.match(r'(\d+)\s*天后', t)
    if m: d = today + timedelta(days=int(m.group(1))); return {"date": d.strftime("%Y-%m-%d"), "display": t}
    m = re.match(r'(\d+)\s*天前', t)
    if m: d = today - timedelta(days=int(m.group(1))); return {"date": d.strftime("%Y-%m-%d"), "display": t}

    m = re.match(r'下(?:个)?(周.)', t)
    if m:
        target = m.group(1)
        for i, name in enumerate(TODAY_WEEKDAY_NAMES):
            if name == target:
                days_ahead = i - today.weekday()
                if days_ahead <= 0: days_ahead += 7
                d = today + timedelta(days=days_ahead)
                return {"date": d.strftime("%Y-%m-%d"), "display": t}
        return {"date": None}

    m = re.match(r'(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]', t)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = today.year
        if month < today.month or (month == today.month and day < today.day):
            year += 1
        try:
            d = date(year, month, day)
            return {"date": d.strftime("%Y-%m-%d"), "display": t}
        except ValueError:
            return {"date": None}

    m = re.match(r'本月\s*(\d{1,2})\s*[号日]', t)
    if m:
        day = int(m.group(1))
        try:
            d = date(today.year, today.month, day)
            return {"date": d.strftime("%Y-%m-%d"), "display": t}
        except ValueError:
            return {"date": None}

    return {"date": None}


def make_date_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_resolve_date, db),
            name="resolve_date",
            description="将自然语言日期表达式解析为 YYYY-MM-DD 格式。支持：下周五、3天后、本月15号、5月6日、明天 etcs。",
            args_schema=ResolveDateInput,
        ),
    ]
