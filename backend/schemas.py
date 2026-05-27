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
