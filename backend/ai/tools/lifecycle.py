"""设备生命周期工具"""
from functools import partial
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from ai.tools.device_attr import norm_attr


class DeviceLifecycleInput(BaseModel):
    device_id: str = Field(..., description="设备号")


def _get_device_lifecycle(db, device_id: str):
    from crud import get_device_timeline
    result = get_device_timeline(db, device_id)
    # 映射事件描述中的"商机交付"→"已售出"
    for event in result.get("events", []):
        if "商机交付" in event.get("description", ""):
            event["description"] = event["description"].replace("商机交付", "已售出")
    return result


def make_lifecycle_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_get_device_lifecycle, db),
            name="get_device_lifecycle",
            description="查询设备完整生命周期：入库、出库、借用、归还等历史记录。",
            args_schema=DeviceLifecycleInput,
        ),
    ]
