from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


# ========== Inventory Schemas ==========

class InventoryBase(BaseModel):
    serial_number: Optional[str] = None
    version: Optional[str] = None
    device_id: str = Field(..., min_length=12, max_length=12, description="设备号(3字母+9数字=12位)")
    type: Optional[str] = None
    packaging: Optional[str] = None
    device_attribute: Optional[str] = None
    owner: Optional[str] = None
    borrower: Optional[str] = None
    sales_person: Optional[str] = None
    iot_card_status: Optional[str] = None
    remarks: Optional[str] = None
    supplementary_info: Optional[str] = None
    delivery_date: Optional[date] = None


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    version: Optional[str] = None
    type: Optional[str] = None
    packaging: Optional[str] = None
    device_attribute: Optional[str] = None
    owner: Optional[str] = None
    borrower: Optional[str] = None
    sales_person: Optional[str] = None
    iot_card_status: Optional[str] = None
    remarks: Optional[str] = None
    supplementary_info: Optional[str] = None
    delivery_date: Optional[date] = None


class InventoryResponse(InventoryBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IoTCardUpdate(BaseModel):
    device_id: str
    iot_card_status: str


class BatchIoTCardUpdate(BaseModel):
    device_ids: List[str]
    iot_card_status: str


class BatchInventoryUpdate(BaseModel):
    device_ids: List[str]
    version: Optional[str] = None
    type: Optional[str] = None
    packaging: Optional[str] = None
    device_attribute: Optional[str] = None
    owner: Optional[str] = None
    borrower: Optional[str] = None
    sales_person: Optional[str] = None
    iot_card_status: Optional[str] = None
    remarks: Optional[str] = None
    supplementary_info: Optional[str] = None
    delivery_date: Optional[date] = None


# ========== Reminder Schemas ==========

class ReminderBase(BaseModel):
    device_id: Optional[str] = None
    reminder_type: Optional[str] = None
    due_date: Optional[date] = None
    description: Optional[str] = None


class ReminderCreate(ReminderBase):
    pass


class ReminderResponse(ReminderBase):
    id: int
    is_processed: Optional[bool] = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== AI Parser Schemas ==========

class AIParseRequest(BaseModel):
    user_input: str


class AIParseResponse(BaseModel):
    action: str
    details: dict = {}
    response_text: str = ""
    confirmation_needed: bool = False


# ========== Analysis Schemas ==========

class AnalysisQuery(BaseModel):
    query: str


class AnalysisResponse(BaseModel):
    success: bool
    query: str
    answer: str
    data: Optional[dict] = None


# ========== Dashboard Stats Schema ==========

class DashboardStats(BaseModel):
    total_devices: int
    available_devices: Optional[int] = 0
    sold_devices: Optional[int] = 0
    wifi_devices: int
    g4_devices: int
    sleep_devices: int
    fall_devices: int
    active_iot_cards: Optional[int] = 0
    unprocessed_reminders: int
    upcoming_trial_end: Optional[int] = 0
    overdue_borrows: Optional[int] = 0
    long_term_borrows: Optional[int] = 0


# ========== Borrow Record Schemas ==========

class BorrowRecordCreate(BaseModel):
    device_id: str
    borrower: str
    expected_return_date: Optional[date] = None
    purpose: Optional[str] = None
    condition_on_borrow: Optional[str] = None
    remarks: Optional[str] = None


class BorrowRecordReturn(BaseModel):
    actual_return_date: Optional[date] = None
    condition_on_return: Optional[str] = None
    remarks: Optional[str] = None


class BorrowRecordResponse(BaseModel):
    id: int
    device_id: str
    borrower: str
    borrow_date: Optional[datetime] = None
    expected_return_date: Optional[date] = None
    actual_return_date: Optional[date] = None
    purpose: Optional[str] = None
    status: str
    condition_on_borrow: Optional[str] = None
    condition_on_return: Optional[str] = None
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== Auth Schemas ==========

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    role: str = "operator"


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== Operation Log Schemas ==========

class OperationLogResponse(BaseModel):
    id: int
    username: Optional[str] = None
    operation_type: str
    device_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== Reservation Schemas ==========

class ReservationCreate(BaseModel):
    quantity: int = Field(..., ge=1, le=1000, description="需求数量(1-1000)")
    version_req: Optional[str] = None
    packaging_req: Optional[str] = None
    client_name: Optional[str] = None
    sales_person: Optional[str] = None
    required_date: Optional[date] = None
    purpose: Optional[str] = None


class ReservationApprove(BaseModel):
    assigned_devices: List[str]
    admin_remarks: Optional[str] = None


class ReservationReject(BaseModel):
    admin_remarks: Optional[str] = None


class ReservationResponse(BaseModel):
    id: int
    applicant: str
    quantity: int
    version_req: Optional[str] = None
    packaging_req: Optional[str] = None
    client_name: Optional[str] = None
    sales_person: Optional[str] = None
    required_date: Optional[date] = None
    purpose: Optional[str] = None
    status: str
    admin_username: Optional[str] = None
    assigned_devices: Optional[str] = None
    admin_remarks: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== Device Lifecycle Schemas ==========

class TimelineEvent(BaseModel):
    date: str
    event_type: str
    description: str
    operator: Optional[str] = None


class DeviceTimelineResponse(BaseModel):
    device_id: str
    events: List[TimelineEvent]


# ========== 运营平台 Schemas ==========

# --- Device Status ---

class DeviceStatusLogResponse(BaseModel):
    id: int
    device_id: str
    organization: Optional[str] = None
    check_time: Optional[datetime] = None
    is_online: Optional[bool] = True
    last_heartbeat: Optional[datetime] = None
    offline_duration_minutes: Optional[int] = 0
    firmware_version: Optional[str] = None
    needs_firmware_update: Optional[bool] = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Device Groups ---

class DeviceGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    device_ids: List[str] = []


class DeviceGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    device_ids: Optional[List[str]] = None


class DeviceGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    device_count: Optional[int] = 0
    device_ids: Optional[List[str]] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Offline Incidents ---

class OfflineIncidentHandle(BaseModel):
    reason_tag: str = Field(..., description="原因标签：用户断电/网络故障/设备故障/其他")
    notes: Optional[str] = None


class OfflineIncidentResponse(BaseModel):
    id: int
    device_id: str
    organization: Optional[str] = None
    detected_at: Optional[datetime] = None
    offline_duration: Optional[int] = 0
    firmware_version: Optional[str] = None
    status: Optional[str] = '待处理'
    reason_tag: Optional[str] = None
    handled_by: Optional[str] = None
    handled_at: Optional[datetime] = None
    notes: Optional[str] = None
    is_silenced: Optional[bool] = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Anomaly Records ---

class AnomalyRecordTag(BaseModel):
    algorithm_tag: str = Field(..., description="算法标记：需要回访/算法问题/真实案例")
    algorithm_notes: Optional[str] = None


class AnomalyRecordHandle(BaseModel):
    resolution: Optional[str] = None
    notes: Optional[str] = None


class AnomalyRecordResponse(BaseModel):
    id: int
    record_date: Optional[date] = None
    institution: Optional[str] = None
    room_info: Optional[str] = None
    device_id: Optional[str] = None
    person_name: Optional[str] = None
    anomaly_type: Optional[str] = None
    anomaly_detail: Optional[str] = None
    event_time: Optional[str] = None
    raw_data: Optional[dict] = None
    status: Optional[str] = '待处理'
    priority: Optional[str] = '中'
    algorithm_tag: Optional[str] = None
    algorithm_notes: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    prev_status: Optional[str] = None
    current_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Anomaly Actions ---

class AnomalyActionCreate(BaseModel):
    action_type: str
    content: Optional[str] = None


class AnomalyActionResponse(BaseModel):
    id: int
    record_id: int
    action_by: Optional[str] = None
    action_type: Optional[str] = None
    content: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Data Sync ---

class DataSyncLogResponse(BaseModel):
    id: int
    sync_date: Optional[date] = None
    sync_type: Optional[str] = 'auto'
    status: Optional[str] = 'running'
    stats: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Reports ---

class DailyReportResponse(BaseModel):
    id: int
    report_date: Optional[date] = None
    device_online_rate: Optional[float] = None
    total_monitored_devices: Optional[int] = 0
    offline_count: Optional[int] = 0
    new_anomalies: Optional[int] = 0
    new_offline_incidents: Optional[int] = 0
    resolved_count: Optional[int] = 0
    summary_text: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WeeklyReportResponse(BaseModel):
    id: int
    week_start: Optional[date] = None
    week_end: Optional[date] = None
    total_anomalies: Optional[int] = 0
    resolved_count: Optional[int] = 0
    resolution_rate: Optional[float] = None
    top_institutions: Optional[dict] = None
    top_devices: Optional[dict] = None
    report_data: Optional[dict] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Firmware Config ---

class FirmwareConfigUpdate(BaseModel):
    current_normal_version: str


class FirmwareConfigResponse(BaseModel):
    id: int
    current_normal_version: str
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Organization Daily Row (机构日报行) ---

class OrganizationDailyRow(BaseModel):
    organization: str
    total_devices: int
    online_count: int
    offline_count: int
    online_rate: float
    need_update_count: int
    offline_devices: List[dict] = []  # [{device_id, offline_duration_hours}]


class DeviceStatusPageResponse(BaseModel):
    check_time: Optional[str] = None
    total_online_rate: Optional[float] = None
    organizations: List[OrganizationDailyRow] = []


# ========== 企业级扩展 Schemas ==========

# --- Device Tags ---

class DeviceTagCreate(BaseModel):
    device_ids: List[str]
    tag_key: str
    tag_value: str


class DeviceTagDelete(BaseModel):
    device_id: str
    tag_key: str


class DeviceTagResponse(BaseModel):
    id: int
    device_id: str
    tag_key: str
    tag_value: str
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


# --- Smart Group Rules ---

class FilterCondition(BaseModel):
    field: str = Field(..., description="筛选字段: device_attribute, version, type, owner, firmware_version, is_online, tags.xxx")
    operator: str = Field(..., description="操作符: eq/neq/contains/in/gt/lt/gte/lte")
    value: str


class SmartGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    conditions: dict = Field(..., description='条件JSON: {"logic":"AND/OR","filters":[{field,operator,value},...]}')


class SmartGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[dict] = None
    enabled: Optional[bool] = None


class SmartGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    rule_type: Optional[str] = 'smart'
    conditions: Optional[dict] = None
    enabled: Optional[bool] = True
    matched_device_count: Optional[int] = 0
    matched_devices: Optional[List[str]] = []
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Device Health Score ---

class HealthScoreResponse(BaseModel):
    device_id: str
    score: int
    grade: str  # A(90+)/B(70+)/C(50+)/D(<50)
    online_score: int
    firmware_score: int
    anomaly_score: int
    offline_history_score: int
    details: Optional[dict] = None
    calculated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrgHealthSummary(BaseModel):
    organization: str
    avg_score: float
    grade_a_count: int
    grade_b_count: int
    grade_c_count: int
    grade_d_count: int
    total_devices: int


# --- Institution Region ---

class InstitutionRegionCreate(BaseModel):
    institution_name: str
    region: Optional[str] = None
    city: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None


class InstitutionRegionUpdate(BaseModel):
    region: Optional[str] = None
    city: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None


class InstitutionRegionResponse(BaseModel):
    id: int
    institution_name: str
    region: Optional[str] = None
    city: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# --- Batch Operations ---

class BatchOperationRequest(BaseModel):
    operation_type: str = Field(..., description="操作类型: tag_firmware/mark_offline/export/update_tags")
    target_type: str = Field(..., description="目标类型: group/organization/tag/selection")
    target_id: str = Field(..., description="目标标识")
    params: Optional[dict] = None


class BatchOperationResponse(BaseModel):
    id: int
    operation_type: str
    target_type: str
    target_id: Optional[str] = None
    affected_count: Optional[int] = 0
    success_count: Optional[int] = 0
    failed_count: Optional[int] = 0
    status: Optional[str] = 'running'
    operated_by: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Command Center Dashboard ---

class CommandCenterOverview(BaseModel):
    total_devices: int = 0
    total_institutions: int = 0
    overall_online_rate: float = 0.0
    overall_health_score: float = 0.0
    pending_tickets: int = 0
    pending_incidents: int = 0
    weekly_trend: List[dict] = []  # [{date, online_rate, anomaly_count}]
    top_risk_institutions: List[dict] = []  # [{name, risk_score, offline_count}]
    anomaly_trend: List[dict] = []  # [{type, count}]
    health_distribution: dict = {}  # {A: n, B: n, C: n, D: n}
