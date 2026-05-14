"""IoT卡管理工具"""
from ..tool_registry import register


@register(
    name="update_iot_card",
    description="更新4G设备的物联网卡状态（开卡/关卡）。",
    parameters={
        "device_id": {"type": "string", "description": "设备号", "required": True},
        "iot_card_status": {"type": "string", "description": "开卡 或 关卡", "required": True}
    }
)
def update_iot_card(db, device_id, iot_card_status):
    from crud import update_iot_card_status
    if iot_card_status not in ('开卡', '关卡'):
        return {"success": False, "message": "状态只能是'开卡'或'关卡'"}
    ok = update_iot_card_status(db, device_id, iot_card_status)
    if not ok:
        return {"success": False, "message": f"设备 {device_id} 不存在"}
    return {"success": True, "message": f"设备 {device_id} IoT卡已{iot_card_status}"}
