"""设备库存工具: 查询、创建、更新、回收、删除"""
from functools import partial
from typing import Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from schemas import InventoryCreate, InventoryUpdate
from crud import create_inventory as crud_create, update_inventory as crud_update, delete_inventory as crud_delete
from ai.tools.device_attr import norm_attr


# ---- Pydantic Input Models ----

class QueryInventoryInput(BaseModel):
    device_attribute: Optional[str] = Field(None, description="设备属性筛选: 现有库存/已售出/商机试用/内部试用/产品演示/技术开发测试/特殊占用/异常处理")
    version: Optional[str] = Field(None, description="版本筛选: WiFi/4G")
    type: Optional[str] = Field(None, description="类型筛选: 睡眠/跌倒")
    owner: Optional[str] = Field(None, description="归属人(甲方)")
    borrower: Optional[str] = Field(None, description="领用人")
    iot_card_status: Optional[str] = Field(None, description="物联网卡状态: 开卡/关卡")
    keyword: Optional[str] = Field(None, description="关键词搜索设备号或序号")


class CreateInventoryInput(BaseModel):
    device_id: str = Field(..., min_length=12, max_length=12, description="设备号(必填, 3字母+9数字=12位)")
    serial_number: Optional[str] = Field(None, description="序号")
    version: Optional[str] = Field(None, description="版本: WiFi/4G")
    type: Optional[str] = Field(None, description="类型: 睡眠/跌倒")
    packaging: Optional[str] = Field(None, description="包装: 简约/精品")
    device_attribute: Optional[str] = Field(None, description="设备属性，默认现有库存")
    owner: Optional[str] = Field(None, description="归属人")
    remarks: Optional[str] = Field(None, description="备注")


class UpdateInventoryInput(BaseModel):
    device_id: str = Field(..., description="设备号(必填)")
    device_attribute: Optional[str] = Field(None, description="新设备属性")
    owner: Optional[str] = Field(None, description="新归属人")
    borrower: Optional[str] = Field(None, description="新领用人")
    sales_person: Optional[str] = Field(None, description="销售人员")
    remarks: Optional[str] = Field(None, description="备注")
    version: Optional[str] = Field(None, description="版本")
    type: Optional[str] = Field(None, description="类型")


class ReclaimDeviceInput(BaseModel):
    device_ids: List[str] = Field(..., description="要回收的设备号列表")


class DeleteInventoryInput(BaseModel):
    device_id: str = Field(..., description="设备号(必填)")


# ---- Implementation Functions (db as first arg) ----

def _query_inventory(db, device_attribute=None, version=None, type=None, owner=None,
                     borrower=None, iot_card_status=None, keyword=None):
    from models import Inventory
    query = db.query(Inventory)
    if device_attribute:
        # 反向映射：AI 传入"已售出"时，DB 查询"商机交付"
        attr_filter = "商机交付" if device_attribute == "已售出" else device_attribute
        query = query.filter(Inventory.device_attribute == attr_filter)
    if version: query = query.filter(Inventory.version == version)
    if type: query = query.filter(Inventory.type == type)
    if owner: query = query.filter(Inventory.owner.like(f"%{owner}%"))
    if borrower: query = query.filter(Inventory.borrower.like(f"%{borrower}%"))
    if iot_card_status: query = query.filter(Inventory.iot_card_status == iot_card_status)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            (Inventory.device_id.like(kw)) | (Inventory.serial_number.like(kw)) | (Inventory.owner.like(kw))
        )
    total = query.count()
    items = query.limit(50).all()
    results = [{"device_id": d.device_id, "version": d.version or "-", "type": d.type or "-",
                "packaging": d.packaging or "-", "device_attribute": norm_attr(d.device_attribute),
                "owner": d.owner or "-", "borrower": d.borrower or "-",
                "sales_person": d.sales_person or "-", "iot_card_status": d.iot_card_status or "-",
                "remarks": d.remarks or "", "delivery_date": str(d.delivery_date) if d.delivery_date else "-"}
               for d in items]
    return {"total": total, "items": results, "success": True}


def _create_inventory(db, device_id: str, serial_number=None, version=None, type=None,
                      packaging=None, device_attribute="现有库存", owner=None, remarks=None):
    from models import Inventory
    existing = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if existing:
        return {"success": False, "message": f"设备号 {device_id} 已存在"}
    sn = serial_number or device_id
    existing_serial = db.query(Inventory).filter(Inventory.serial_number == sn).first()
    if existing_serial:
        return {"success": False, "message": f"序号 {sn} 已存在"}

    data = {"device_id": device_id, "serial_number": sn,
            "version": version or "", "type": type or "", "packaging": packaging or "",
            "device_attribute": "商机交付" if (device_attribute or "现有库存") == "已售出" else (device_attribute or "现有库存"),
            "owner": owner or "", "remarks": remarks or ""}
    inv = InventoryCreate(**data)
    result = crud_create(db, inv)
    db.commit()
    return {"success": True, "message": f"已添加设备 {device_id}", "device_id": device_id}


def _update_inventory(db, device_id: str, **kwargs):
    from models import Inventory
    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not device:
        return {"success": False, "message": f"设备 {device_id} 不存在"}
    clean = {k: v for k, v in kwargs.items() if v is not None and k != 'device_id'}
    if not clean:
        return {"success": False, "message": "没有要更新的字段"}
    # 反向映射：AI 传入"已售出"时，DB 存储"商机交付"
    if clean.get("device_attribute") == "已售出":
        clean["device_attribute"] = "商机交付"
    update_data = InventoryUpdate(**clean)
    crud_update(db, device_id=device_id, inventory_update=update_data)
    db.commit()
    return {"success": True, "message": f"已更新设备 {device_id}"}


def _reclaim_device(db, device_ids: list):
    from models import Inventory, BorrowRecord
    from datetime import date
    results = []
    for device_id in device_ids:
        device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
        if not device:
            results.append({"device_id": device_id, "status": "失败", "reason": "设备不存在"})
            continue
        # 终止活跃借用记录
        active = db.query(BorrowRecord).filter(
            BorrowRecord.device_id == device_id,
            BorrowRecord.status.in_(['borrowed', 'overdue'])
        ).all()
        for b in active:
            b.status = 'terminated'
            b.actual_return_date = date.today()
            b.remarks = f"{b.remarks or ''}\n(因回收终止)"
        device.device_attribute = "现有库存"
        device.owner = None
        device.borrower = None
        device.sales_person = None
        device.remarks = ""
        device.supplementary_info = None
        device.delivery_date = None
        results.append({"device_id": device_id, "status": "成功"})
    db.commit()
    ok = [r for r in results if r["status"] == "成功"]
    fail = [r for r in results if r["status"] != "成功"]
    return {"success": True, "message": f"已回收 {len(ok)} 台设备为库存" + (f"，失败 {len(fail)} 台" if fail else ""), "details": results}


def _delete_inventory(db, device_id: str):
    from models import BorrowRecord
    active = db.query(BorrowRecord).filter(
        BorrowRecord.device_id == device_id,
        BorrowRecord.status.in_(['borrowed', 'overdue'])
    ).first()
    if active:
        return {"success": False, "message": f"设备 {device_id} 正在被 {active.borrower} 借用中，请先归还"}
    ok = crud_delete(db, device_id=device_id)
    if not ok:
        return {"success": False, "message": f"设备 {device_id} 不存在"}
    db.commit()
    return {"success": True, "message": f"已永久删除设备 {device_id}"}


# ---- Factory: 创建 db 绑定的 LangChain Tools ----

def make_inventory_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_query_inventory, db),
            name="query_inventory",
            description="查询库存设备列表。按条件筛选(设备属性/版本/类型/归属人/领用人/IoT卡状态/关键词)。返回匹配的设备列表(最多50条)及总数。要看全部设备请用 get_inventory_overview。",
            args_schema=QueryInventoryInput,
        ),
        StructuredTool.from_function(
            func=partial(_create_inventory, db),
            name="create_inventory",
            description="添加新设备到库存。录入/入库新设备时使用。",
            args_schema=CreateInventoryInput,
        ),
        StructuredTool.from_function(
            func=partial(_update_inventory, db),
            name="update_inventory",
            description="更新设备信息。修改设备属性、归属人、备注等字段。只传需要修改的字段。",
            args_schema=UpdateInventoryInput,
        ),
        StructuredTool.from_function(
            func=partial(_reclaim_device, db),
            name="reclaim_device",
            description="设备回收/退库。将设备回收为现有库存状态，清除所有分配信息。当用户说'回收/退库/回收为库存/清除信息回库'时使用。支持多台设备同时回收。",
            args_schema=ReclaimDeviceInput,
        ),
        StructuredTool.from_function(
            func=partial(_delete_inventory, db),
            name="delete_inventory",
            description="永久删除设备记录(从数据库移除)。注意: 这不是回收/退库操作。回收设备到库存请用 reclaim_device。不可恢复。",
            args_schema=DeleteInventoryInput,
        ),
    ]
