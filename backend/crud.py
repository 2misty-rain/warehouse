from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models import Inventory, Reminders, AILogs, BorrowRecord, OperationLog, User, ConversationHistory, Reservation
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
