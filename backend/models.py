from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey
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
    ORGANIZATION_SALE = "组织售卖"
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
