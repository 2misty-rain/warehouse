"""IoT卡管理工具"""
from functools import partial
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool


class UpdateIoTCardInput(BaseModel):
    device_id: str = Field(..., description="设备号")
    iot_card_status: str = Field(..., description="开卡 或 关卡")


def _update_iot_card(db, device_id: str, iot_card_status: str):
    if iot_card_status not in ('开卡', '关卡'):
        return {"success": False, "message": "iot_card_status 必须是'开卡'或'关卡'"}
    from crud import update_iot_card_status
    ok = update_iot_card_status(db, device_id, iot_card_status)
    if not ok:
        return {"success": False, "message": f"设备 {device_id} 不存在"}
    return {"success": True, "message": f"设备 {device_id} IoT卡已{iot_card_status}"}


def make_iot_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_update_iot_card, db),
            name="update_iot_card",
            description="更新4G设备的物联网卡状态(开卡/关卡)。",
            args_schema=UpdateIoTCardInput,
        ),
    ]
