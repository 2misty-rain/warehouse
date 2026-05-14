"""设备库存工具: 查询、创建、更新、删除"""
from ..tool_registry import register
from schemas import InventoryCreate, InventoryUpdate
from crud import create_inventory as crud_create, update_inventory as crud_update, delete_inventory as crud_delete


@register(
    name="query_inventory",
    description="查询库存设备列表。按条件筛选：device_attribute(设备属性)、version(版本WiFi/4G)、type(类型睡眠/跌倒)、owner(归属人)、borrower(领用人)、iot_card_status(开卡/关卡)、keyword(关键词搜索设备号)。",
    parameters={
        "device_attribute": {"type": "string", "description": "设备属性筛选", "required": False},
        "version": {"type": "string", "description": "版本 WiFi/4G", "required": False},
        "type": {"type": "string", "description": "类型 睡眠/跌倒", "required": False},
        "owner": {"type": "string", "description": "归属人", "required": False},
        "borrower": {"type": "string", "description": "领用人", "required": False},
        "iot_card_status": {"type": "string", "description": "物联网卡状态 开卡/关卡", "required": False},
        "keyword": {"type": "string", "description": "关键词搜索设备号", "required": False}
    }
)
def query_inventory(db, device_attribute=None, version=None, type=None, owner=None,
                    borrower=None, iot_card_status=None, keyword=None):
    from models import Inventory
    query = db.query(Inventory)
    if device_attribute: query = query.filter(Inventory.device_attribute == device_attribute)
    if version: query = query.filter(Inventory.version == version)
    if type: query = query.filter(Inventory.type == type)
    if owner: query = query.filter(Inventory.owner.like(f"%{owner}%"))
    if borrower: query = query.filter(Inventory.borrower.like(f"%{borrower}%"))
    if iot_card_status: query = query.filter(Inventory.iot_card_status == iot_card_status)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter((Inventory.device_id.like(kw)) | (Inventory.serial_number.like(kw)))

    items = query.limit(50).all()
    total = query.count()
    results = [{
        "device_id": d.device_id, "version": d.version or "-", "type": d.type or "-",
        "device_attribute": d.device_attribute or "未分类", "owner": d.owner or "-",
        "borrower": d.borrower or "-", "iot_card_status": d.iot_card_status or "-"
    } for d in items]

    return {"total": total, "items": results, "success": True}


@register(
    name="create_inventory",
    description="添加新设备到库存。录入/入库新设备时使用。",
    parameters={
        "device_id": {"type": "string", "description": "设备号", "required": True},
        "serial_number": {"type": "string", "description": "序号", "required": False},
        "version": {"type": "string", "description": "版本 WiFi/4G", "required": False},
        "type": {"type": "string", "description": "类型 睡眠/跌倒", "required": False},
        "packaging": {"type": "string", "description": "包装", "required": False},
        "device_attribute": {"type": "string", "description": "设备属性", "required": False},
        "owner": {"type": "string", "description": "归属人", "required": False},
        "remarks": {"type": "string", "description": "备注", "required": False}
    }
)
def create_inventory(db, device_id, serial_number=None, version=None, type=None,
                     packaging=None, device_attribute="现有库存", owner=None, remarks=None):
    data = {"device_id": device_id, "serial_number": serial_number or device_id,
            "version": version or "", "type": type or "", "packaging": packaging or "",
            "device_attribute": device_attribute or "现有库存", "owner": owner or "", "remarks": remarks or ""}
    inv = InventoryCreate(**data)
    result = crud_create(db, inv)
    db.commit()
    return {"success": True, "message": f"已添加设备 {device_id}", "device_id": device_id}


@register(
    name="update_inventory",
    description="更新设备信息。修改设备属性、归属人、备注等。",
    parameters={
        "device_id": {"type": "string", "description": "设备号", "required": True},
        "device_attribute": {"type": "string", "description": "新设备属性", "required": False},
        "owner": {"type": "string", "description": "新归属人", "required": False},
        "borrower": {"type": "string", "description": "新领用人", "required": False},
        "sales_person": {"type": "string", "description": "销售人员", "required": False},
        "remarks": {"type": "string", "description": "备注", "required": False},
        "version": {"type": "string", "description": "版本", "required": False},
        "type": {"type": "string", "description": "类型", "required": False}
    }
)
def update_inventory(db, device_id, **kwargs):
    from models import Inventory
    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not device:
        return {"success": False, "message": f"设备 {device_id} 不存在"}

    clean = {k: v for k, v in kwargs.items() if v is not None and k != 'device_id'}
    if not clean:
        return {"success": False, "message": "没有要更新的字段"}

    update_data = InventoryUpdate(**clean)
    crud_update(db, device_id=device_id, inventory_update=update_data)
    db.commit()
    return {"success": True, "message": f"已更新设备 {device_id}"}


@register(
    name="delete_inventory",
    description="删除设备。不可恢复，谨慎使用。",
    parameters={
        "device_id": {"type": "string", "description": "设备号", "required": True}
    }
)
def delete_inventory(db, device_id):
    from models import Inventory, BorrowRecord
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
    return {"success": True, "message": f"已删除设备 {device_id}"}
