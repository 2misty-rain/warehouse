from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
from enum import Enum as PyEnum


class DeviceAttribute(str, PyEnum):
    PRODUCT_DEMO = "产品演示"
    TECH_DEV_TEST = "技术开发/测试"
    INTERNAL_TRIAL = "内部试用"
    BUSINESS_OPPORTUNITY = "商机试用"
    SPECIAL_OCCUPATION = "特殊占用"
    EXISTING_STOCK = "现有库存"
    ORGANIZATION_SALE = "商机交付"
    EXCEPTION_HANDLING = "异常处理"


class IoTCardStatus(str, PyEnum):
    ACTIVE = "开卡"
    INACTIVE = "关卡"


class UserRole(str, PyEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class ReservationStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    FULFILLED = "fulfilled"
    REJECTED = "rejected"


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    serial_number = Column(String(50), unique=True, nullable=False, comment='序号')
    version = Column(String(50), comment='版本')
    device_id = Column(String(50), unique=True, nullable=False, comment='设备号')
    type = Column(String(100), comment='类型')
    packaging = Column(String(100), comment='产品包装')
    device_attribute = Column(String(100), comment='设备属性')
    owner = Column(String(100), comment='归属人/责任人/甲方')
    borrower = Column(String(100), comment='领用人')
    sales_person = Column(String(100), comment='销售')
    iot_card_status = Column(String(20), comment='物联网卡状态：开卡/关卡（4G设备专用）')
    remarks = Column(Text, comment='备注')
    supplementary_info = Column(Text, comment='补充信息记录')
    delivery_date = Column(Date, comment='交付/安装时间')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class Reminders(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(50), nullable=True, comment='设备号(可选)')
    reminder_type = Column(String(50), comment='提醒类型')
    due_date = Column(Date, comment='到期日期')
    description = Column(Text, comment='描述')
    is_processed = Column(Boolean, default=False, comment='是否已处理')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


class AILogs(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_input = Column(Text, nullable=False, comment='用户输入')
    ai_parsed_action = Column(String(200), comment='AI解析的操作')
    affected_records = Column(Text, comment='受影响的记录')
    operation_result = Column(Text, comment='操作结果')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


class BorrowRecord(Base):
    """设备借用记录表"""
    __tablename__ = "borrow_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(50), ForeignKey('inventory.device_id'), nullable=False, comment='设备号')
    borrower = Column(String(100), nullable=False, comment='借用人')
    borrow_date = Column(DateTime, server_default=func.now(), comment='借用时间')
    expected_return_date = Column(Date, comment='预计归还时间')
    actual_return_date = Column(Date, comment='实际归还时间')
    purpose = Column(Text, comment='借用目的')
    status = Column(String(20), default='borrowed', comment='状态：borrowed-借出中，returned-已归还，overdue-逾期')
    condition_on_borrow = Column(Text, comment='借出时设备状态')
    condition_on_return = Column(Text, comment='归还时设备状态')
    remarks = Column(Text, comment='备注')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class OperationLog(Base):
    """操作审计日志表"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), comment='操作人')
    operation_type = Column(String(50), nullable=False, comment='操作类型：create/update/delete/borrow/return/sell/import')
    device_id = Column(String(50), comment='目标设备号')
    details = Column(Text, comment='操作详情(JSON)')
    ip_address = Column(String(50), comment='操作IP')
    created_at = Column(DateTime, server_default=func.now(), comment='操作时间')


class User(Base):
    """系统用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment='用户名')
    email = Column(String(100), comment='邮箱')
    hashed_password = Column(String(255), nullable=False, comment='密码哈希')
    role = Column(String(20), default='operator', comment='角色：admin/operator/viewer')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class ConversationHistory(Base):
    """AI对话历史持久化表"""
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, comment='用户标识')
    role = Column(String(20), nullable=False, comment='角色：user/assistant/system')
    content = Column(Text, nullable=False, comment='对话内容')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


class Reservation(Base):
    """出库预约申请表"""
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    applicant = Column(String(50), nullable=False, comment='申请人用户名')
    quantity = Column(Integer, nullable=False, comment='需求设备数量')
    version_req = Column(String(20), comment='版本要求：WiFi/4G/不限')
    packaging_req = Column(String(20), comment='包装要求：简约/精品/不限')
    client_name = Column(String(100), comment='甲方/归属人')
    sales_person = Column(String(100), comment='销售')
    required_date = Column(Date, comment='需求日期')
    purpose = Column(Text, comment='用途说明')
    status = Column(String(20), default='pending', comment='状态：pending/approved/fulfilled/rejected')
    admin_username = Column(String(50), comment='处理人用户名')
    assigned_devices = Column(Text, comment='分配的设备号JSON数组')
    admin_remarks = Column(Text, comment='管理员备注')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')


# ========== 运营平台模型 ==========

class DeviceStatusLog(Base):
    """设备状态检查历史"""
    __tablename__ = "device_status_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(50), nullable=False, comment='设备号')
    organization = Column(String(100), comment='归属机构')
    check_time = Column(DateTime, nullable=False, comment='检查时间')
    is_online = Column(Boolean, default=True, comment='是否在线')
    last_heartbeat = Column(DateTime, comment='最后心跳时间')
    offline_duration_minutes = Column(Integer, default=0, comment='离线时长(分钟)')
    firmware_version = Column(String(50), comment='固件版本')
    needs_firmware_update = Column(Boolean, default=False, comment='是否需要固件更新')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


class DeviceGroup(Base):
    """用户自定义设备分组"""
    __tablename__ = "device_groups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment='分组名称')
    description = Column(Text, comment='分组描述')
    created_by = Column(String(50), comment='创建人')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


class DeviceGroupItem(Base):
    """分组中的设备"""
    __tablename__ = "device_group_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('device_groups.id', ondelete='CASCADE'), nullable=False, comment='分组ID')
    device_id = Column(String(50), nullable=False, comment='设备号')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


class OfflineIncident(Base):
    """离线事件"""
    __tablename__ = "offline_incidents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(50), nullable=False, comment='设备号')
    organization = Column(String(100), comment='归属机构')
    detected_at = Column(DateTime, nullable=False, comment='检测到离线的时间')
    offline_duration = Column(Integer, default=0, comment='离线时长(分钟)')
    firmware_version = Column(String(50), comment='固件版本')
    status = Column(String(20), default='待处理', comment='状态：待处理/已处理/已关闭')
    reason_tag = Column(String(50), comment='原因标签：用户断电/网络故障/设备故障/其他')
    handled_by = Column(String(50), comment='处理人')
    handled_at = Column(DateTime, comment='处理时间')
    notes = Column(Text, comment='处理备注')
    is_silenced = Column(Boolean, default=False, comment='是否静默(静默后不再生成新事件)')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class AnomalyRecord(Base):
    """异常记录工单"""
    __tablename__ = "anomaly_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_date = Column(Date, nullable=False, comment='异常发生日期')
    institution = Column(String(100), comment='机构名称')
    room_info = Column(String(100), comment='房间号')
    device_id = Column(String(50), comment='设备号')
    person_name = Column(String(50), comment='老人姓名')
    anomaly_type = Column(String(50), nullable=False, comment='异常类型：睡眠状态异常/睡眠过少/多次离床/体征异常')
    anomaly_detail = Column(Text, comment='异常详情描述')
    event_time = Column(String(100), comment='事件发生时间描述')
    raw_data = Column(JSON, comment='原始数据快照')
    status = Column(String(20), default='待处理', comment='状态：待处理/处理中/待回访/已完成/已归档')
    priority = Column(String(10), default='中', comment='优先级：高/中/低')
    algorithm_tag = Column(String(50), comment='算法标记：需要回访/算法问题/真实案例')
    algorithm_notes = Column(Text, comment='算法备注')
    assigned_to = Column(String(50), comment='处理人')
    resolution = Column(Text, comment='处理结果描述')
    resolved_at = Column(DateTime, comment='完成时间')
    prev_status = Column(String(50), comment='前一天用户设备状态')
    current_status = Column(String(50), comment='当天用户设备状态')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class AnomalyAction(Base):
    """工单操作日志（时间线）"""
    __tablename__ = "anomaly_actions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey('anomaly_records.id', ondelete='CASCADE'), nullable=False, comment='关联工单ID')
    action_by = Column(String(50), comment='操作人')
    action_type = Column(String(50), comment='操作类型：标记/回访/处理/完成/备注')
    content = Column(Text, comment='操作内容')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


class DataSyncLog(Base):
    """数据同步日志"""
    __tablename__ = "data_sync_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sync_date = Column(Date, nullable=False, comment='同步日期')
    sync_type = Column(String(20), default='auto', comment='同步类型：auto/manual')
    status = Column(String(20), default='running', comment='状态：running/success/failed')
    stats = Column(JSON, comment='统计信息')
    error_message = Column(Text, comment='错误信息')
    started_at = Column(DateTime, comment='开始时间')
    finished_at = Column(DateTime, comment='完成时间')


class DailyReport(Base):
    """每日运营日报"""
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_date = Column(Date, nullable=False, comment='报告日期')
    device_online_rate = Column(Float, comment='整体在线率')
    total_monitored_devices = Column(Integer, default=0, comment='监控设备总数')
    offline_count = Column(Integer, default=0, comment='离线设备数')
    new_anomalies = Column(Integer, default=0, comment='新增异常数')
    new_offline_incidents = Column(Integer, default=0, comment='新增离线事件数')
    resolved_count = Column(Integer, default=0, comment='已处理数量')
    summary_text = Column(Text, comment='文字摘要')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


class WeeklyReport(Base):
    """周报"""
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    week_start = Column(Date, nullable=False, comment='周开始日期')
    week_end = Column(Date, nullable=False, comment='周结束日期')
    total_anomalies = Column(Integer, default=0, comment='异常总数')
    resolved_count = Column(Integer, default=0, comment='已处理数')
    resolution_rate = Column(Float, comment='处理率')
    top_institutions = Column(JSON, comment='TOP机构')
    top_devices = Column(JSON, comment='高频异常设备')
    report_data = Column(JSON, comment='完整报告数据')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


class FirmwareConfig(Base):
    """固件版本标定"""
    __tablename__ = "firmware_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    current_normal_version = Column(String(50), nullable=False, comment='当前正常固件版本')
    updated_by = Column(String(50), comment='更新人')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class AnomalyIgnoreRule(Base):
    """异常忽略规则 — 标记为'不考虑'的设备+异常类型组合"""
    __tablename__ = "anomaly_ignore_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(50), nullable=False, comment='设备号')
    anomaly_type = Column(String(50), comment='异常类型(NULL表示全部类型)')
    reason = Column(Text, comment='忽略原因')
    created_by = Column(String(50), comment='操作人')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


# ========== 企业级运营平台扩展模型 ==========

class DeviceTag(Base):
    """设备自定义标签（支持多标签）"""
    __tablename__ = "device_tags"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(50), nullable=False, comment='设备号')
    tag_key = Column(String(50), nullable=False, comment='标签键（如 region, floor, product_line）')
    tag_value = Column(String(100), nullable=False, comment='标签值（如 华东区, 3楼, 睡眠设备）')
    created_by = Column(String(50), comment='创建人')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


class SmartGroupRule(Base):
    """智能分组规则"""
    __tablename__ = "smart_group_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment='规则名称')
    description = Column(Text, comment='规则描述')
    rule_type = Column(String(30), default='smart', comment='分组类型: smart(智能)/manual(手动)')
    conditions = Column(JSON, nullable=False, comment='筛选条件JSON，格式: {"logic":"AND","filters":[...]}')
    enabled = Column(Boolean, default=True, comment='是否启用')
    created_by = Column(String(50), comment='创建人')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class DeviceHealthScore(Base):
    """设备健康度评分"""
    __tablename__ = "device_health_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(50), nullable=False, comment='设备号')
    score = Column(Integer, default=100, comment='健康度评分 0-100')
    grade = Column(String(5), default='A', comment='健康等级 A/B/C/D')
    online_score = Column(Integer, default=100, comment='在线率子分 (权重40%)')
    firmware_score = Column(Integer, default=100, comment='固件合规子分 (权重30%)')
    anomaly_score = Column(Integer, default=100, comment='异常频率子分 (权重20%)')
    offline_history_score = Column(Integer, default=100, comment='离线历史子分 (权重10%)')
    details = Column(JSON, comment='评分详情')
    calculated_at = Column(DateTime, comment='计算时间')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')


class InstitutionRegion(Base):
    """机构地域配置"""
    __tablename__ = "institution_regions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    institution_name = Column(String(100), nullable=False, unique=True, comment='机构名称')
    region = Column(String(50), comment='大区（如 华北/华东/华南/西南）')
    city = Column(String(50), comment='城市')
    contact_person = Column(String(50), comment='机构联系人')
    contact_phone = Column(String(20), comment='联系电话')
    notes = Column(Text, comment='备注')
    updated_by = Column(String(50), comment='更新人')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')


class BatchOperation(Base):
    """批量操作记录"""
    __tablename__ = "batch_operations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    operation_type = Column(String(50), nullable=False, comment='操作类型: tag_firmware/mark_offline/export/update_tags')
    target_type = Column(String(20), nullable=False, comment='目标类型: group/organization/tag/selection')
    target_id = Column(String(100), comment='目标标识（分组ID/机构名/标签/设备号列表JSON）')
    params = Column(JSON, comment='操作参数')
    affected_count = Column(Integer, default=0, comment='影响设备数')
    success_count = Column(Integer, default=0, comment='成功数')
    failed_count = Column(Integer, default=0, comment='失败数')
    status = Column(String(20), default='running', comment='状态: running/success/failed/partial')
    operated_by = Column(String(50), comment='操作人')
    started_at = Column(DateTime, comment='开始时间')
    finished_at = Column(DateTime, comment='完成时间')
    created_at = Column(DateTime, server_default=func.now(), comment='创建时间')
