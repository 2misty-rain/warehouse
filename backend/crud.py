from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models import Inventory, Reminders, AILogs, BorrowRecord, OperationLog, User, ConversationHistory, Reservation
from models import DeviceStatusLog, DeviceGroup, DeviceGroupItem, OfflineIncident, AnomalyRecord, AnomalyAction
from models import DataSyncLog, DailyReport, WeeklyReport, FirmwareConfig
from models import DeviceTag, SmartGroupRule, DeviceHealthScore, InstitutionRegion, BatchOperation
from schemas import InventoryCreate, InventoryUpdate, ReminderCreate, BorrowRecordCreate, BorrowRecordReturn
from datetime import datetime, date, timedelta
import json
import logging

logger = logging.getLogger(__name__)


# ========== Inventory CRUD ==========

def get_inventory(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Inventory).offset(skip).limit(limit).all()


def get_inventory_by_device_id(db: Session, device_id: str):
    return db.query(Inventory).filter(Inventory.device_id == device_id).first()


def create_inventory(db: Session, inventory: InventoryCreate, username: str = "system"):
    data = inventory.model_dump()
    if not data.get('serial_number'):
        data['serial_number'] = data['device_id']
    db_inventory = Inventory(**data)
    db.add(db_inventory)
    db.flush()
    db.refresh(db_inventory)
    _log_operation(db, username, "create", db_inventory.device_id, data)
    db.commit()
    return db_inventory


def update_inventory(db: Session, device_id: str, inventory_update: InventoryUpdate, username: str = "system"):
    db_inventory = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not db_inventory:
        return None

    for key, value in inventory_update.model_dump(exclude_unset=True).items():
        setattr(db_inventory, key, value)

    db_inventory.updated_at = datetime.utcnow()
    db.flush()
    db.refresh(db_inventory)
    _log_operation(db, username, "update", device_id, inventory_update.model_dump(exclude_unset=True))
    db.commit()
    return db_inventory


def delete_inventory(db: Session, device_id: str, username: str = "system"):
    db_inventory = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not db_inventory:
        return False

    db.delete(db_inventory)
    db.flush()
    _log_operation(db, username, "delete", device_id, {"device_id": device_id})
    db.commit()
    return True


def get_inventory_count(db: Session):
    return db.query(Inventory).count()


def get_inventory_by_version(db: Session, version: str):
    return db.query(Inventory).filter(Inventory.version == version).count()


def get_inventory_by_type(db: Session, type_name: str):
    return db.query(Inventory).filter(Inventory.type == type_name).count()


def update_iot_card_status(db: Session, device_id: str, status: str, username: str = "system") -> bool:
    """更新4G设备的物联网卡状态"""
    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not device:
        return False
    if device.version != '4G':
        return False  # WiFi设备无IoT卡
    device.iot_card_status = status
    device.updated_at = datetime.utcnow()
    _log_operation(db, username, "update_iot", device_id, {"iot_card_status": status})
    db.commit()
    return True


def batch_update_iot_card_status(db: Session, device_ids: list, status: str, username: str = "system") -> dict:
    """批量更新物联网卡状态"""
    updated = 0
    failed = []
    for device_id in device_ids:
        if update_iot_card_status(db, device_id, status, username):
            updated += 1
        else:
            failed.append(device_id)
    return {"updated": updated, "failed": failed}


def batch_update_inventory_fields(db: Session, device_ids: list, update_data: dict, username: str = "system") -> dict:
    """批量更新设备字段，只更新非空字段"""
    updated = 0
    failed = []
    # 过滤掉 None 值和空的 device_ids
    fields_to_update = {k: v for k, v in update_data.items()
                        if v is not None and v != '' and k != 'device_ids'}
    if not fields_to_update:
        return {"updated": 0, "failed": device_ids, "message": "没有要更新的字段"}

    for device_id in device_ids:
        device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
        if not device:
            failed.append(device_id)
            continue
        for key, value in fields_to_update.items():
            # WiFi设备跳过IoT卡状态
            if key == 'iot_card_status' and device.version != '4G':
                continue
            setattr(device, key, value)
        device.updated_at = datetime.utcnow()
        updated += 1
        _log_operation(db, username, "batch_update", device_id, fields_to_update)

    db.commit()
    return {"updated": updated, "failed": failed}


# ========== Reminder CRUD ==========

def get_reminders(db: Session, is_processed: bool = None):
    query = db.query(Reminders)
    if is_processed is not None:
        query = query.filter(Reminders.is_processed == is_processed)
    return query.all()


def create_reminder(db: Session, reminder: ReminderCreate):
    db_reminder = Reminders(**reminder.model_dump())
    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return db_reminder


def update_reminder_status(db: Session, reminder_id: int, is_processed: bool):
    db_reminder = db.query(Reminders).filter(Reminders.id == reminder_id).first()
    if not db_reminder:
        return None
    db_reminder.is_processed = is_processed
    db.commit()
    db.refresh(db_reminder)
    return db_reminder


def delete_reminder(db: Session, reminder_id: int):
    db_reminder = db.query(Reminders).filter(Reminders.id == reminder_id).first()
    if not db_reminder:
        return False
    db.delete(db_reminder)
    db.commit()
    return True


# ========== AI Logs CRUD ==========

def create_ai_log(db: Session, user_input: str, ai_parsed_action: str, affected_records: str, operation_result: str):
    ai_log = AILogs(
        user_input=user_input,
        ai_parsed_action=ai_parsed_action,
        affected_records=affected_records,
        operation_result=operation_result
    )
    db.add(ai_log)
    db.commit()
    db.refresh(ai_log)
    return ai_log


# ========== Operation Log CRUD ==========

def _log_operation(db: Session, username: str, operation_type: str, device_id: str, details: dict):
    try:
        log = OperationLog(
            username=username,
            operation_type=operation_type,
            device_id=device_id,
            details=json.dumps(details, ensure_ascii=False, default=str)
        )
        db.add(log)
        db.flush()
    except Exception as e:
        logger.warning(f"操作日志记录失败(非关键): {e}")


def get_operation_logs(db: Session, operation_type: str = None, username: str = None,
                       skip: int = 0, limit: int = 100):
    query = db.query(OperationLog)
    if operation_type:
        query = query.filter(OperationLog.operation_type == operation_type)
    if username:
        query = query.filter(OperationLog.username == username)
    total = query.count()
    items = query.order_by(OperationLog.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


# ========== Dashboard Statistics ==========

def get_dashboard_stats(db: Session):
    total_devices = db.query(Inventory).count()
    available_devices = db.query(Inventory).filter(
        Inventory.borrower == None,
        Inventory.device_attribute != '商机交付'
    ).count()
    sold_devices = db.query(Inventory).filter(
        Inventory.device_attribute == '商机交付'
    ).count()

    wifi_devices = db.query(Inventory).filter(Inventory.version == "WiFi").count()
    g4_devices = db.query(Inventory).filter(Inventory.version == "4G").count()
    sleep_devices = db.query(Inventory).filter(Inventory.type == "睡眠").count()
    fall_devices = db.query(Inventory).filter(Inventory.type == "跌倒").count()
    active_iot_cards = db.query(Inventory).filter(
        Inventory.iot_card_status == '开卡'
    ).count()

    unprocessed_reminders = db.query(Reminders).filter(Reminders.is_processed == False).count()

    today = date.today()

    upcoming_trial_end = db.query(Reminders).filter(
        Reminders.reminder_type == 'trial_period',
        Reminders.is_processed == False,
        Reminders.due_date >= today,
        Reminders.due_date <= today + timedelta(days=7)
    ).count()

    overdue_borrows = db.query(BorrowRecord).filter(
        BorrowRecord.status.in_(['borrowed', 'overdue']),
        BorrowRecord.expected_return_date < today
    ).count()

    long_term_borrows = db.query(BorrowRecord).filter(
        BorrowRecord.status == 'borrowed',
        BorrowRecord.borrow_date <= today - timedelta(days=30)
    ).count()

    return {
        "total_devices": total_devices,
        "available_devices": available_devices,
        "sold_devices": sold_devices,
        "wifi_devices": wifi_devices,
        "g4_devices": g4_devices,
        "sleep_devices": sleep_devices,
        "fall_devices": fall_devices,
        "active_iot_cards": active_iot_cards,
        "unprocessed_reminders": unprocessed_reminders,
        "upcoming_trial_end": upcoming_trial_end,
        "overdue_borrows": overdue_borrows,
        "long_term_borrows": long_term_borrows
    }


def get_sales_trend(db: Session):
    sales_data = db.query(
        func.extract('month', Inventory.delivery_date).label('month'),
        func.count(Inventory.id).label('count')
    ).filter(
        Inventory.device_attribute == '商机交付',
        Inventory.delivery_date.isnot(None)
    ).group_by(
        func.extract('month', Inventory.delivery_date)
    ).order_by(
        func.extract('month', Inventory.delivery_date)
    ).all()

    month_names = ['1月', '2月', '3月', '4月', '5月', '6月',
                   '7月', '8月', '9月', '10月', '11月', '12月']

    result = []
    for month_num, count in sales_data:
        if 1 <= month_num <= 12:
            result.append({
                "month": month_names[int(month_num) - 1],
                "count": count
            })

    if not result:
        result = [{"month": m, "count": 0} for m in month_names]

    return result


# ========== Weekly / Monthly Report ==========

def get_weekly_report(db: Session) -> dict:
    """获取本周出库统计"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    week_devices = db.query(Inventory).filter(
        Inventory.delivery_date >= week_start,
        Inventory.delivery_date <= week_end
    ).all()

    if not week_devices:
        return {
            "period": f"{week_start} ~ {week_end}",
            "total_outbound": 0,
            "by_attribute": [],
            "by_version": [],
            "by_type": []
        }

    attr_counts = {}
    version_counts = {}
    type_counts = {}
    for d in week_devices:
        attr = d.device_attribute or "未分类"
        ver = d.version or "未知"
        typ = d.type or "未知"
        attr_counts[attr] = attr_counts.get(attr, 0) + 1
        version_counts[ver] = version_counts.get(ver, 0) + 1
        type_counts[typ] = type_counts.get(typ, 0) + 1

    return {
        "period": f"{week_start} ~ {week_end}",
        "total_outbound": len(week_devices),
        "by_attribute": [{"name": k, "count": v} for k, v in sorted(attr_counts.items(), key=lambda x: -x[1])],
        "by_version": [{"name": k, "count": v} for k, v in sorted(version_counts.items(), key=lambda x: -x[1])],
        "by_type": [{"name": k, "count": v} for k, v in sorted(type_counts.items(), key=lambda x: -x[1])]
    }


def get_monthly_report(db: Session) -> dict:
    """获取本月统计"""
    today = date.today()
    month_start = today.replace(day=1)

    month_devices = db.query(Inventory).filter(
        Inventory.delivery_date >= month_start,
        Inventory.delivery_date <= today
    ).all()

    total_outbound = len(month_devices)
    sold_count = sum(1 for d in month_devices if d.device_attribute == '商机交付')
    trial_count = sum(1 for d in month_devices if d.device_attribute == '商机试用')
    demo_count = sum(1 for d in month_devices if d.device_attribute == '产品演示')
    dev_count = sum(1 for d in month_devices if d.device_attribute == '技术开发/测试')
    internal_trial_count = sum(1 for d in month_devices if d.device_attribute == '内部试用')

    active_iot = db.query(Inventory).filter(
        Inventory.version == '4G',
        Inventory.iot_card_status == '开卡'
    ).count()
    inactive_iot = db.query(Inventory).filter(
        Inventory.version == '4G',
        Inventory.iot_card_status == '关卡'
    ).count()
    unset_iot = db.query(Inventory).filter(
        Inventory.version == '4G',
        Inventory.iot_card_status == None
    ).count()

    return {
        "period": f"{month_start} ~ {today}",
        "total_outbound": total_outbound,
        "by_attribute": {
            "sold": sold_count,
            "trial": trial_count,
            "demo": demo_count,
            "dev_test": dev_count,
            "internal_trial": internal_trial_count,
            "other": total_outbound - sold_count - trial_count - demo_count - dev_count - internal_trial_count
        },
        "iot_card_summary": {
            "active": active_iot,
            "inactive": inactive_iot,
            "unset": unset_iot
        }
    }


def get_sales_analysis(db: Session, time_range: str = "全部", group_by: str = None) -> dict:
    """获取销售深度分析"""
    query = db.query(Inventory).filter(
        Inventory.device_attribute == '商机交付'
    )

    today = date.today()
    if time_range == "本周":
        week_start = today - timedelta(days=today.weekday())
        query = query.filter(Inventory.delivery_date >= week_start)
    elif time_range == "本月":
        month_start = today.replace(day=1)
        query = query.filter(Inventory.delivery_date >= month_start)
    elif time_range == "本季度":
        quarter_start = today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1)
        query = query.filter(Inventory.delivery_date >= quarter_start)
    elif time_range == "今年":
        year_start = today.replace(month=1, day=1)
        query = query.filter(Inventory.delivery_date >= year_start)

    sold_devices = query.all()
    total_sold = len(sold_devices)

    result = {"total_sold": total_sold, "time_range": time_range,
              "by_owner": [], "by_version": [], "by_type": []}

    if not group_by or "owner" in (group_by or ""):
        owner_counts = {}
        for d in sold_devices:
            owner = d.owner or "未知甲方"
            owner_counts[owner] = owner_counts.get(owner, 0) + 1
        result["by_owner"] = [{"name": k, "count": v} for k, v in
                              sorted(owner_counts.items(), key=lambda x: -x[1])]

    if not group_by or "version" in (group_by or ""):
        version_counts = {}
        for d in sold_devices:
            ver = d.version or "未知"
            version_counts[ver] = version_counts.get(ver, 0) + 1
        result["by_version"] = [{"name": k, "count": v} for k, v in
                                sorted(version_counts.items(), key=lambda x: -x[1])]

    if not group_by or "type" in (group_by or ""):
        type_counts = {}
        for d in sold_devices:
            typ = d.type or "未知"
            type_counts[typ] = type_counts.get(typ, 0) + 1
        result["by_type"] = [{"name": k, "count": v} for k, v in
                             sorted(type_counts.items(), key=lambda x: -x[1])]

    return result


# ========== Borrow Record CRUD ==========

def create_borrow_record(db: Session, borrow_record: BorrowRecordCreate, username: str = "system"):
    device = db.query(Inventory).filter(Inventory.device_id == borrow_record.device_id).first()
    if not device:
        raise ValueError(f"设备 {borrow_record.device_id} 不存在")

    db_borrow = BorrowRecord(**borrow_record.model_dump())
    db.add(db_borrow)
    db.flush()
    db.refresh(db_borrow)
    _log_operation(db, username, "borrow", borrow_record.device_id, borrow_record.model_dump())
    return db_borrow


def get_borrow_records(db: Session, status: str = None, search: str = None,
                       borrow_date_start: str = None, borrow_date_end: str = None,
                       skip: int = 0, limit: int = 100):
    query = db.query(BorrowRecord)
    if status:
        query = query.filter(BorrowRecord.status == status)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (BorrowRecord.device_id.like(pattern)) |
            (BorrowRecord.borrower.like(pattern)) |
            (BorrowRecord.purpose.like(pattern))
        )
    if borrow_date_start:
        try:
            sd = datetime.strptime(borrow_date_start, "%Y-%m-%d").date()
            query = query.filter(BorrowRecord.borrow_date >= sd)
        except ValueError:
            pass
    if borrow_date_end:
        try:
            ed = datetime.strptime(borrow_date_end, "%Y-%m-%d").date()
            query = query.filter(BorrowRecord.borrow_date <= ed + timedelta(days=1))
        except ValueError:
            pass
    total = query.count()
    items = query.order_by(BorrowRecord.borrow_date.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


def delete_borrow_record(db: Session, record_id: int) -> bool:
    record = db.query(BorrowRecord).filter(BorrowRecord.id == record_id).first()
    if not record:
        return False
    if record.status in ('borrowed', 'overdue'):
        raise ValueError(f"设备 {record.device_id} 仍在借用中，请先归还后再删除")
    db.delete(record)
    db.flush()
    return True


def get_borrow_record_by_id(db: Session, record_id: int):
    return db.query(BorrowRecord).filter(BorrowRecord.id == record_id).first()


def return_device(db: Session, record_id: int, return_data: BorrowRecordReturn, username: str = "system"):
    db_record = db.query(BorrowRecord).filter(BorrowRecord.id == record_id).first()
    if not db_record:
        return None

    if db_record.status == 'returned':
        raise ValueError("该设备已经归还")

    db_record.actual_return_date = return_data.actual_return_date or datetime.now().date()
    db_record.condition_on_return = return_data.condition_on_return
    if return_data.remarks:
        db_record.remarks = f"{db_record.remarks or ''}\n归还备注: {return_data.remarks}"
    db_record.status = 'returned'
    db_record.updated_at = datetime.utcnow()

    device = db.query(Inventory).filter(Inventory.device_id == db_record.device_id).first()
    if device:
        device.borrower = None
        # 归还后无条件重置为现有库存，清除所有分配信息
        device.device_attribute = '现有库存'
        device.owner = None
        device.sales_person = None
        device.supplementary_info = None
        device.remarks = ''
        device.delivery_date = None

    _log_operation(db, username, "return", db_record.device_id, {"record_id": record_id})
    db.commit()
    db.refresh(db_record)
    return db_record


def get_overdue_borrows(db: Session):
    today = date.today()
    return db.query(BorrowRecord).filter(
        BorrowRecord.status.in_(['borrowed', 'overdue']),
        BorrowRecord.expected_return_date < today
    ).all()


def update_overdue_status(db: Session):
    overdue_records = get_overdue_borrows(db)
    for record in overdue_records:
        if record.status != 'overdue':
            record.status = 'overdue'
    db.commit()
    return len(overdue_records)


# ========== User CRUD ==========

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, username: str, password: str, email: str = None, role: str = "operator"):
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = User(
        username=username,
        email=email,
        hashed_password=pwd_context.hash(password),
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_all_users(db: Session):
    return db.query(User).all()


def get_device_timeline(db: Session, device_id: str) -> dict:
    """获取设备全生命周期时间线"""
    events = []

    device = db.query(Inventory).filter(Inventory.device_id == device_id).first()
    if not device:
        return {"device_id": device_id, "events": []}

    events.append({
        "date": device.created_at.strftime("%Y-%m-%d %H:%M") if device.created_at else "未知",
        "event_type": "入库",
        "description": f"设备 {device_id} 入库",
        "operator": "system"
    })

    if device.delivery_date:
        events.append({
            "date": device.delivery_date.strftime("%Y-%m-%d"),
            "event_type": "出库",
            "description": f"设备出库，属性: {device.device_attribute or '未设置'}，归属: {device.owner or '未设置'}",
            "operator": device.sales_person or "system"
        })

    borrow_records = db.query(BorrowRecord).filter(
        BorrowRecord.device_id == device_id
    ).order_by(BorrowRecord.borrow_date.asc()).all()

    for r in borrow_records:
        events.append({
            "date": r.borrow_date.strftime("%Y-%m-%d %H:%M") if r.borrow_date else "未知",
            "event_type": "借出",
            "description": f"{r.borrower} 借用本设备，预计归还: {r.expected_return_date.strftime('%Y-%m-%d') if r.expected_return_date else '未指定'}",
            "operator": r.borrower
        })
        if r.status in ('returned', 'terminated'):
            events.append({
                "date": r.actual_return_date.strftime("%Y-%m-%d") if r.actual_return_date else r.updated_at.strftime(
                    "%Y-%m-%d %H:%M") if r.updated_at else "未知",
                "event_type": "归还" if r.status == 'returned' else "终止",
                "description": f"{r.borrower} 归还/终止借用",
                "operator": r.borrower
            })

    ops = db.query(OperationLog).filter(
        OperationLog.device_id == device_id
    ).order_by(OperationLog.created_at.asc()).all()

    for op in ops:
        events.append({
            "date": op.created_at.strftime("%Y-%m-%d %H:%M") if op.created_at else "未知",
            "event_type": op.operation_type,
            "description": f"操作: {op.operation_type}",
            "operator": op.username or "system"
        })

    events.sort(key=lambda x: x['date'])

    return {"device_id": device_id, "events": events}


# ========== Conversation History ==========

def save_conversation_history(db: Session, user_id: str, role: str, content: str):
    record = ConversationHistory(user_id=user_id, role=role, content=content)
    db.add(record)
    db.commit()


def load_conversation_history(db: Session, user_id: str, limit: int = 20):
    records = db.query(ConversationHistory).filter(
        ConversationHistory.user_id == user_id
    ).order_by(ConversationHistory.created_at.desc()).limit(limit).all()

    return [{"role": r.role, "content": r.content} for r in reversed(records)]


# ========== Reservation CRUD ==========

def create_reservation(db: Session, data: dict, applicant: str):
    reservation = Reservation(
        applicant=applicant,
        quantity=data.get('quantity', 1),
        version_req=data.get('version_req', ''),
        packaging_req=data.get('packaging_req', ''),
        client_name=data.get('client_name', ''),
        sales_person=data.get('sales_person', ''),
        required_date=data.get('required_date'),
        purpose=data.get('purpose', ''),
        status='pending'
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def get_reservations(db: Session, applicant: str = None, status: str = None,
                     skip: int = 0, limit: int = 100):
    query = db.query(Reservation)
    if applicant:
        query = query.filter(Reservation.applicant == applicant)
    if status:
        query = query.filter(Reservation.status == status)
    total = query.count()
    items = query.order_by(Reservation.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


def get_reservation_by_id(db: Session, reservation_id: int):
    return db.query(Reservation).filter(Reservation.id == reservation_id).first()


def get_pending_reservations_count(db: Session) -> int:
    return db.query(Reservation).filter(Reservation.status == 'pending').count()


def approve_reservation(db: Session, reservation_id: int, assigned_devices: list,
                        admin_username: str, admin_remarks: str = None):
    import json
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise ValueError("申请不存在")
    if reservation.status != 'pending':
        raise ValueError(f"申请状态为 {reservation.status}，无法审批")

    reservation.status = 'approved'
    reservation.admin_username = admin_username
    reservation.assigned_devices = json.dumps(assigned_devices, ensure_ascii=False)
    if admin_remarks:
        reservation.admin_remarks = admin_remarks
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    return reservation


def fulfill_reservation(db: Session, reservation_id: int, admin_username: str):
    """执行出库：修改库存设备属性 + 创建借出记录"""
    import json
    from models import Inventory, BorrowRecord

    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise ValueError("申请不存在")
    if reservation.status not in ('approved',):
        raise ValueError(f"申请状态为 {reservation.status}，无法执行出库")

    device_ids = json.loads(reservation.assigned_devices or '[]')
    if not device_ids:
        raise ValueError("未分配设备号")

    fulfilled = []
    failed = []
    for did in device_ids:
        device = db.query(Inventory).filter(
            Inventory.device_id == did
        ).with_for_update().first()
        if not device:
            failed.append(f"{did}(不存在)")
            continue
        if device.device_attribute == '商机交付':
            failed.append(f"{did}(已售出)")
            continue
        if device.borrower:
            failed.append(f"{did}(被{device.borrower}借用中)")
            continue

        # 更新设备为组织售卖
        device.device_attribute = '商机交付'
        device.owner = reservation.client_name or ''
        device.sales_person = reservation.sales_person or ''
        device.delivery_date = date.today()
        device.updated_at = datetime.utcnow()

        # 创建出库记录
        borrower_name = (reservation.sales_person or '').strip() or (reservation.applicant or '').strip()
        if not borrower_name:
            failed.append(f"{did}(无有效借用人)")
            continue
        borrow = BorrowRecord(
            device_id=did,
            borrower=borrower_name,
            expected_return_date=reservation.required_date,
            purpose=f"组织售卖出库: {reservation.purpose or ''}",
            status='borrowed',
            remarks=f"预约出库, 甲方: {reservation.client_name or ''}"
        )
        db.add(borrow)
        _log_operation(db, admin_username, "fulfill_reservation", did,
                       {"reservation_id": reservation_id, "client": reservation.client_name})
        fulfilled.append(did)

    reservation.status = 'fulfilled'
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    return {"fulfilled": fulfilled, "failed": failed, "reservation": reservation}


def reject_reservation(db: Session, reservation_id: int, admin_username: str,
                       admin_remarks: str = None):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise ValueError("申请不存在")
    if reservation.status != 'pending':
        raise ValueError(f"申请状态为 {reservation.status}，无法驳回")

    reservation.status = 'rejected'
    reservation.admin_username = admin_username
    if admin_remarks:
        reservation.admin_remarks = admin_remarks
    reservation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reservation)
    return reservation


# ========== 运营平台 CRUD ==========

# --- Device Status Logs ---

def save_device_status_logs(db: Session, logs: list) -> int:
    """批量保存设备状态检查记录"""
    count = 0
    for log_data in logs:
        entry = DeviceStatusLog(**log_data)
        db.add(entry)
        count += 1
    db.commit()
    return count


def get_latest_device_status(db: Session, device_ids: list = None, organization: str = None) -> list:
    """获取设备最新状态（每个设备取最新一条）"""
    from sqlalchemy import and_

    subq = db.query(
        DeviceStatusLog.device_id,
        func.max(DeviceStatusLog.check_time).label('max_time')
    ).group_by(DeviceStatusLog.device_id)

    if device_ids:
        subq = subq.filter(DeviceStatusLog.device_id.in_(device_ids))

    subq = subq.subquery()

    query = db.query(DeviceStatusLog).join(
        subq,
        and_(
            DeviceStatusLog.device_id == subq.c.device_id,
            DeviceStatusLog.check_time == subq.c.max_time
        )
    )

    if organization:
        query = query.filter(DeviceStatusLog.organization == organization)

    return query.all()


def get_device_status_history(db: Session, device_id: str, days: int = 7) -> list:
    """获取设备状态历史"""
    since = datetime.utcnow() - timedelta(days=days)
    return db.query(DeviceStatusLog).filter(
        DeviceStatusLog.device_id == device_id,
        DeviceStatusLog.check_time >= since
    ).order_by(DeviceStatusLog.check_time.desc()).all()


# --- Device Groups ---

def create_device_group(db: Session, name: str, device_ids: list, username: str, description: str = None) -> DeviceGroup:
    group = DeviceGroup(name=name, description=description, created_by=username)
    db.add(group)
    db.flush()
    for did in device_ids:
        item = DeviceGroupItem(group_id=group.id, device_id=did)
        db.add(item)
    db.commit()
    db.refresh(group)
    return group


def get_device_groups(db: Session) -> list:
    groups = db.query(DeviceGroup).order_by(DeviceGroup.created_at.desc()).all()
    result = []
    for g in groups:
        items = db.query(DeviceGroupItem).filter(DeviceGroupItem.group_id == g.id).all()
        result.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "created_by": g.created_by,
            "device_count": len(items),
            "device_ids": [item.device_id for item in items],
            "created_at": g.created_at.strftime("%Y-%m-%d %H:%M") if g.created_at else None,
        })
    return result


def get_device_group_by_id(db: Session, group_id: int) -> dict:
    g = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not g:
        return None
    items = db.query(DeviceGroupItem).filter(DeviceGroupItem.group_id == g.id).all()
    return {
        "id": g.id,
        "name": g.name,
        "description": g.description,
        "created_by": g.created_by,
        "device_count": len(items),
        "device_ids": [item.device_id for item in items],
        "created_at": g.created_at.strftime("%Y-%m-%d %H:%M") if g.created_at else None,
    }


def update_device_group(db: Session, group_id: int, name: str = None, description: str = None, device_ids: list = None) -> dict:
    g = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not g:
        return None
    if name:
        g.name = name
    if description is not None:
        g.description = description
    if device_ids is not None:
        db.query(DeviceGroupItem).filter(DeviceGroupItem.group_id == group_id).delete()
        for did in device_ids:
            item = DeviceGroupItem(group_id=group_id, device_id=did)
            db.add(item)
    db.commit()
    return get_device_group_by_id(db, group_id)


def delete_device_group(db: Session, group_id: int) -> bool:
    g = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not g:
        return False
    db.query(DeviceGroupItem).filter(DeviceGroupItem.group_id == group_id).delete()
    db.delete(g)
    db.commit()
    return True


# --- Offline Incidents ---

def create_offline_incident(db: Session, device_id: str, organization: str, offline_duration: int = 0,
                            firmware_version: str = None) -> OfflineIncident:
    """创建离线事件（如果同设备同原因已静默则跳过）"""
    silenced = db.query(OfflineIncident).filter(
        OfflineIncident.device_id == device_id,
        OfflineIncident.is_silenced == True
    ).first()
    if silenced:
        return None

    incident = OfflineIncident(
        device_id=device_id,
        organization=organization,
        detected_at=datetime.utcnow(),
        offline_duration=offline_duration,
        firmware_version=firmware_version,
        status='待处理'
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def get_offline_incidents(db: Session, status: str = None, organization: str = None,
                          skip: int = 0, limit: int = 100) -> dict:
    query = db.query(OfflineIncident)
    if status:
        query = query.filter(OfflineIncident.status == status)
    if organization:
        query = query.filter(OfflineIncident.organization == organization)
    total = query.count()
    items = query.order_by(OfflineIncident.detected_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


def handle_offline_incident(db: Session, incident_id: int, reason_tag: str, notes: str, username: str) -> OfflineIncident:
    incident = db.query(OfflineIncident).filter(OfflineIncident.id == incident_id).first()
    if not incident:
        return None
    incident.reason_tag = reason_tag
    incident.notes = notes
    incident.handled_by = username
    incident.handled_at = datetime.utcnow()
    incident.status = '已处理'
    if reason_tag == '用户断电':
        incident.is_silenced = True
    db.commit()
    db.refresh(incident)
    return incident


def auto_close_offline_incident(db: Session, device_id: str) -> int:
    """设备恢复上线后自动关闭未处理事件"""
    count = db.query(OfflineIncident).filter(
        OfflineIncident.device_id == device_id,
        OfflineIncident.status == '待处理'
    ).update({"status": "已关闭", "updated_at": datetime.utcnow()})
    db.commit()
    return count


# --- Anomaly Records ---

def create_anomaly_records_batch(db: Session, records: list) -> int:
    """批量创建异常记录（去重 + 忽略规则过滤）"""
    from models import AnomalyIgnoreRule

    # 加载所有忽略规则
    ignore_rules = db.query(AnomalyIgnoreRule).all()
    ignore_map = {}
    for rule in ignore_rules:
        key = (rule.device_id, rule.anomaly_type or '*')
        ignore_map[key] = True

    count = 0
    for r in records:
        did = r.get('device_id', '')
        atype = r.get('anomaly_type', '')

        # 检查忽略规则
        if (did, atype) in ignore_map or (did, '*') in ignore_map:
            continue

        exists = db.query(AnomalyRecord).filter(
            AnomalyRecord.record_date == r.get('record_date'),
            AnomalyRecord.device_id == did,
            AnomalyRecord.anomaly_type == atype
        ).first()
        if exists:
            continue
        entry = AnomalyRecord(**r)
        db.add(entry)
        count += 1
    db.commit()
    return count


def get_anomaly_records(db: Session, status: str = None, institution: str = None,
                        anomaly_type: str = None, priority: str = None,
                        record_date: str = None, algorithm_tag: str = None,
                        search: str = None, skip: int = 0, limit: int = 100) -> dict:
    query = db.query(AnomalyRecord)
    if status:
        query = query.filter(AnomalyRecord.status == status)
    if institution:
        query = query.filter(AnomalyRecord.institution == institution)
    if anomaly_type:
        query = query.filter(AnomalyRecord.anomaly_type == anomaly_type)
    if priority:
        query = query.filter(AnomalyRecord.priority == priority)
    if record_date:
        try:
            rd = datetime.strptime(record_date, "%Y-%m-%d").date()
            query = query.filter(AnomalyRecord.record_date == rd)
        except ValueError:
            pass
    if algorithm_tag:
        query = query.filter(AnomalyRecord.algorithm_tag == algorithm_tag)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (AnomalyRecord.person_name.like(pattern)) |
            (AnomalyRecord.device_id.like(pattern)) |
            (AnomalyRecord.institution.like(pattern))
        )
    total = query.count()
    items = query.order_by(
        AnomalyRecord.priority.desc(),
        AnomalyRecord.created_at.desc()
    ).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


def get_anomaly_stats(db: Session) -> dict:
    """获取异常工单各状态计数"""
    statuses = ['待处理', '处理中', '待回访', '已完成', '已归档']
    result = {}
    for s in statuses:
        result[s] = db.query(AnomalyRecord).filter(AnomalyRecord.status == s).count()
    return result


def tag_anomaly_record(db: Session, record_id: int, algorithm_tag: str, algorithm_notes: str, username: str) -> AnomalyRecord:
    """算法标记异常记录"""
    record = db.query(AnomalyRecord).filter(AnomalyRecord.id == record_id).first()
    if not record:
        return None
    record.algorithm_tag = algorithm_tag
    record.algorithm_notes = algorithm_notes
    if algorithm_tag == '需要回访':
        record.status = '待回访'
    elif algorithm_tag == '算法问题':
        record.status = '已归档'
    elif algorithm_tag == '真实案例':
        record.status = '处理中'
    record.updated_at = datetime.utcnow()

    # 记录操作
    action = AnomalyAction(
        record_id=record_id,
        action_by=username,
        action_type='标记',
        content=f"标记为: {algorithm_tag}" + (f" ({algorithm_notes})" if algorithm_notes else "")
    )
    db.add(action)
    db.commit()
    db.refresh(record)
    return record


def handle_anomaly_record(db: Session, record_id: int, resolution: str, username: str, notes: str = None) -> AnomalyRecord:
    """处理异常工单（回访/完成操作）"""
    record = db.query(AnomalyRecord).filter(AnomalyRecord.id == record_id).first()
    if not record:
        return None
    record.resolution = resolution
    record.assigned_to = username
    record.status = '已完成'
    record.resolved_at = datetime.utcnow()
    record.updated_at = datetime.utcnow()

    action = AnomalyAction(
        record_id=record_id,
        action_by=username,
        action_type='完成',
        content=f"处理完成: {resolution}" + (f" (备注: {notes})" if notes else "")
    )
    db.add(action)
    db.commit()
    db.refresh(record)
    return record


def add_anomaly_note(db: Session, record_id: int, content: str, username: str) -> AnomalyAction:
    """添加工单备注"""
    action = AnomalyAction(
        record_id=record_id,
        action_by=username,
        action_type='备注',
        content=content
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def get_anomaly_actions(db: Session, record_id: int) -> list:
    """获取工单操作时间线"""
    return db.query(AnomalyAction).filter(
        AnomalyAction.record_id == record_id
    ).order_by(AnomalyAction.created_at.asc()).all()


# --- Data Sync Logs ---

def create_sync_log(db: Session, sync_date: date, sync_type: str = 'auto') -> DataSyncLog:
    log = DataSyncLog(
        sync_date=sync_date,
        sync_type=sync_type,
        status='running',
        started_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_sync_log(db: Session, log_id: int, status: str, stats: dict = None, error_message: str = None):
    log = db.query(DataSyncLog).filter(DataSyncLog.id == log_id).first()
    if not log:
        return
    log.status = status
    log.finished_at = datetime.utcnow()
    if stats:
        log.stats = stats
    if error_message:
        log.error_message = error_message
    db.commit()


def get_latest_sync_log(db: Session, sync_type: str = None) -> DataSyncLog:
    query = db.query(DataSyncLog)
    if sync_type:
        query = query.filter(DataSyncLog.sync_type == sync_type)
    return query.order_by(DataSyncLog.started_at.desc()).first()


# --- Reports ---

def create_daily_report(db: Session, report_date: date, data: dict) -> DailyReport:
    existing = db.query(DailyReport).filter(DailyReport.report_date == report_date).first()
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    report = DailyReport(report_date=report_date, **data)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_daily_report(db: Session, report_date: date) -> DailyReport:
    return db.query(DailyReport).filter(DailyReport.report_date == report_date).first()


def create_weekly_report(db: Session, week_start: date, week_end: date, data: dict) -> WeeklyReport:
    existing = db.query(WeeklyReport).filter(
        WeeklyReport.week_start == week_start,
        WeeklyReport.week_end == week_end
    ).first()
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    report = WeeklyReport(week_start=week_start, week_end=week_end, **data)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_weekly_report(db: Session, week_start: date = None, week_end: date = None) -> WeeklyReport:
    query = db.query(WeeklyReport)
    if week_start:
        query = query.filter(WeeklyReport.week_start == week_start)
    if week_end:
        query = query.filter(WeeklyReport.week_end == week_end)
    return query.order_by(WeeklyReport.week_start.desc()).first()


# --- Firmware Config ---

def get_firmware_config(db: Session) -> FirmwareConfig:
    return db.query(FirmwareConfig).order_by(FirmwareConfig.id.desc()).first()


def set_firmware_config(db: Session, version: str, username: str) -> FirmwareConfig:
    config = FirmwareConfig(
        current_normal_version=version,
        updated_by=username,
        updated_at=datetime.utcnow()
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


# --- Device Monitoring Page Helpers ---

def get_monitored_devices(db: Session, attributes: list = None) -> list:
    """获取需要监控的设备列表（从库存表）"""
    if attributes is None:
        attributes = ['商机交付', '商机试用']
    devices = db.query(Inventory).filter(
        Inventory.device_attribute.in_(attributes)
    ).all()
    return devices


def get_organization_device_summary(db: Session, attributes: list = None) -> list:
    """按机构统计监控设备数量（从库存表）"""
    if attributes is None:
        attributes = ['商机交付', '商机试用']

    devices = db.query(Inventory).filter(
        Inventory.device_attribute.in_(attributes)
    ).all()

    org_map = {}
    for d in devices:
        org = d.owner or '未分配机构'
        if org not in org_map:
            org_map[org] = {"total": 0, "device_ids": []}
        org_map[org]["total"] += 1
        org_map[org]["device_ids"].append(d.device_id)

    return [{"organization": k, **v} for k, v in org_map.items()]


# ========== 企业级扩展 CRUD ==========

# --- Device Tags ---

def set_device_tags(db: Session, device_ids: list, tag_key: str, tag_value: str, username: str) -> int:
    """给设备设置标签（覆盖同key标签）"""
    count = 0
    for did in device_ids:
        existing = db.query(DeviceTag).filter(
            DeviceTag.device_id == did, DeviceTag.tag_key == tag_key
        ).first()
        if existing:
            existing.tag_value = tag_value
        else:
            db.add(DeviceTag(device_id=did, tag_key=tag_key, tag_value=tag_value, created_by=username))
        count += 1
    db.commit()
    return count


def delete_device_tag(db: Session, device_id: str, tag_key: str) -> bool:
    db.query(DeviceTag).filter(
        DeviceTag.device_id == device_id, DeviceTag.tag_key == tag_key
    ).delete()
    db.commit()
    return True


def get_device_tags(db: Session, device_id: str) -> dict:
    tags = db.query(DeviceTag).filter(DeviceTag.device_id == device_id).all()
    return {t.tag_key: t.tag_value for t in tags}


def get_all_tags(db: Session) -> list:
    """获取所有已存在的标签键值对"""
    tags = db.query(DeviceTag).all()
    tag_map = {}
    for t in tags:
        if t.tag_key not in tag_map:
            tag_map[t.tag_key] = set()
        tag_map[t.tag_key].add(t.tag_value)
    return [{"key": k, "values": list(v)} for k, v in tag_map.items()]


def get_devices_by_tag(db: Session, tag_key: str, tag_value: str) -> list:
    tags = db.query(DeviceTag).filter(
        DeviceTag.tag_key == tag_key, DeviceTag.tag_value == tag_value
    ).all()
    return [t.device_id for t in tags]


# --- Smart Group Rules ---

def create_smart_group(db: Session, data: dict, username: str) -> SmartGroupRule:
    rule = SmartGroupRule(
        name=data['name'],
        description=data.get('description', ''),
        rule_type='smart',
        conditions=data['conditions'],
        created_by=username
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def get_smart_groups(db: Session) -> list:
    return db.query(SmartGroupRule).order_by(SmartGroupRule.created_at.desc()).all()


def get_smart_group_by_id(db: Session, rule_id: int) -> SmartGroupRule:
    return db.query(SmartGroupRule).filter(SmartGroupRule.id == rule_id).first()


def update_smart_group(db: Session, rule_id: int, data: dict) -> SmartGroupRule:
    rule = db.query(SmartGroupRule).filter(SmartGroupRule.id == rule_id).first()
    if not rule:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    return rule


def delete_smart_group(db: Session, rule_id: int) -> bool:
    rule = db.query(SmartGroupRule).filter(SmartGroupRule.id == rule_id).first()
    if not rule:
        return False
    db.delete(rule)
    db.commit()
    return True


def evaluate_smart_group(db: Session, rule_id: int) -> list:
    """评估智能分组规则，返回匹配的设备号列表"""
    rule = db.query(SmartGroupRule).filter(SmartGroupRule.id == rule_id).first()
    if not rule or not rule.enabled:
        return []

    conditions = rule.conditions
    logic = conditions.get('logic', 'AND')
    filters = conditions.get('filters', [])

    if not filters:
        return []

    query = db.query(Inventory)

    for f in filters:
        field = f.get('field', '')
        op = f.get('operator', 'eq')
        value = f.get('value', '')

        if field.startswith('tags.'):
            # 标签字段：子查询
            tag_key = field[5:]
            tagged_devices = get_devices_by_tag(db, tag_key, value)
            if logic == 'AND':
                query = query.filter(Inventory.device_id.in_(tagged_devices))
            else:
                query = query.filter(Inventory.device_id.in_(tagged_devices))
        elif field == 'device_attribute':
            query = _apply_filter(query, Inventory.device_attribute, op, value, logic)
        elif field == 'version':
            query = _apply_filter(query, Inventory.version, op, value, logic)
        elif field == 'type':
            query = _apply_filter(query, Inventory.type, op, value, logic)
        elif field == 'owner':
            query = _apply_filter(query, Inventory.owner, op, value, logic)
        elif field == 'packaging':
            query = _apply_filter(query, Inventory.packaging, op, value, logic)

    devices = query.all()
    return [d.device_id for d in devices]


def _apply_filter(query, column, op: str, value: str, logic: str):
    """应用单个过滤条件"""
    if op == 'eq':
        return query.filter(column == value)
    elif op == 'neq':
        return query.filter(column != value)
    elif op == 'contains':
        return query.filter(column.like(f'%{value}%'))
    elif op == 'in':
        vals = [v.strip() for v in value.split(',')]
        return query.filter(column.in_(vals))
    return query


# --- Device Health Score ---

def calculate_device_health(db: Session, device_id: str) -> dict:
    """计算单个设备的健康度评分"""
    from datetime import datetime as dt

    # 1. 在线率子分 (40%)
    recent_logs = db.query(DeviceStatusLog).filter(
        DeviceStatusLog.device_id == device_id
    ).order_by(DeviceStatusLog.check_time.desc()).limit(10).all()

    if recent_logs:
        online_count = sum(1 for l in recent_logs if l.is_online)
        online_rate = online_count / len(recent_logs)
        online_score = int(online_rate * 100)
    else:
        online_score = 100  # 无数据默认满分

    # 2. 固件合规子分 (30%)
    latest = recent_logs[0] if recent_logs else None
    fw_config = db.query(FirmwareConfig).order_by(FirmwareConfig.id.desc()).first()
    if latest and fw_config and latest.firmware_version:
        from routers.operations import _version_less_than
        if latest.needs_firmware_update:
            firmware_score = 40
        else:
            firmware_score = 100
    else:
        firmware_score = 100

    # 3. 异常频率子分 (20%)
    today = dt.utcnow().date()
    week_ago = today - timedelta(days=7)
    recent_anomalies = db.query(AnomalyRecord).filter(
        AnomalyRecord.device_id == device_id,
        AnomalyRecord.record_date >= week_ago
    ).count()
    if recent_anomalies >= 5:
        anomaly_score = 0
    elif recent_anomalies >= 3:
        anomaly_score = 40
    elif recent_anomalies >= 1:
        anomaly_score = 70
    else:
        anomaly_score = 100

    # 4. 离线历史子分 (10%)
    offline_incidents = db.query(OfflineIncident).filter(
        OfflineIncident.device_id == device_id,
        OfflineIncident.detected_at >= week_ago
    ).count()
    if offline_incidents >= 3:
        offline_history_score = 20
    elif offline_incidents >= 1:
        offline_history_score = 60
    else:
        offline_history_score = 100

    # 综合评分
    score = int(
        online_score * 0.4 +
        firmware_score * 0.3 +
        anomaly_score * 0.2 +
        offline_history_score * 0.1
    )

    if score >= 90:
        grade = 'A'
    elif score >= 70:
        grade = 'B'
    elif score >= 50:
        grade = 'C'
    else:
        grade = 'D'

    result = {
        "device_id": device_id,
        "score": score,
        "grade": grade,
        "online_score": online_score,
        "firmware_score": firmware_score,
        "anomaly_score": anomaly_score,
        "offline_history_score": offline_history_score,
        "details": {
            "recent_checks": len(recent_logs),
            "online_rate": f"{online_score}%",
            "fw_status": "需更新" if (latest and latest.needs_firmware_update) else "正常",
            "week_anomalies": recent_anomalies,
            "week_offline_incidents": offline_incidents,
        }
    }

    # 保存到数据库
    existing = db.query(DeviceHealthScore).filter(
        DeviceHealthScore.device_id == device_id
    ).order_by(DeviceHealthScore.calculated_at.desc()).first()

    if not existing or (dt.utcnow() - existing.calculated_at).total_seconds() > 3600:
        entry = DeviceHealthScore(**result, calculated_at=dt.utcnow())
        db.add(entry)
        db.commit()

    return result


def get_health_scores_by_org(db: Session) -> list:
    """获取按机构汇总的健康度"""
    devices = get_monitored_devices(db)
    org_scores = {}
    for d in devices:
        org = d.owner or '未分配机构'
        if org not in org_scores:
            org_scores[org] = {"scores": [], "count": 0}
        score_data = calculate_device_health(db, d.device_id)
        org_scores[org]["scores"].append(score_data["score"])
        org_scores[org]["count"] += 1

    result = []
    for org, data in org_scores.items():
        scores = data["scores"]
        avg = sum(scores) / len(scores) if scores else 0
        result.append({
            "organization": org,
            "avg_score": round(avg, 1),
            "grade_a_count": sum(1 for s in scores if s >= 90),
            "grade_b_count": sum(1 for s in scores if 70 <= s < 90),
            "grade_c_count": sum(1 for s in scores if 50 <= s < 70),
            "grade_d_count": sum(1 for s in scores if s < 50),
            "total_devices": data["count"],
        })
    result.sort(key=lambda x: x["avg_score"])
    return result


# --- Institution Regions ---

def get_all_regions(db: Session) -> list:
    return db.query(InstitutionRegion).all()


def upsert_region(db: Session, data: dict, username: str) -> InstitutionRegion:
    existing = db.query(InstitutionRegion).filter(
        InstitutionRegion.institution_name == data['institution_name']
    ).first()
    if existing:
        for k, v in data.items():
            if v is not None:
                setattr(existing, k, v)
        existing.updated_by = username
        db.commit()
        db.refresh(existing)
        return existing
    entry = InstitutionRegion(**data, updated_by=username)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_region_tree(db: Session) -> list:
    """获取地域树形结构"""
    regions = db.query(InstitutionRegion).all()
    tree = {}
    for r in regions:
        reg = r.region or '未分类'
        if reg not in tree:
            tree[reg] = {}
        city = r.city or '未分类'
        if city not in tree[reg]:
            tree[reg][city] = []
        tree[reg][city].append(r.institution_name)
    return [
        {"region": reg, "cities": [
            {"city": city, "institutions": insts}
            for city, insts in cities.items()
        ]}
        for reg, cities in tree.items()
    ]


# --- Batch Operations ---

def create_batch_operation(db: Session, op_type: str, target_type: str, target_id: str,
                           params: dict, username: str) -> BatchOperation:
    job = BatchOperation(
        operation_type=op_type,
        target_type=target_type,
        target_id=target_id,
        params=params,
        status='running',
        operated_by=username,
        started_at=datetime.utcnow()
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_batch_operation(db: Session, job_id: int, status: str,
                           affected: int = 0, success: int = 0, failed: int = 0):
    job = db.query(BatchOperation).filter(BatchOperation.id == job_id).first()
    if job:
        job.status = status
        job.affected_count = affected
        job.success_count = success
        job.failed_count = failed
        job.finished_at = datetime.utcnow()
        db.commit()


def get_batch_operations(db: Session, skip: int = 0, limit: int = 20) -> list:
    return db.query(BatchOperation).order_by(
        BatchOperation.created_at.desc()
    ).offset(skip).limit(limit).all()


# --- Command Center ---

def get_command_center_data(db: Session) -> dict:
    """获取运营指挥中心总览数据"""
    from datetime import datetime as dt

    devices = get_monitored_devices(db)
    monitored_ids = [d.device_id for d in devices]
    institutions = list(set(d.owner or '未分配机构' for d in devices))

    # 在线率
    statuses = get_latest_device_status(db, device_ids=monitored_ids) if monitored_ids else []
    online_count = sum(1 for s in statuses if s.is_online)
    online_rate = round(online_count / len(statuses) * 100, 1) if statuses else 0

    # 健康度汇总
    health_scores = [calculate_device_health(db, did) for did in monitored_ids]
    avg_health = round(sum(h['score'] for h in health_scores) / len(health_scores), 1) if health_scores else 100

    # 工单和事件
    pending_tickets = db.query(AnomalyRecord).filter(AnomalyRecord.status == '待处理').count()
    pending_incidents = db.query(OfflineIncident).filter(OfflineIncident.status == '待处理').count()

    # 本周趋势（简化为最近7天）
    today = dt.utcnow().date()
    weekly_trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_logs = db.query(DeviceStatusLog).filter(
            func.date(DeviceStatusLog.check_time) == d,
            DeviceStatusLog.device_id.in_(monitored_ids)
        ).all() if monitored_ids else []
        day_online = sum(1 for l in day_logs if l.is_online)
        day_total = len(day_logs)
        day_anomalies = db.query(AnomalyRecord).filter(
            AnomalyRecord.record_date == d
        ).count()
        weekly_trend.append({
            "date": d.strftime("%m/%d"),
            "online_rate": round(day_online / day_total * 100, 1) if day_total else 0,
            "anomaly_count": day_anomalies,
        })

    # 高风险机构（按离线设备数）
    org_offline = {}
    for s in statuses:
        if not s.is_online:
            org = s.organization or '未分配机构'
            org_offline[org] = org_offline.get(org, 0) + 1
    top_risk = sorted(org_offline.items(), key=lambda x: -x[1])[:10]
    top_risk_institutions = [{"name": k, "offline_count": v} for k, v in top_risk]

    # 异常类型分布
    anomaly_types = db.query(
        AnomalyRecord.anomaly_type,
        func.count(AnomalyRecord.id)
    ).filter(
        AnomalyRecord.record_date >= today - timedelta(days=7)
    ).group_by(AnomalyRecord.anomaly_type).all()
    anomaly_trend = [{"type": t, "count": c} for t, c in anomaly_types]

    # 健康度分布
    health_dist = {"A": 0, "B": 0, "C": 0, "D": 0}
    for h in health_scores:
        health_dist[h["grade"]] = health_dist.get(h["grade"], 0) + 1

    return {
        "total_devices": len(devices),
        "total_institutions": len(institutions),
        "overall_online_rate": online_rate,
        "overall_health_score": avg_health,
        "pending_tickets": pending_tickets,
        "pending_incidents": pending_incidents,
        "weekly_trend": weekly_trend,
        "top_risk_institutions": top_risk_institutions,
        "anomaly_trend": anomaly_trend,
        "health_distribution": health_dist,
    }
