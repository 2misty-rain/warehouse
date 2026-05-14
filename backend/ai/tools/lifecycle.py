"""设备生命周期工具"""
from ..tool_registry import register


@register(
    name="get_device_lifecycle",
    description="查询设备完整生命周期：入库、出库、借用、归还等历史记录。",
    parameters={
        "device_id": {"type": "string", "description": "设备号", "required": True}
    }
)
def get_device_lifecycle(db, device_id):
    from crud import get_device_timeline
    return get_device_timeline(db, device_id)
