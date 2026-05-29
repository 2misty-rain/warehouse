"""
运营平台路由
包含：设备监控、异常工单、数据报告、固件版本管理、数据同步
"""

import os
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from database import get_db
from auth import get_current_user
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operations", tags=["Operations"])

# 数据存储根目录（复用 daily_ops 的数据目录）
_WAREHOUSE_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = str(_WAREHOUSE_ROOT / "daily_ops_data")

# 全局缓存
_device_mapping_cache = {}
_room_info_cache = {}
_token = None


# ============== 请求模型 ==============

class DeviceGroupReq(BaseModel):
    name: str
    description: Optional[str] = None
    device_ids: List[str] = []


class DeviceGroupUpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    device_ids: Optional[List[str]] = None


class OfflineHandleReq(BaseModel):
    reason_tag: str
    notes: Optional[str] = None


class AnomalyTagReq(BaseModel):
    algorithm_tag: str
    algorithm_notes: Optional[str] = None


class AnomalyHandleReq(BaseModel):
    resolution: Optional[str] = None
    notes: Optional[str] = None


class AnomalyNoteReq(BaseModel):
    content: str


class FirmwareSetReq(BaseModel):
    current_normal_version: str


class SyncReq(BaseModel):
    date: Optional[str] = None


class DateReq(BaseModel):
    date: Optional[str] = None


# ============== 辅助函数 ==============

def _get_token():
    global _token
    from daily_ops.downloader import login as do_login
    if _token is None:
        _token = do_login()
    return _token


def _get_device_mapping(force_refresh: bool = False):
    global _device_mapping_cache
    from daily_ops.api_client import load_device_mapping
    token = _get_token()
    if token:
        cache_dir = str(Path(__file__).resolve().parent.parent / "daily_ops" / "cache")
        _device_mapping_cache = load_device_mapping(token, cache_dir, force_refresh)
    return _device_mapping_cache


def _get_default_date():
    return datetime.now().strftime("%Y-%m-%d")


# ==========================================
# 一、设备监控
# ==========================================

@router.get("/device-status/overview")
def device_status_overview(
    attr: Optional[str] = Query(None, description="过滤设备属性，逗号分隔，默认商机交付,商机试用"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """获取设备状态总览：按机构分组展示在线/离线/固件情况"""
    from crud import get_monitored_devices, get_organization_device_summary, get_latest_device_status, get_firmware_config

    attributes = attr.split(",") if attr else ['商机交付', '商机试用']
    org_summary = get_organization_device_summary(db, attributes)

    if not org_summary:
        return {"success": True, "check_time": None, "total_online_rate": None, "organizations": []}

    all_device_ids = []
    for org in org_summary:
        all_device_ids.extend(org["device_ids"])

    statuses = get_latest_device_status(db, device_ids=all_device_ids) if all_device_ids else []
    status_map = {}
    for s in statuses:
        status_map[s.device_id] = s

    firmware_config = get_firmware_config(db)

    organizations = []
    total_online = 0
    total_devices = 0
    check_time = None

    for org in org_summary:
        online_count = 0
        need_update_count = 0
        offline_list = []

        for did in org["device_ids"]:
            s = status_map.get(did)
            if s:
                if check_time is None:
                    check_time = s.check_time.strftime("%Y-%m-%d %H:%M") if s.check_time else None
                if s.is_online:
                    online_count += 1
                else:
                    offline_list.append({
                        "device_id": did,
                        "offline_duration_hours": round((s.offline_duration_minutes or 0) / 60, 1),
                        "firmware_version": s.firmware_version,
                    })
                if s.needs_firmware_update:
                    need_update_count += 1
            else:
                # 没有状态记录，视为未知
                pass

        total_online += online_count
        total_devices += org["total"]
        online_rate = round(online_count / org["total"] * 100, 1) if org["total"] > 0 else 0

        organizations.append({
            "organization": org["organization"],
            "total_devices": org["total"],
            "online_count": online_count,
            "offline_count": org["total"] - online_count,
            "online_rate": online_rate,
            "need_update_count": need_update_count,
            "offline_devices": offline_list,
        })

    total_online_rate = round(total_online / total_devices * 100, 1) if total_devices > 0 else 0

    return {
        "success": True,
        "check_time": check_time,
        "total_online_rate": total_online_rate,
        "organizations": organizations,
    }


@router.get("/device-status/detail")
def device_status_detail(
    organization: Optional[str] = None,
    device_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """获取设备详细状态列表"""
    from crud import get_latest_device_status, get_device_status_history, get_monitored_devices

    devices = get_monitored_devices(db)
    device_ids = [d.device_id for d in devices]
    if device_id:
        device_ids = [device_id]

    statuses = get_latest_device_status(db, device_ids=device_ids, organization=organization)
    status_list = []
    for s in statuses:
        status_list.append({
            "device_id": s.device_id,
            "organization": s.organization,
            "check_time": s.check_time.strftime("%Y-%m-%d %H:%M") if s.check_time else None,
            "is_online": s.is_online,
            "last_heartbeat": s.last_heartbeat.strftime("%Y-%m-%d %H:%M") if s.last_heartbeat else None,
            "offline_duration_minutes": s.offline_duration_minutes,
            "firmware_version": s.firmware_version,
            "needs_firmware_update": s.needs_firmware_update,
        })

    return {"success": True, "devices": status_list}


@router.get("/device-status/history")
def device_status_history(
    device_id: str,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """获取设备状态历史"""
    from crud import get_device_status_history
    logs = get_device_status_history(db, device_id, days)
    history = []
    for log in logs:
        history.append({
            "check_time": log.check_time.strftime("%Y-%m-%d %H:%M") if log.check_time else None,
            "is_online": log.is_online,
            "firmware_version": log.firmware_version,
            "offline_duration_minutes": log.offline_duration_minutes,
        })
    return {"success": True, "device_id": device_id, "history": history}


@router.post("/device-status/refresh")
def device_status_refresh(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """手动刷新设备状态（从生产库同步）"""
    from crud import get_monitored_devices, save_device_status_logs
    from crud import create_offline_incident, auto_close_offline_incident, get_firmware_config
    from crud import get_latest_device_status as get_latest

    devices = get_monitored_devices(db)
    if not devices:
        return {"success": True, "message": "没有需要监控的设备", "synced": 0}

    # 尝试从生产库同步
    db_config = _get_production_db_config()
    if not db_config:
        return {"success": False, "detail": "尚未配置生产数据库连接信息"}

    fw_config = get_firmware_config(db)
    normal_version = fw_config.current_normal_version if fw_config else None

    check_time = datetime.utcnow()
    logs = []
    synced = 0

    for device in devices:
        did = device.device_id
        org = device.owner or '未分配机构'

        prod_data = _query_device_from_production(db_config, did)

        is_online = False
        last_heartbeat = None
        firmware_version = None

        if prod_data:
            # 直接使用生产库的status字段判断在线状态
            is_online = prod_data.get('is_online', False)
            firmware_version = prod_data.get('firmware_version')

            # 心跳时间：在线设备用last_online_time，离线设备用last_offline_time计算离线时长
            if is_online:
                last_heartbeat = prod_data.get('last_heartbeat')
            else:
                # 对于离线设备，用最后一次在线时间来计算离线时长
                last_heartbeat = prod_data.get('last_heartbeat')

        offline_duration = 0
        if not is_online and last_heartbeat:
            offline_duration = int((check_time - last_heartbeat).total_seconds() / 60)
        elif is_online and last_heartbeat:
            # 在线设备检查心跳新鲜度
            delta = (check_time - last_heartbeat).total_seconds() / 60
            if delta > 30:
                # 心跳超过30分钟没更新，标记为离线
                is_online = False
                offline_duration = int(delta)

        needs_update = False
        if normal_version and firmware_version:
            # firmware_version可能是字符串或整数（版本代号）
            fw_str = str(firmware_version) if firmware_version else ''
            needs_update = _version_less_than(fw_str, normal_version)

        logs.append({
            "device_id": did,
            "organization": org,
            "check_time": check_time,
            "is_online": is_online,
            "last_heartbeat": last_heartbeat,
            "offline_duration_minutes": offline_duration,
            "firmware_version": firmware_version,
            "needs_firmware_update": needs_update,
        })
        synced += 1

    if logs:
        save_device_status_logs(db, logs)

    # 处理离线事件
    latest_statuses = get_latest(db, device_ids=[d.device_id for d in devices])
    status_map = {s.device_id: s for s in latest_statuses}

    for dev in devices:
        s = status_map.get(dev.device_id)
        if s and not s.is_online:
            create_offline_incident(
                db, dev.device_id, dev.owner or '未分配机构',
                s.offline_duration_minutes or 0, s.firmware_version
            )
        elif s and s.is_online:
            auto_close_offline_incident(db, dev.device_id)

    return {"success": True, "synced": synced, "check_time": check_time.strftime("%Y-%m-%d %H:%M:%S")}


# ==========================================
# 二、设备分组管理
# ==========================================

@router.get("/device-groups")
def list_device_groups(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_device_groups
    return {"success": True, "groups": get_device_groups(db)}


@router.post("/device-groups")
def create_device_group(
    req: DeviceGroupReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import create_device_group as create_group
    group = create_group(db, req.name, req.device_ids, user.username, req.description)
    return {"success": True, "group": group}


@router.get("/device-groups/{group_id}")
def get_device_group(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_device_group_by_id
    group = get_device_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    return {"success": True, "group": group}


@router.put("/device-groups/{group_id}")
def update_device_group(
    group_id: int,
    req: DeviceGroupUpdateReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import update_device_group as update_group
    group = update_group(db, group_id, req.name, req.description, req.device_ids)
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    return {"success": True, "group": group}


@router.delete("/device-groups/{group_id}")
def delete_device_group(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import delete_device_group as del_group
    if not del_group(db, group_id):
        raise HTTPException(status_code=404, detail="分组不存在")
    return {"success": True}


# ==========================================
# 三、离线事件
# ==========================================

@router.get("/offline-incidents")
def list_offline_incidents(
    status: Optional[str] = None,
    organization: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_offline_incidents
    result = get_offline_incidents(db, status, organization, skip, limit)
    return {"success": True, **result}


@router.put("/offline-incidents/{incident_id}/handle")
def handle_offline_incident(
    incident_id: int,
    req: OfflineHandleReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import handle_offline_incident as handle
    incident = handle(db, incident_id, req.reason_tag, req.notes, user.username)
    if not incident:
        raise HTTPException(status_code=404, detail="事件不存在")
    return {"success": True, "incident": incident}


# ==========================================
# 四、异常工单
# ==========================================

@router.get("/anomaly-records")
def list_anomaly_records(
    status: Optional[str] = None,
    institution: Optional[str] = None,
    anomaly_type: Optional[str] = None,
    priority: Optional[str] = None,
    record_date: Optional[str] = None,
    algorithm_tag: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_anomaly_records
    result = get_anomaly_records(
        db, status, institution, anomaly_type, priority,
        record_date, algorithm_tag, search, skip, limit
    )
    return {"success": True, **result}


@router.get("/anomaly-records/stats")
def anomaly_stats(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_anomaly_stats
    return {"success": True, "stats": get_anomaly_stats(db)}


@router.put("/anomaly-records/{record_id}/tag")
def tag_anomaly_record(
    record_id: int,
    req: AnomalyTagReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """算法人员标记异常记录"""
    from crud import tag_anomaly_record as tag
    record = tag(db, record_id, req.algorithm_tag, req.algorithm_notes, user.username)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "record": record}


@router.put("/anomaly-records/{record_id}/handle")
def handle_anomaly_record(
    record_id: int,
    req: AnomalyHandleReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """处理异常工单（标记完成）"""
    from crud import handle_anomaly_record as handle
    record = handle(db, record_id, req.resolution or '', user.username, req.notes)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "record": record}


@router.post("/anomaly-records/{record_id}/notes")
def add_anomaly_note(
    record_id: int,
    req: AnomalyNoteReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import add_anomaly_note as add_note
    action = add_note(db, record_id, req.content, user.username)
    return {"success": True, "action": action}


@router.get("/anomaly-records/{record_id}/timeline")
def anomaly_timeline(
    record_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_anomaly_actions
    actions = get_anomaly_actions(db, record_id)
    return {"success": True, "record_id": record_id, "actions": actions}


# ==========================================
# 五、数据同步
# ==========================================

@router.post("/sync/anomaly-data")
def sync_anomaly_data(
    req: Optional[SyncReq] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """手动触发异常数据同步（下载+分析+入库）"""
    if req is None:
        req = SyncReq()
    target_date = req.date or _get_default_date()

    from crud import create_sync_log, update_sync_log, create_anomaly_records_batch

    log_entry = create_sync_log(db, datetime.strptime(target_date, "%Y-%m-%d").date(), 'manual')

    try:
        from daily_ops.downloader import download_reports, login as do_login
        from daily_ops.analyzer import analyze_today

        token = _get_token()
        if not token:
            token = do_login()
            if not token:
                raise Exception("登录远程报表系统失败")

        os.makedirs(DATA_DIR, exist_ok=True)
        dl_result = download_reports(target_date, DATA_DIR, token, include_previous=True)
        if not dl_result.get("success"):
            raise Exception(dl_result.get("error", "下载失败"))

        device_mapping = _get_device_mapping(force_refresh=True)
        analysis_result = analyze_today(target_date, DATA_DIR, token, device_mapping, _room_info_cache)

        if not analysis_result.get("success"):
            raise Exception(analysis_result.get("error", "分析失败"))

        # 将分析结果写入数据库
        summary_rows = analysis_result.get("summary_rows", [])
        stats = analysis_result.get("stats", {})

        anomaly_records = []
        for row in summary_rows:
            anomaly_type = row.get('问题分类', '')
            record = {
                "record_date": datetime.strptime(target_date, "%Y-%m-%d").date(),
                "institution": row.get('机构', ''),
                "device_id": str(row.get('设备号', '')),
                "person_name": row.get('姓名', ''),
                "anomaly_type": anomaly_type,
                "anomaly_detail": row.get('事件记录', ''),
                "event_time": row.get('事件发生时间', ''),
                "raw_data": row,
            }
            # 体征异常自动归档
            if anomaly_type == '体征异常':
                record["status"] = '已归档'
                record["priority"] = '低'
            # 睡眠状态异常优先级高
            elif anomaly_type == '睡眠状态异常':
                record["priority"] = '高'
            # 睡眠过少和多次离床优先级中
            else:
                record["priority"] = '中'
            anomaly_records.append(record)

        inserted = create_anomaly_records_batch(db, anomaly_records)

        update_sync_log(db, log_entry.id, 'success', {
            "valid_devices": stats.get("valid_devices", 0),
            "abnormal_devices": stats.get("abnormal_devices", 0),
            "total_summary": stats.get("total_summary", 0),
            "sleep_too_little": stats.get("sleep_too_little", 0),
            "multiple_bed_exit": stats.get("multiple_bed_exit", 0),
            "sleep_abnormal": stats.get("sleep_abnormal", 0),
            "vital_abnormal": stats.get("vital_abnormal", 0),
            "status_changes": stats.get("status_changes", 0),
            "inserted_records": inserted,
        })

        return {
            "success": True,
            "date": target_date,
            "stats": stats,
            "inserted_records": inserted,
        }

    except Exception as e:
        update_sync_log(db, log_entry.id, 'failed', error_message=str(e))
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/sync/logs")
def sync_logs(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_latest_sync_log
    log = get_latest_sync_log(db)
    return {"success": True, "latest": log}


@router.get("/sync/export-report")
def export_report(
    date: Optional[str] = None,
    user=Depends(get_current_user)
):
    """导出指定日期的异常报表（Excel下载链接）"""
    target_date = date or _get_default_date()
    excel_file = os.path.join(DATA_DIR, target_date, f"异常汇总_{target_date}.xlsx")
    if not os.path.exists(excel_file):
        txt_file = os.path.join(DATA_DIR, target_date, f"汇总报告_{target_date}.txt")
        if not os.path.exists(txt_file):
            raise HTTPException(status_code=404, detail=f"{target_date} 的报表数据不存在，请先执行数据同步")

    filename = f"异常汇总_{target_date}.xlsx"
    from fastapi.responses import FileResponse
    return FileResponse(
        path=excel_file,
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ==========================================
# 六、固件版本管理
# ==========================================

@router.get("/firmware-config")
def get_firmware_config_endpoint(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_firmware_config as get_fw
    config = get_fw(db)
    if not config:
        return {"success": True, "config": None}
    return {
        "success": True,
        "config": {
            "id": config.id,
            "current_normal_version": config.current_normal_version,
            "updated_by": config.updated_by,
            "updated_at": config.updated_at.strftime("%Y-%m-%d %H:%M") if config.updated_at else None,
        }
    }


@router.post("/firmware-config")
def set_firmware_config_endpoint(
    req: FirmwareSetReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import set_firmware_config
    config = set_firmware_config(db, req.current_normal_version, user.username)
    return {"success": True, "config": {
        "id": config.id,
        "current_normal_version": config.current_normal_version,
        "updated_by": config.updated_by,
        "updated_at": config.updated_at.strftime("%Y-%m-%d %H:%M") if config.updated_at else None,
    }}


# ==========================================
# 七、数据报告
# ==========================================

@router.get("/reports/daily")
def daily_report(
    date: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_daily_report
    target_date = date or _get_default_date()
    report = get_daily_report(db, datetime.strptime(target_date, "%Y-%m-%d").date())

    if not report:
        return {
            "success": True,
            "date": target_date,
            "has_report": False,
            "report": None,
        }

    return {
        "success": True,
        "date": target_date,
        "has_report": True,
        "report": {
            "id": report.id,
            "report_date": str(report.report_date),
            "device_online_rate": report.device_online_rate,
            "total_monitored_devices": report.total_monitored_devices,
            "offline_count": report.offline_count,
            "new_anomalies": report.new_anomalies,
            "new_offline_incidents": report.new_offline_incidents,
            "resolved_count": report.resolved_count,
            "summary_text": report.summary_text,
            "created_at": report.created_at.strftime("%Y-%m-%d %H:%M") if report.created_at else None,
        },
    }


@router.post("/reports/daily/generate")
def generate_daily_report(
    req: Optional[DateReq] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """生成指定日期的日报"""
    if req is None:
        req = DateReq()
    target_date = req.date or _get_default_date()
    report_date = datetime.strptime(target_date, "%Y-%m-%d").date()

    from crud import create_daily_report, get_latest_device_status, get_monitored_devices
    from crud import get_anomaly_records, get_offline_incidents

    devices = get_monitored_devices(db)
    device_ids = [d.device_id for d in devices]
    total_devices = len(device_ids)

    # 在线率
    statuses = get_latest_device_status(db, device_ids=device_ids) if device_ids else []
    online_count = sum(1 for s in statuses if s.is_online)
    online_rate = round(online_count / len(statuses) * 100, 1) if statuses else 0
    offline_count = len(statuses) - online_count

    # 异常工单统计
    anomaly_result = get_anomaly_records(db, record_date=target_date, limit=10000)
    new_anomalies = anomaly_result["total"]

    # 离线事件统计
    incident_result = get_offline_incidents(db, limit=10000)
    today_incidents = [
        i for i in incident_result["items"]
        if i.detected_at and i.detected_at.strftime("%Y-%m-%d") == target_date
    ]
    new_offline_incidents = len(today_incidents)

    # 已完成数
    resolved_result = get_anomaly_records(db, status='已完成', record_date=target_date, limit=10000)
    resolved_count = resolved_result["total"]

    summary_text = f"【{target_date}运营日报】\n"
    summary_text += f"监控设备{total_devices}台，在线{online_count}台，在线率{online_rate}%\n"
    summary_text += f"新增异常{new_anomalies}条，新增离线事件{new_offline_incidents}个，已处理{resolved_count}条"

    data = {
        "device_online_rate": online_rate,
        "total_monitored_devices": total_devices,
        "offline_count": offline_count,
        "new_anomalies": new_anomalies,
        "new_offline_incidents": new_offline_incidents,
        "resolved_count": resolved_count,
        "summary_text": summary_text,
    }

    report = create_daily_report(db, report_date, data)
    return {"success": True, "date": target_date, "report": data}


@router.get("/reports/weekly")
def weekly_report(
    week_start: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_weekly_report

    if week_start:
        ws = datetime.strptime(week_start, "%Y-%m-%d").date()
        we = ws + timedelta(days=6)
    else:
        today = date.today()
        ws = today - timedelta(days=today.weekday())
        we = ws + timedelta(days=6)

    report = get_weekly_report(db, ws, we)
    if not report:
        return {"success": True, "week_start": str(ws), "week_end": str(we), "has_report": False, "report": None}

    return {
        "success": True,
        "week_start": str(report.week_start),
        "week_end": str(report.week_end),
        "has_report": True,
        "report": {
            "id": report.id,
            "total_anomalies": report.total_anomalies,
            "resolved_count": report.resolved_count,
            "resolution_rate": report.resolution_rate,
            "top_institutions": report.top_institutions,
            "top_devices": report.top_devices,
            "report_data": report.report_data,
        },
    }


@router.post("/reports/weekly/generate")
def generate_weekly_report(
    week_start: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """生成周报"""
    if week_start:
        ws = datetime.strptime(week_start, "%Y-%m-%d").date()
    else:
        today = date.today()
        ws = today - timedelta(days=today.weekday())
    we = ws + timedelta(days=6)

    from crud import create_weekly_report, get_anomaly_records

    # 统计本周异常
    anomaly_result = get_anomaly_records(db, limit=10000)
    week_items = []
    for item in anomaly_result["items"]:
        if item.record_date and ws <= item.record_date <= we:
            week_items.append(item)

    total_anomalies = len(week_items)
    resolved = sum(1 for item in week_items if item.status in ('已完成', '已归档'))
    resolution_rate = round(resolved / total_anomalies * 100, 1) if total_anomalies > 0 else 0

    # TOP机构
    inst_counts = {}
    for item in week_items:
        inst = item.institution or '未知'
        inst_counts[inst] = inst_counts.get(inst, 0) + 1
    top_institutions = sorted(inst_counts.items(), key=lambda x: -x[1])[:10]

    # 高频设备
    dev_counts = {}
    for item in week_items:
        did = item.device_id or '未知'
        dev_counts[did] = dev_counts.get(did, 0) + 1
    top_devices = sorted(dev_counts.items(), key=lambda x: -x[1])[:10]

    report_data = {
        "total_anomalies": total_anomalies,
        "resolved_count": resolved,
        "resolution_rate": resolution_rate,
        "top_institutions": [{"name": k, "count": v} for k, v in top_institutions],
        "top_devices": [{"device_id": k, "count": v} for k, v in top_devices],
        "report_data": {
            "by_type": {},
            "by_institution": dict(top_institutions),
        },
    }

    report = create_weekly_report(db, ws, we, report_data)
    return {"success": True, "week_start": str(ws), "week_end": str(we), "report": report_data}


# ==========================================
# 生产数据库连接（占位 - 等用户提供连接信息）
# ==========================================

_production_db_config = None


def _get_production_db_config() -> dict:
    """获取生产数据库配置（从环境变量或配置文件读取）"""
    global _production_db_config
    if _production_db_config:
        return _production_db_config

    # 尝试从环境变量读取
    prod_url = os.environ.get("PRODUCTION_DATABASE_URL")
    if prod_url:
        _production_db_config = {"url": prod_url}
        return _production_db_config

    return None


def set_production_db_config(config: dict):
    """设置生产数据库配置"""
    global _production_db_config
    _production_db_config = config


class ProductionDBConfigReq(BaseModel):
    host: str
    port: int = 3306
    database: str
    username: str
    password: str
    device_table: str = "devices"
    device_id_column: str = "device_id"
    online_status_column: str = "online_status"
    last_heartbeat_column: str = "last_heartbeat"
    firmware_version_column: str = "firmware_version"


class ProductionDBTestReq(BaseModel):
    host: str
    port: int = 3306
    database: str
    username: str
    password: str


@router.post("/production-db/config")
def save_production_db_config(
    req: ProductionDBConfigReq,
    user=Depends(get_current_user)
):
    """保存生产数据库连接配置"""
    config = {
        "host": req.host, "port": req.port, "database": req.database,
        "username": req.username, "password": req.password,
        "device_table": req.device_table,
        "device_id_column": req.device_id_column,
        "online_status_column": req.online_status_column,
        "last_heartbeat_column": req.last_heartbeat_column,
        "firmware_version_column": req.firmware_version_column,
    }
    set_production_db_config(config)
    # 持久化到环境变量文件
    try:
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        url = f"mysql+pymysql://{req.username}:{req.password}@{req.host}:{req.port}/{req.database}"
        # 写入或更新 PRODUCTION_DATABASE_URL
        lines = []
        found = False
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
        with open(env_path, 'w') as f:
            for line in lines:
                if line.startswith('PRODUCTION_DATABASE_URL='):
                    f.write(f'PRODUCTION_DATABASE_URL={url}\n')
                    found = True
                elif line.startswith('PRODUCTION_DB_'):
                    continue  # 跳过旧的字段级配置
                else:
                    f.write(line)
            if not found:
                f.write(f'\nPRODUCTION_DATABASE_URL={url}\n')
            # 写入字段映射
            f.write(f'PRODUCTION_DB_TABLE={req.device_table}\n')
            f.write(f'PRODUCTION_DB_DEVICE_ID_COL={req.device_id_column}\n')
            f.write(f'PRODUCTION_DB_ONLINE_COL={req.online_status_column}\n')
            f.write(f'PRODUCTION_DB_HEARTBEAT_COL={req.last_heartbeat_column}\n')
            f.write(f'PRODUCTION_DB_FW_COL={req.firmware_version_column}\n')
        os.environ['PRODUCTION_DATABASE_URL'] = url
    except Exception as e:
        logger.warning(f"持久化生产数据库配置失败: {e}")
    return {"success": True, "message": "生产数据库配置已保存"}


@router.post("/production-db/test")
def test_production_db_connection(
    req: ProductionDBTestReq,
    user=Depends(get_current_user)
):
    """测试生产数据库连接"""
    import pymysql
    try:
        conn = pymysql.connect(
            host=req.host, port=req.port, database=req.database,
            user=req.username, password=req.password,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"success": True, "message": "连接成功"}
    except Exception as e:
        return {"success": False, "detail": f"连接失败: {str(e)}"}


@router.get("/production-db/config")
def get_production_db_config_endpoint(
    user=Depends(get_current_user)
):
    """获取当前生产数据库配置（隐藏密码）"""
    config = _get_production_db_config()
    if not config:
        # 尝试从环境变量重建
        url = os.environ.get('PRODUCTION_DATABASE_URL', '')
        if url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            config = {
                "host": parsed.hostname or '',
                "port": parsed.port or 3306,
                "database": (parsed.path or '/')[1:],
                "username": parsed.username or '',
                "password": '******',
                "device_table": os.environ.get('PRODUCTION_DB_TABLE', 'devices'),
                "device_id_column": os.environ.get('PRODUCTION_DB_DEVICE_ID_COL', 'device_id'),
                "online_status_column": os.environ.get('PRODUCTION_DB_ONLINE_COL', 'online_status'),
                "last_heartbeat_column": os.environ.get('PRODUCTION_DB_HEARTBEAT_COL', 'last_heartbeat'),
                "firmware_version_column": os.environ.get('PRODUCTION_DB_FW_COL', 'firmware_version'),
            }
            set_production_db_config(config)
            return {"success": True, "config": config}
        return {"success": True, "config": None}
    # 隐藏密码
    safe_config = {**config}
    if 'password' in safe_config:
        safe_config['password'] = '******'
    return {"success": True, "config": safe_config}


def _query_device_from_production(db_config: dict, device_id: str) -> dict:
    """从生产数据库查询设备在线状态和固件版本"""
    import pymysql
    try:
        conn = pymysql.connect(
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 3306),
            database=db_config.get('database', 'wechat_idc'),
            user=db_config.get('username', 'root'),
            password=db_config.get('password', '123456'),
            connect_timeout=5,
            charset='utf8mb4'
        )
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        table = db_config.get('device_table', 'operation_device')
        id_col = db_config.get('device_id_column', 'device_id')
        online_col = db_config.get('online_status_column', 'status')
        heartbeat_col = db_config.get('last_heartbeat_column', 'last_online_time')
        fw_col = db_config.get('firmware_version_column', 'version')

        cursor.execute(f"""
            SELECT {online_col} as online_status, {heartbeat_col} as last_heartbeat, {fw_col} as firmware_version
            FROM {table}
            WHERE {id_col} = %s
            LIMIT 1
        """, (device_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            result = {}
            status_val = row.get('online_status')
            if isinstance(status_val, int):
                result['is_online'] = status_val == 1
            else:
                result['is_online'] = status_val

            result['last_heartbeat'] = row.get('last_heartbeat')

            fw_val = row.get('firmware_version')
            if isinstance(fw_val, (int, float)):
                result['firmware_version'] = str(fw_val)
            else:
                result['firmware_version'] = fw_val

            # Convert datetime to Python datetime if needed
            if result.get('last_heartbeat') and hasattr(result['last_heartbeat'], 'strftime'):
                pass  # Already datetime
            elif isinstance(result.get('last_heartbeat'), str):
                from datetime import datetime as dt
                try:
                    result['last_heartbeat'] = dt.strptime(result['last_heartbeat'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass

            return result
        return None
    except Exception as e:
        logger.warning(f"查询生产数据库失败 device={device_id}: {e}")
        return None


def _version_less_than(v1: str, v2: str) -> bool:
    """比较版本号 v1 < v2"""
    try:
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))
        return parts1 < parts2
    except (ValueError, AttributeError):
        return False


# ==========================================
# 八、企业级扩展 — 智能分组
# ==========================================

class SmartGroupReq(BaseModel):
    name: str
    description: Optional[str] = None
    conditions: dict


class SmartGroupUpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[dict] = None
    enabled: Optional[bool] = None


@router.get("/smart-groups")
def list_smart_groups(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_smart_groups, evaluate_smart_group
    rules = get_smart_groups(db)
    result = []
    for r in rules:
        matched = evaluate_smart_group(db, r.id)
        result.append({
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "rule_type": r.rule_type,
            "conditions": r.conditions,
            "enabled": r.enabled,
            "matched_device_count": len(matched),
            "matched_devices": matched,
            "created_by": r.created_by,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else None,
        })
    return {"success": True, "groups": result}


@router.post("/smart-groups")
def create_smart_group(
    req: SmartGroupReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import create_smart_group as create_sg
    rule = create_sg(db, {"name": req.name, "description": req.description, "conditions": req.conditions}, user.username)
    return {"success": True, "group": {
        "id": rule.id, "name": rule.name, "description": rule.description,
        "conditions": rule.conditions, "enabled": rule.enabled,
    }}


@router.put("/smart-groups/{rule_id}")
def update_smart_group(
    rule_id: int,
    req: SmartGroupUpdateReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import update_smart_group as update_sg
    rule = update_sg(db, rule_id, req.model_dump(exclude_unset=True))
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"success": True, "group": rule}


@router.delete("/smart-groups/{rule_id}")
def delete_smart_group(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import delete_smart_group
    if not delete_smart_group(db, rule_id):
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"success": True}


@router.post("/smart-groups/{rule_id}/evaluate")
def evaluate_smart_group(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import evaluate_smart_group as evaluate
    matched = evaluate(db, rule_id)
    return {"success": True, "rule_id": rule_id, "matched_count": len(matched), "matched_devices": matched}


# ==========================================
# 九、企业级扩展 — 设备标签
# ==========================================

class TagReq(BaseModel):
    device_ids: List[str]
    tag_key: str
    tag_value: str


class TagDeleteReq(BaseModel):
    device_id: str
    tag_key: str


@router.get("/device-tags")
def list_device_tags(
    device_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_device_tags, get_all_tags
    if device_id:
        tags = get_device_tags(db, device_id)
        return {"success": True, "device_id": device_id, "tags": tags}
    all_tags = get_all_tags(db)
    return {"success": True, "tags": all_tags}


@router.post("/device-tags")
def set_device_tags(
    req: TagReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import set_device_tags as set_tags
    count = set_tags(db, req.device_ids, req.tag_key, req.tag_value, user.username)
    return {"success": True, "affected": count}


@router.post("/device-tags/delete")
def remove_device_tag(
    req: TagDeleteReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import delete_device_tag
    delete_device_tag(db, req.device_id, req.tag_key)
    return {"success": True}


# ==========================================
# 十、企业级扩展 — 设备健康度
# ==========================================

@router.get("/device-health/{device_id}")
def device_health(
    device_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import calculate_device_health
    score = calculate_device_health(db, device_id)
    return {"success": True, **score}


@router.get("/device-health/organization-summary")
def org_health_summary(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_health_scores_by_org
    scores = get_health_scores_by_org(db)
    return {"success": True, "organizations": scores}


# ==========================================
# 十一、企业级扩展 — 地域管理
# ==========================================

class RegionReq(BaseModel):
    institution_name: str
    region: Optional[str] = None
    city: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None


@router.get("/regions")
def list_regions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_all_regions, get_region_tree
    regions = get_all_regions(db)
    tree = get_region_tree(db)
    return {"success": True, "regions": regions, "tree": tree}


@router.post("/regions")
def upsert_region(
    req: RegionReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import upsert_region as upsert
    entry = upsert(db, req.model_dump(exclude_unset=True), user.username)
    return {"success": True, "region": entry}


# ==========================================
# 十二、企业级扩展 — 批量操作
# ==========================================

class BatchReq(BaseModel):
    operation_type: str
    target_type: str
    target_id: str
    params: Optional[dict] = None


@router.post("/batch-operations")
def execute_batch(
    req: BatchReq,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import create_batch_operation, update_batch_operation
    from crud import get_monitored_devices, evaluate_smart_group

    # 解析目标设备列表
    device_ids = []
    if req.target_type == 'group':
        from crud import get_device_group_by_id
        g = get_device_group_by_id(db, int(req.target_id))
        device_ids = g.get('device_ids', []) if g else []
    elif req.target_type == 'smart_group':
        device_ids = evaluate_smart_group(db, int(req.target_id))
    elif req.target_type == 'organization':
        devices = get_monitored_devices(db)
        device_ids = [d.device_id for d in devices if (d.owner or '未分配机构') == req.target_id]
    elif req.target_type == 'selection':
        import json
        device_ids = json.loads(req.target_id)

    if not device_ids:
        raise HTTPException(status_code=400, detail="没有匹配的设备")

    job = create_batch_operation(db, req.operation_type, req.target_type,
                                 req.target_id, req.params, user.username)

    success = 0
    failed = 0

    try:
        if req.operation_type == 'tag_firmware':
            from crud import set_firmware_config as set_fw
            ver = req.params.get('version', '') if req.params else ''
            set_fw(db, ver, user.username)
            success = len(device_ids)
        elif req.operation_type == 'mark_offline':
            from crud import create_offline_incident as create_off, handle_offline_incident as handle_off
            reason = req.params.get('reason_tag', '其他') if req.params else '其他'
            for did in device_ids:
                try:
                    inc = create_off(db, did, req.target_id, 0)
                    if inc:
                        handle_off(db, inc.id, reason, '批量标记', user.username)
                        success += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
        elif req.operation_type == 'export':
            # 返回可导出的设备号列表
            update_batch_operation(db, job.id, 'success', len(device_ids), len(device_ids), 0)
            return {"success": True, "job_id": job.id, "device_ids": device_ids}
        else:
            success = len(device_ids)

        update_batch_operation(db, job.id, 'success' if failed == 0 else 'partial',
                              len(device_ids), success, failed)
    except Exception as e:
        update_batch_operation(db, job.id, 'failed', len(device_ids), success, len(device_ids) - success)

    return {"success": True, "job_id": job.id, "affected": len(device_ids),
            "success_count": success, "failed_count": failed}


@router.get("/batch-operations")
def list_batch_ops(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_batch_operations
    return {"success": True, "operations": get_batch_operations(db)}


# ==========================================
# 十三、企业级扩展 — 运营指挥中心
# ==========================================

@router.get("/command-center")
def command_center(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from crud import get_command_center_data
    data = get_command_center_data(db)
    return {"success": True, **data}


# ==========================================
# 十四、异常忽略规则（不考虑列表）
# ==========================================

class IgnoreRuleCreate(BaseModel):
    device_id: str
    anomaly_type: Optional[str] = None
    reason: Optional[str] = None


@router.get("/anomaly-ignore-rules")
def list_ignore_rules(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """获取所有'不考虑'规则列表"""
    from models import AnomalyIgnoreRule
    rules = db.query(AnomalyIgnoreRule).order_by(AnomalyIgnoreRule.created_at.desc()).all()
    return {"success": True, "rules": [
        {"id": r.id, "device_id": r.device_id, "anomaly_type": r.anomaly_type or "全部",
         "reason": r.reason, "created_by": r.created_by,
         "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else ""}
        for r in rules
    ]}


@router.post("/anomaly-ignore-rules")
def add_ignore_rule(req: IgnoreRuleCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """添加'不考虑'规则"""
    from models import AnomalyIgnoreRule
    existing = db.query(AnomalyIgnoreRule).filter(
        AnomalyIgnoreRule.device_id == req.device_id,
        AnomalyIgnoreRule.anomaly_type == req.anomaly_type
    ).first()
    if existing:
        return {"success": True, "message": "规则已存在"}
    rule = AnomalyIgnoreRule(
        device_id=req.device_id, anomaly_type=req.anomaly_type,
        reason=req.reason, created_by=user.username
    )
    db.add(rule)
    db.commit()
    return {"success": True, "rule": {"id": rule.id, "device_id": rule.device_id}}


@router.delete("/anomaly-ignore-rules/{rule_id}")
def delete_ignore_rule(rule_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """移除'不考虑'规则（设备重新开始产生工单）"""
    from models import AnomalyIgnoreRule
    rule = db.query(AnomalyIgnoreRule).filter(AnomalyIgnoreRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(rule)
    db.commit()
    return {"success": True, "message": "已移除，该设备将重新产生异常工单"}


# ==========================================
# 十五、机构趋势数据
# ==========================================

@router.get("/device-status/org-trend")
def org_trend(
    org: str = Query(..., description="机构名称"),
    days: int = Query(7, ge=1, le=90, description="天数"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """获取某机构指定天数内的每日趋势数据"""
    from models import DeviceStatusLog
    from sqlalchemy import func
    from datetime import datetime as dt, timedelta

    end = dt.utcnow().date()
    start = end - timedelta(days=days)

    logs = db.query(DeviceStatusLog).filter(
        DeviceStatusLog.organization == org,
        func.date(DeviceStatusLog.check_time) >= start,
        func.date(DeviceStatusLog.check_time) <= end
    ).order_by(DeviceStatusLog.check_time.asc()).all()

    # 按日期分组
    daily = {}
    for log in logs:
        d = log.check_time.strftime("%Y-%m-%d") if log.check_time else ""
        if d not in daily:
            daily[d] = {"date": d, "total": 0, "online": 0, "offline": 0, "fw_updates": 0, "devices": []}
        daily[d]["total"] += 1
        if log.is_online: daily[d]["online"] += 1
        else: daily[d]["offline"] += 1
        if log.needs_firmware_update: daily[d]["fw_updates"] += 1

    trend = []
    for d, v in sorted(daily.items()):
        v["online_rate"] = round(v["online"] / max(1, v["total"]) * 100, 1)
        trend.append(v)

    return {"success": True, "organization": org, "days": days, "trend": trend}


# ==========================================
# 十六、综合查询 — 按任意维度查看设备
# ==========================================

@router.get("/device-search")
def device_search(
    region: Optional[str] = None,
    city: Optional[str] = None,
    institution: Optional[str] = None,
    tag_key: Optional[str] = None,
    tag_value: Optional[str] = None,
    firmware_below: Optional[str] = None,
    is_online: Optional[bool] = None,
    health_grade: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """多维度设备搜索"""
    from crud import get_monitored_devices, get_latest_device_status
    from crud import get_devices_by_tag, get_all_regions, calculate_device_health

    devices = get_monitored_devices(db)

    # 地域筛选
    if region or city or institution:
        regions = {r.institution_name: r for r in get_all_regions(db)}
        if region:
            devices = [d for d in devices if regions.get(d.owner, None) and regions[d.owner].region == region]
        if city:
            devices = [d for d in devices if regions.get(d.owner, None) and regions[d.owner].city == city]
        if institution:
            devices = [d for d in devices if (d.owner or '未分配机构') == institution]

    # 标签筛选
    if tag_key and tag_value:
        tagged = set(get_devices_by_tag(db, tag_key, tag_value))
        devices = [d for d in devices if d.device_id in tagged]

    # 固件筛选
    if firmware_below:
        statuses = get_latest_device_status(db, device_ids=[d.device_id for d in devices])
        fw_map = {s.device_id: s for s in statuses}
        devices = [d for d in devices if fw_map.get(d.device_id) and
                   fw_map[d.device_id].firmware_version and
                   _version_less_than(fw_map[d.device_id].firmware_version, firmware_below)]

    # 在线状态筛选
    if is_online is not None:
        statuses = get_latest_device_status(db, device_ids=[d.device_id for d in devices])
        online_map = {s.device_id: s.is_online for s in statuses}
        devices = [d for d in devices if online_map.get(d.device_id) == is_online]

    # 健康度筛选
    if health_grade:
        filtered = []
        for d in devices:
            score = calculate_device_health(db, d.device_id)
            if score['grade'] == health_grade:
                filtered.append(d)
        devices = filtered

    return {
        "success": True,
        "total": len(devices),
        "devices": [{"device_id": d.device_id, "owner": d.owner, "device_attribute": d.device_attribute,
                      "version": d.version, "type": d.type} for d in devices],
    }
