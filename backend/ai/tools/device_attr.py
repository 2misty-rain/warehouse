"""设备属性输出映射：将数据库原始值转换为 AI 友好名称"""
from typing import Optional


def norm_attr(db_value: Optional[str]) -> str:
    """将数据库 device_attribute 值映射为对 AI 友好的名称"""
    if not db_value:
        return "未分类"
    if db_value == "商机交付":
        return "已售出"
    return db_value
