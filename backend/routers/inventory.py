from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import io, csv, logging, re, traceback

from database import get_db
from models import Inventory, BorrowRecord
from schemas import (
    InventoryCreate, InventoryUpdate, InventoryResponse,
    IoTCardUpdate, BatchIoTCardUpdate, BatchInventoryUpdate,
)
from crud import (
    get_inventory, get_inventory_by_device_id, create_inventory,
    update_inventory, delete_inventory, update_iot_card_status,
    batch_update_iot_card_status, batch_update_inventory_fields,
    get_device_timeline
)
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inventory", tags=["Inventory"])


def _get_username(request: Request) -> str:
    return getattr(request.state, 'username', 'system')


@router.get("")
def read_inventory(
    request: Request,
    skip: int = 0, limit: int = 100,
    search: str = "",
    device_attribute: str = "", version: str = "",
    type: str = "", packaging: str = "", owner: str = "",
    iot_card_status: str = "",
    delivery_date_start: Optional[str] = None,
    delivery_date_end: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    query = db.query(Inventory)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (Inventory.device_id.like(pattern)) |
            (Inventory.serial_number.like(pattern)) |
            (Inventory.owner.like(pattern))
        )

    if device_attribute:
        query = query.filter(Inventory.device_attribute == device_attribute)
    if version:
        query = query.filter(Inventory.version == version)
    if type:
        query = query.filter(Inventory.type == type)
    if packaging:
        query = query.filter(Inventory.packaging == packaging)
    if owner:
        query = query.filter(Inventory.owner == owner)
    if iot_card_status:
        if iot_card_status == '未设置':
            query = query.filter(
                (Inventory.iot_card_status == None) | (Inventory.iot_card_status == '')
            )
        else:
            query = query.filter(Inventory.iot_card_status == iot_card_status)

    if delivery_date_start:
        try:
            query = query.filter(Inventory.delivery_date >= datetime.strptime(delivery_date_start, "%Y-%m-%d").date())
        except ValueError:
            pass
    if delivery_date_end:
        try:
            query = query.filter(Inventory.delivery_date <= datetime.strptime(delivery_date_end, "%Y-%m-%d").date())
        except ValueError:
            pass

    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"total": total, "items": items}


# ---- 静态路由必须在 /{device_id} 之前定义 ----

@router.get("/export/stream")
def export_inventory(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    search: str = "",
    device_attribute: str = "", version: str = "",
    type: str = "", packaging: str = "", owner: str = "",
    iot_card_status: str = "",
    delivery_date_start: Optional[str] = None,
    delivery_date_end: Optional[str] = None,
):
    try:
        query = db.query(Inventory)

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                (Inventory.device_id.like(pattern)) |
                (Inventory.serial_number.like(pattern)) |
                (Inventory.owner.like(pattern))
            )
        if device_attribute:
            query = query.filter(Inventory.device_attribute == device_attribute)
        if version:
            query = query.filter(Inventory.version == version)
        if type:
            query = query.filter(Inventory.type == type)
        if packaging:
            query = query.filter(Inventory.packaging == packaging)
        if owner:
            query = query.filter(Inventory.owner == owner)
        if iot_card_status:
            query = query.filter(Inventory.iot_card_status == iot_card_status)
        if delivery_date_start:
            try:
                query = query.filter(Inventory.delivery_date >= datetime.strptime(delivery_date_start, "%Y-%m-%d").date())
            except ValueError:
                pass
        if delivery_date_end:
            try:
                query = query.filter(Inventory.delivery_date <= datetime.strptime(delivery_date_end, "%Y-%m-%d").date())
            except ValueError:
                pass

        devices = query.all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            '版本', '设备号', '类型', '包装', '设备属性', '归属人', '领用人', '销售',
            '物联网卡状态', '备注', '补充信息', '交付时间'
        ])
        for device in devices:
            writer.writerow([
                device.version or '', device.device_id, device.type or '',
                device.packaging or '', device.device_attribute or '',
                device.owner or '', device.borrower or '', device.sales_person or '',
                device.iot_card_status or '',
                device.remarks or '', device.supplementary_info or '',
                device.delivery_date.strftime('%Y-%m-%d') if device.delivery_date else ''
            ])
        csv_content = output.getvalue()
        output.close()
        return StreamingResponse(
            iter([csv_content.encode('utf-8-sig')]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    except Exception as e:
        logger.error(f"导出失败: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.get("/import/template")
def download_import_template(user=Depends(get_current_user)):
    template = """版本,设备号,类型,包装,设备属性,归属人,领用人,销售,物联网卡状态,备注,补充信息,交付时间
WiFi,DEV001,睡眠,简约,现有库存,张三,,,,,,2024-01-01
4G,DEV002,跌倒,精品,商机交付,李四,王五,赵六,,客户试用,,2024-01-15"""
    return StreamingResponse(
        iter([template.encode('utf-8-sig')]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_import_template.csv"}
    )


@router.get("/owners")
def get_owners(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """获取所有不重复的归属人列表（动态，用于筛选下拉）"""
    results = db.query(Inventory.owner).filter(
        Inventory.owner.isnot(None),
        Inventory.owner != ''
    ).distinct().order_by(Inventory.owner).all()
    return [r[0] for r in results]


@router.get("/{device_id}", response_model=InventoryResponse)
def read_inventory_item(device_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = get_inventory_by_device_id(db, device_id=device_id)
    if not item:
        raise HTTPException(status_code=404, detail="设备不存在")
    return item


@router.get("/{device_id}/detail")
def read_inventory_detail(device_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    device = get_inventory_by_device_id(db, device_id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    borrow_history = db.query(BorrowRecord).filter(
        BorrowRecord.device_id == device_id
    ).order_by(BorrowRecord.borrow_date.desc()).limit(20).all()

    borrows = []
    for record in borrow_history:
        borrows.append({
            "id": record.id,
            "borrower": record.borrower,
            "borrow_date": record.borrow_date.strftime("%Y-%m-%d %H:%M") if record.borrow_date else None,
            "expected_return_date": record.expected_return_date.strftime("%Y-%m-%d") if record.expected_return_date else None,
            "actual_return_date": record.actual_return_date.strftime("%Y-%m-%d") if record.actual_return_date else None,
            "status": record.status,
            "purpose": record.purpose
        })

    return {"device": device, "borrow_history": borrows}


@router.get("/{device_id}/timeline")
def read_device_timeline(device_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    device = get_inventory_by_device_id(db, device_id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    return get_device_timeline(db, device_id)


@router.post("", response_model=InventoryResponse)
def create_inventory_item(
    request: Request,
    inventory: InventoryCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    existing_device = get_inventory_by_device_id(db, device_id=inventory.device_id)
    if existing_device:
        raise HTTPException(status_code=400, detail="设备ID已存在")

    existing_serial = db.query(Inventory).filter(Inventory.serial_number == inventory.serial_number).first()
    if existing_serial:
        raise HTTPException(status_code=400, detail="序号已存在")

    return create_inventory(db=db, inventory=inventory, username=_get_username(request))


@router.put("/{device_id}", response_model=InventoryResponse)
def update_inventory_item(
    request: Request,
    device_id: str,
    inventory_update: InventoryUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    item = update_inventory(db, device_id=device_id, inventory_update=inventory_update,
                            username=_get_username(request))
    if not item:
        raise HTTPException(status_code=404, detail="设备不存在")
    return item


@router.delete("/{device_id}")
def delete_inventory_item(
    request: Request,
    device_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    success = delete_inventory(db, device_id=device_id, username=_get_username(request))
    if not success:
        raise HTTPException(status_code=404, detail="设备不存在")
    return {"message": "设备删除成功"}


@router.put("/{device_id}/iot-card")
def update_device_iot_card(
    device_id: str, data: IoTCardUpdate,
    db: Session = Depends(get_db), user=Depends(get_current_user)
):
    success = update_iot_card_status(db, device_id, data.iot_card_status)
    if not success:
        # 可能是设备不存在，也可能是 WiFi 设备
        device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="设备不存在")
        raise HTTPException(status_code=400, detail="仅4G设备支持IoT卡管理")
    return {"message": f"IoT卡状态已更新为: {data.iot_card_status}"}


@router.post("/batch/delete")
def batch_delete_inventory(data: dict, db: Session = Depends(get_db),
                           user=Depends(get_current_user)):
    device_ids = data.get('device_ids', [])
    if not device_ids:
        raise HTTPException(status_code=400, detail="请选择要删除的设备")
    deleted = 0
    failed = []
    for did in device_ids:
        device = db.query(Inventory).filter(Inventory.device_id == did).first()
        if not device:
            failed.append(did)
            continue
        active = db.query(BorrowRecord).filter(
            BorrowRecord.device_id == did, BorrowRecord.status.in_(['borrowed', 'overdue'])
        ).first()
        if active:
            failed.append(f"{did}(借用中)")
            continue
        db.delete(device)
        from crud import _log_operation
        _log_operation(db, _get_username(request), "batch_delete", did, {"batch_size": len(device_ids)})
        deleted += 1
    db.commit()
    return {"message": f"成功删除 {deleted} 台设备", "deleted": deleted, "failed": failed}


@router.post("/batch/iot-card")
def batch_update_iot_card(data: BatchIoTCardUpdate, db: Session = Depends(get_db),
                          user=Depends(get_current_user)):
    result = batch_update_iot_card_status(db, data.device_ids, data.iot_card_status)
    return {"message": f"批量更新完成", **result}


@router.post("/batch/update")
def batch_update_inventory(
    request: Request,
    data: BatchInventoryUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """批量编辑设备：只更新非空字段，留空字段保持不变"""
    update_data = data.model_dump(exclude_unset=True)
    result = batch_update_inventory_fields(
        db, data.device_ids, update_data,
        username=_get_username(request)
    )
    return {
        "message": f"成功更新 {result['updated']} 台设备"
        + (f"，失败 {len(result['failed'])} 台" if result['failed'] else ""),
        **result
    }


@router.post("/import")
async def import_inventory(
    file: UploadFile = File(...), db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="只支持CSV文件格式")

    try:
        contents = await file.read()
        csv_content = contents.decode('utf-8-sig')
        lines = csv_content.strip().split('\n')

        if len(lines) < 2:
            raise HTTPException(status_code=400, detail="CSV文件内容为空或格式不正确")

        reader = csv.DictReader(lines)
        if reader.fieldnames:
            reader.fieldnames = [name.strip() for name in reader.fieldnames]

        success_count = 0
        error_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                cleaned_row = {}
                for k, v in row.items():
                    key = k.strip() if k else k
                    value = v.strip() if v and isinstance(v, str) else (v or '')
                    cleaned_row[key] = value

                device_id = cleaned_row.get('设备号', '').strip()
                if not device_id:
                    errors.append(f"第{row_num}行：缺少必填字段(设备号)")
                    error_count += 1
                    continue
                if len(device_id) != 12 or not re.match(r'^[A-Za-z]{3}\d{9}$', device_id):
                    errors.append(f"第{row_num}行：设备号格式错误(应为3字母+9数字=12位): {device_id}")
                    error_count += 1
                    continue

                version = cleaned_row.get('版本', '').strip()
                if version and version not in ('WiFi', '4G'):
                    errors.append(f"第{row_num}行：版本 '{version}' 无效")
                    error_count += 1
                    continue

                device_type = cleaned_row.get('类型', '').strip()
                if device_type and device_type not in ('睡眠', '跌倒'):
                    errors.append(f"第{row_num}行：类型 '{device_type}' 无效")
                    error_count += 1
                    continue

                packaging = cleaned_row.get('包装', '').strip()
                if packaging and packaging not in ('简约', '精品'):
                    errors.append(f"第{row_num}行：包装 '{packaging}' 无效")
                    error_count += 1
                    continue

                existing = get_inventory_by_device_id(db, device_id)
                serial_number = cleaned_row.get('序号') or device_id
                delivery_date_str = cleaned_row.get('交付时间', '').strip()

                update_data = InventoryUpdate(
                    version=cleaned_row.get('版本', ''),
                    type=cleaned_row.get('类型', ''),
                    packaging=cleaned_row.get('包装', ''),
                    device_attribute=cleaned_row.get('设备属性', ''),
                    owner=cleaned_row.get('归属人', ''),
                    borrower=cleaned_row.get('领用人', ''),
                    sales_person=cleaned_row.get('销售', ''),
                    iot_card_status=cleaned_row.get('物联网卡状态', '') or None,
                    remarks=cleaned_row.get('备注', ''),
                    supplementary_info=cleaned_row.get('补充信息', ''),
                    delivery_date=datetime.strptime(delivery_date_str, '%Y-%m-%d').date() if delivery_date_str else None
                )

                if existing:
                    # 覆盖更新已有设备（含 serial_number）
                    existing.serial_number = serial_number
                    update_inventory(db, device_id, update_data, username=_get_username(request))
                    success_count += 1
                    continue

                # 检查序号冲突（仅对新建设备）
                existing_serial = db.query(Inventory).filter(
                    Inventory.serial_number == serial_number
                ).first()
                if existing_serial:
                    errors.append(f"第{row_num}行：序号 {serial_number} 已存在（设备 {existing_serial.device_id}）")
                    error_count += 1
                    continue

                create_data = InventoryCreate(
                    serial_number=serial_number,
                    device_id=device_id,
                    version=update_data.version,
                    type=update_data.type,
                    packaging=update_data.packaging,
                    device_attribute=update_data.device_attribute,
                    owner=update_data.owner,
                    borrower=update_data.borrower,
                    sales_person=update_data.sales_person,
                    iot_card_status=update_data.iot_card_status,
                    remarks=update_data.remarks,
                    supplementary_info=update_data.supplementary_info,
                    delivery_date=update_data.delivery_date
                )
                create_inventory(db, create_data, username=_get_username(request))
                success_count += 1
            except Exception as e:
                errors.append(f"第{row_num}行：{str(e)}")
                error_count += 1

        return {
            "success": True,
            "message": f"导入完成：成功 {success_count} 条，失败 {error_count} 条",
            "success_count": success_count, "error_count": error_count,
            "errors": errors[:10]
        }
    except Exception as e:
        logger.error(f"导入失败: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
