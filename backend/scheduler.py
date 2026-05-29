"""
定时任务调度器
- 每天 9:00 设备状态同步
- 每天 13:00 异常数据同步
- 每天 18:00 日报生成
- 每周一 8:00 周报生成
"""

import asyncio
import logging
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)

# 调度器运行状态
_running = False
_tasks: list[asyncio.Task] = []


async def _job_device_status_sync():
    """设备状态同步（每天 9:00）"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        from routers.operations import _get_production_db_config
        db_config = _get_production_db_config()
        if not db_config:
            logger.warning("设备状态同步跳过：未配置生产数据库连接")
            return

        from crud import get_monitored_devices, save_device_status_logs
        from crud import create_offline_incident, auto_close_offline_incident, get_firmware_config
        from crud import get_latest_device_status as get_latest
        from routers.operations import _query_device_from_production

        devices = get_monitored_devices(db)
        if not devices:
            logger.info("设备状态同步：没有需要监控的设备")
            return

        fw_config = get_firmware_config(db)
        normal_version = fw_config.current_normal_version if fw_config else None
        check_time = datetime.utcnow()
        logs = []

        for device in devices:
            did = device.device_id
            org = device.owner or '未分配机构'
            prod_data = _query_device_from_production(db_config, did)

            is_online = False
            last_heartbeat = None
            firmware_version = None

            if prod_data:
                is_online = prod_data.get('is_online', False)
                firmware_version = prod_data.get('firmware_version')
                last_heartbeat = prod_data.get('last_heartbeat')

            offline_duration = 0
            if not is_online and last_heartbeat:
                offline_duration = int((check_time - last_heartbeat).total_seconds() / 60)
            elif is_online and last_heartbeat:
                delta = (check_time - last_heartbeat).total_seconds() / 60
                if delta > 30:
                    is_online = False
                    offline_duration = int(delta)

            needs_update = False
            if normal_version and firmware_version:
                from routers.operations import _version_less_than
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

        if logs:
            save_device_status_logs(db, logs)
            logger.info(f"设备状态同步完成：保存 {len(logs)} 条记录")

        # 离线事件处理
        latest_statuses = get_latest(db, device_ids=[d.device_id for d in devices])
        status_map = {s.device_id: s for s in latest_statuses}

        for dev in devices:
            s = status_map.get(dev.device_id)
            if s and not s.is_online:
                incident = create_offline_incident(db, dev.device_id, dev.owner or '未分配机构',
                                                   s.offline_duration_minutes or 0, s.firmware_version)
                if incident:
                    logger.info(f"离线事件创建: {dev.device_id}")
            elif s and s.is_online:
                closed = auto_close_offline_incident(db, dev.device_id)
                if closed:
                    logger.info(f"离线事件自动关闭: {dev.device_id}")

    except Exception as e:
        logger.error(f"设备状态同步失败: {e}", exc_info=True)
    finally:
        db.close()


async def _job_anomaly_data_sync():
    """异常数据同步（每天 13:00）"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        from crud import create_sync_log, update_sync_log, create_anomaly_records_batch
        from daily_ops.downloader import download_reports, login as do_login
        from daily_ops.analyzer import analyze_today
        from routers.operations import DATA_DIR, _get_device_mapping, _room_info_cache
        import os

        target_date = datetime.now().strftime("%Y-%m-%d")
        sync_date = datetime.strptime(target_date, "%Y-%m-%d").date()

        log_entry = create_sync_log(db, sync_date, 'auto')

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

        summary_rows = analysis_result.get("summary_rows", [])
        stats = analysis_result.get("stats", {})

        anomaly_records = []
        for row in summary_rows:
            a_type = row.get('问题分类', '')
            record = {
                "record_date": sync_date,
                "institution": row.get('机构', ''),
                "device_id": str(row.get('设备号', '')),
                "person_name": row.get('姓名', ''),
                "anomaly_type": a_type,
                "anomaly_detail": row.get('事件记录', ''),
                "event_time": row.get('事件发生时间', ''),
                "raw_data": row,
            }
            if a_type == '体征异常':
                record["status"] = '已归档'
                record["priority"] = '低'
            elif a_type == '睡眠状态异常':
                record["priority"] = '高'
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
        logger.info(f"异常数据同步完成：插入 {inserted} 条记录")

    except Exception as e:
        logger.error(f"异常数据同步失败: {e}", exc_info=True)
        try:
            update_sync_log(db, log_entry.id, 'failed', error_message=str(e))
        except Exception:
            pass
    finally:
        db.close()


async def _job_generate_daily_report():
    """日报生成（每天 18:00）"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        from crud import create_daily_report, get_latest_device_status, get_monitored_devices
        from crud import get_anomaly_records, get_offline_incidents

        target_date = datetime.now().strftime("%Y-%m-%d")
        report_date = datetime.strptime(target_date, "%Y-%m-%d").date()

        devices = get_monitored_devices(db)
        device_ids = [d.device_id for d in devices]
        total_devices = len(device_ids)

        statuses = get_latest_device_status(db, device_ids=device_ids) if device_ids else []
        online_count = sum(1 for s in statuses if s.is_online)
        online_rate = round(online_count / len(statuses) * 100, 1) if statuses else 0
        offline_count = len(statuses) - online_count

        anomaly_result = get_anomaly_records(db, record_date=target_date, limit=10000)
        new_anomalies = anomaly_result["total"]

        incident_result = get_offline_incidents(db, limit=10000)
        today_incidents = [
            i for i in incident_result["items"]
            if i.detected_at and i.detected_at.strftime("%Y-%m-%d") == target_date
        ]

        resolved_result = get_anomaly_records(db, status='已完成', record_date=target_date, limit=10000)

        summary_text = f"【{target_date}运营日报】\n"
        summary_text += f"监控设备{total_devices}台，在线{online_count}台，在线率{online_rate}%\n"
        summary_text += f"新增异常{new_anomalies}条，新增离线事件{len(today_incidents)}个，已处理{resolved_result['total']}条"

        data = {
            "device_online_rate": online_rate,
            "total_monitored_devices": total_devices,
            "offline_count": offline_count,
            "new_anomalies": new_anomalies,
            "new_offline_incidents": len(today_incidents),
            "resolved_count": resolved_result["total"],
            "summary_text": summary_text,
        }

        create_daily_report(db, report_date, data)
        logger.info(f"日报生成完成: {target_date}")

    except Exception as e:
        logger.error(f"日报生成失败: {e}", exc_info=True)
    finally:
        db.close()


async def _job_generate_weekly_report():
    """周报生成（每周一 8:00）"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        today = date.today()
        if today.weekday() != 0:
            return  # 不是周一，跳过

        from crud import create_weekly_report, get_anomaly_records

        ws = today - timedelta(days=7)  # 上周一
        we = ws + timedelta(days=6)     # 上周日

        anomaly_result = get_anomaly_records(db, limit=10000)
        week_items = []
        for item in anomaly_result["items"]:
            if item.record_date and ws <= item.record_date <= we:
                week_items.append(item)

        total_anomalies = len(week_items)
        resolved = sum(1 for item in week_items if item.status in ('已完成', '已归档'))
        resolution_rate = round(resolved / total_anomalies * 100, 1) if total_anomalies > 0 else 0

        inst_counts = {}
        for item in week_items:
            inst = item.institution or '未知'
            inst_counts[inst] = inst_counts.get(inst, 0) + 1
        top_institutions = sorted(inst_counts.items(), key=lambda x: -x[1])[:10]

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

        create_weekly_report(db, ws, we, report_data)
        logger.info(f"周报生成完成: {ws} ~ {we}")

    except Exception as e:
        logger.error(f"周报生成失败: {e}", exc_info=True)
    finally:
        db.close()


def _already_ran_today(task_name: str, db) -> bool:
    """检查任务今天是否已执行过"""
    from crud import get_latest_device_status
    from models import DataSyncLog, DailyReport, WeeklyReport
    from datetime import date as date_type, datetime as dt

    today = date_type.today()

    if task_name == 'device':
        statuses = get_latest_device_status(db)
        if statuses:
            latest = statuses[0]
            if latest.check_time and latest.check_time.date() == today:
                return True
    elif task_name == 'anomaly':
        log = db.query(DataSyncLog).filter(
            DataSyncLog.sync_date == today,
            DataSyncLog.status == 'success'
        ).first()
        if log:
            return True
    elif task_name == 'daily_report':
        report = db.query(DailyReport).filter(
            DailyReport.report_date == today
        ).first()
        if report:
            return True
    elif task_name == 'weekly_report':
        today_dt = dt.utcnow().date() if hasattr(dt, 'utcnow') else date_type.today()
        if today_dt.weekday() == 0:
            report = db.query(WeeklyReport).filter(
                WeeklyReport.week_start == today_dt - timedelta(days=7)
            ).first()
            if report:
                return True
        else:
            return True  # 不是周一，跳过
    return False


async def _scheduler_loop():
    """主调度循环 — 每分钟检查一次，到达预定时间且今天未执行则执行"""
    global _running
    _running = True
    logger.info("定时任务调度器已启动（等待到达预定时间）")

    while _running:
        now = datetime.now()

        # 到达整点附近才检查（减少数据库查询）
        if now.minute <= 1:
            from database import SessionLocal
            db = SessionLocal()
            try:
                # 9:00 设备状态同步
                if now.hour == 9:
                    if not _already_ran_today('device', db):
                        logger.info("执行定时任务: 设备状态同步 (9:00)")
                        await _job_device_status_sync()

                # 13:00 异常数据同步
                if now.hour == 13:
                    if not _already_ran_today('anomaly', db):
                        logger.info("执行定时任务: 异常数据同步 (13:00)")
                        await _job_anomaly_data_sync()

                # 18:00 日报生成
                if now.hour == 18:
                    if not _already_ran_today('daily_report', db):
                        logger.info("执行定时任务: 日报生成 (18:00)")
                        await _job_generate_daily_report()

                # 周一 8:00 周报生成
                if now.weekday() == 0 and now.hour == 8:
                    if not _already_ran_today('weekly_report', db):
                        logger.info("执行定时任务: 周报生成 (周一8:00)")
                        await _job_generate_weekly_report()

            except Exception as e:
                logger.error(f"调度器错误: {e}")
            finally:
                db.close()

        await asyncio.sleep(60)  # 每分钟检查一次


def start_scheduler():
    """启动调度器（在 FastAPI 启动时调用）"""
    global _tasks
    task = asyncio.create_task(_scheduler_loop())
    _tasks.append(task)
    logger.info("调度器任务已创建")
    return task


def stop_scheduler():
    """停止调度器（在 FastAPI 关闭时调用）"""
    global _running, _tasks
    _running = False
    for task in _tasks:
        task.cancel()
    _tasks.clear()
    logger.info("调度器已停止")
