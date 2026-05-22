"""设备生命周期工具"""
from functools import partial
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool


class DeviceLifecycleInput(BaseModel):
    device_id: str = Field(..., description="设备号")


def _get_device_lifecycle(db, device_id: str):
    from crud import get_device_timeline
    return get_device_timeline(db, device_id)


def make_lifecycle_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_get_device_lifecycle, db),
            name="get_device_lifecycle",
            description="查询设备完整生命周期：入库、出库、借用、归还等历史记录。",
            args_schema=DeviceLifecycleInput,
        ),
    ]
