"""出库预约工具: 查询预约列表"""
from functools import partial
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool


class QueryReservationsInput(BaseModel):
    status: Optional[str] = Field(None, description="预约状态: pending/approved/fulfilled/rejected, 不传=全部")
    applicant: Optional[str] = Field(None, description="申请人用户名筛选")


def _query_reservations(db, status=None, applicant=None):
    from models import Reservation
    query = db.query(Reservation)
    if status:
        query = query.filter(Reservation.status == status)
    if applicant:
        query = query.filter(Reservation.applicant == applicant)
    items = query.order_by(Reservation.created_at.desc()).limit(50).all()
    results = [{
        "id": r.id, "applicant": r.applicant, "quantity": r.quantity,
        "version_req": r.version_req or "不限", "packaging_req": r.packaging_req or "不限",
        "client_name": r.client_name or "-", "sales_person": r.sales_person or "-",
        "required_date": str(r.required_date) if r.required_date else "-",
        "purpose": r.purpose or "", "status": r.status,
        "assigned_devices": r.assigned_devices or "[]",
        "admin_remarks": r.admin_remarks or ""
    } for r in items]
    return {"success": True, "total": len(results), "items": results}


def make_reservation_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_query_reservations, db),
            name="query_reservations",
            description="查询出库预约列表。用户问'有什么预约/待审批预约/我的预约申请'时使用。可按状态和申请人筛选。",
            args_schema=QueryReservationsInput,
        ),
    ]
