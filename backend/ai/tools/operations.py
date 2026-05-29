"""运营查询工具: 查询设备在线状态、异常工单、日报等"""
from functools import partial
from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.tools import StructuredTool


class NoInput(BaseModel):
    pass


class DeviceIdInput(BaseModel):
    device_id: str = Field(..., description="设备号，如 CAA241100006")


class OrgInput(BaseModel):
    organization: Optional[str] = Field(None, description="机构名称，如 紫竹院")


class DateInput(BaseModel):
    date: Optional[str] = Field(None, description="日期，格式 YYYY-MM-DD，默认今天")


def _query_device_status(db, organization: str = None):
    from crud import get_latest_device_status, get_monitored_devices

    devices = get_monitored_devices(db)
    device_ids = [d.device_id for d in devices]
    if not device_ids:
        return {"success": True, "message": "没有需要监控的设备", "devices": []}

    statuses = get_latest_device_status(db, device_ids=device_ids, organization=organization)

    result = []
    for s in statuses:
        result.append({
            "device_id": s.device_id,
            "organization": s.organization,
            "is_online": s.is_online,
            "firmware_version": s.firmware_version,
            "needs_firmware_update": s.needs_firmware_update,
            "offline_minutes": s.offline_duration_minutes or 0,
        })

    online = sum(1 for d in result if d["is_online"])
    return {
        "success": True,
        "total": len(result),
        "online": online,
        "offline": len(result) - online,
        "online_rate": f"{round(online / len(result) * 100, 1)}%" if result else "0%",
        "devices": result,
    }


def _query_offline_devices(db):
    from crud import get_latest_device_status, get_monitored_devices

    devices = get_monitored_devices(db)
    device_ids = [d.device_id for d in devices]
    if not device_ids:
        return {"success": True, "offline_devices": []}

    statuses = get_latest_device_status(db, device_ids=device_ids)
    offline = []
    for s in statuses:
        if not s.is_online:
            offline.append({
                "device_id": s.device_id,
                "organization": s.organization,
                "offline_minutes": s.offline_duration_minutes or 0,
                "firmware_version": s.firmware_version,
            })

    return {"success": True, "total_offline": len(offline), "offline_devices": offline}


def _query_anomaly_tickets(db, status: str = None, record_date: str = None):
    from crud import get_anomaly_records

    result = get_anomaly_records(db, status=status, record_date=record_date, limit=100)
    tickets = []
    for item in result["items"]:
        tickets.append({
            "id": item.id,
            "institution": item.institution,
            "person_name": item.person_name,
            "device_id": item.device_id,
            "anomaly_type": item.anomaly_type,
            "anomaly_detail": item.anomaly_detail,
            "status": item.status,
            "priority": item.priority,
            "algorithm_tag": item.algorithm_tag,
        })

    return {
        "success": True,
        "total": result["total"],
        "tickets": tickets,
    }


def _query_daily_report(db, date: str = None):
    from datetime import date as date_type, datetime
    from crud import get_daily_report

    if date:
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        report_date = date_type.today()

    report = get_daily_report(db, report_date)
    if not report:
        return {"success": True, "has_report": False, "message": f"{report_date} 暂无日报数据"}

    return {
        "success": True,
        "has_report": True,
        "date": str(report.report_date),
        "device_online_rate": f"{report.device_online_rate}%",
        "total_monitored_devices": report.total_monitored_devices,
        "offline_count": report.offline_count,
        "new_anomalies": report.new_anomalies,
        "new_offline_incidents": report.new_offline_incidents,
        "resolved_count": report.resolved_count,
        "summary_text": report.summary_text,
    }


def make_operations_tools(db):
    return [
        StructuredTool.from_function(
            func=partial(_query_device_status, db),
            name="query_device_status",
            description="查询设备在线状态。可按机构筛选。返回在线率、各设备在线/离线状态、固件版本。用户问'设备在线情况/在线率/XX机构的设备状态'时使用。",
            args_schema=OrgInput,
        ),
        StructuredTool.from_function(
            func=partial(_query_offline_devices, db),
            name="query_offline_devices",
            description="查询当前所有离线设备的列表，包括离线时长和固件版本。用户问'哪些设备离线/离线列表'时使用。",
            args_schema=NoInput,
        ),
        StructuredTool.from_function(
            func=partial(_query_anomaly_tickets, db),
            name="query_anomaly_tickets",
            description="查询异常工单列表。可按状态(待处理/处理中/待回访/已完成/已归档)和日期筛选。用户问'有哪些异常/待处理工单/需要回访的'时使用。",
            args_schema=DateInput,
        ),
        StructuredTool.from_function(
            func=partial(_query_daily_report, db),
            name="query_daily_report",
            description="查询指定日期的运营日报，包含设备在线率、新增异常数、已处理数等。用户问'今天的运营报告/日报/昨天运营情况'时使用。",
            args_schema=DateInput,
        ),
    ]
