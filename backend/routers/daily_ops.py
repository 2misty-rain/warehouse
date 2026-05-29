"""
每日运营分析路由
功能：数据下载、异常分析、设备状态监控
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/daily-ops", tags=["DailyOps"])

# 数据存储根目录：主仓库路径下的 daily_ops_data 目录
# routers/daily_ops.py → backend/ → warehouse/
_WAREHOUSE_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = str(_WAREHOUSE_ROOT / "daily_ops_data")

# 全局缓存（Web 服务生命周期内有效）
_device_mapping_cache = {}
_room_info_cache = {}
_token = None


# ============== 请求模型 ==============

class DownloadRequest(BaseModel):
    date: Optional[str] = None
    include_previous: bool = True


class AnalysisRequest(BaseModel):
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


# ============== API 端点 ==============

@router.post("/download")
def api_download(req: Optional[DownloadRequest] = None):
    """下载指定日期的原始数据报表（含前一天数据用于状态对比）"""
    if req is None:
        req = DownloadRequest()
    target_date = req.date or _get_default_date()

    from daily_ops.downloader import download_reports
    from daily_ops.downloader import login as do_login
    token = _get_token()
    if not token:
        token = do_login()
        if not token:
            raise HTTPException(status_code=500, detail="登录远程报表系统失败")

    os.makedirs(DATA_DIR, exist_ok=True)
    result = download_reports(target_date, DATA_DIR, token, req.include_previous)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "下载失败"))

    _get_device_mapping(force_refresh=True)

    return {
        "success": True,
        "date": target_date,
        "downloaded": result.get("downloaded", []),
        "skipped": result.get("skipped", []),
    }


@router.post("/analyze")
def api_analyze(req: Optional[AnalysisRequest] = None):
    """运行数据分析：异常检测 + 状态变化检测 + 生成报告"""
    if req is None:
        req = AnalysisRequest()
    target_date = req.date or _get_default_date()

    token = _get_token()
    device_mapping = _get_device_mapping()

    from daily_ops.analyzer import analyze_today
    result = analyze_today(target_date, DATA_DIR, token, device_mapping, _room_info_cache)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "分析失败"))

    return {
        "success": True,
        "date": result["date"],
        "summary_text": result["summary_text"],
        "output_file": result["output_file"],
        "stats": result["stats"],
    }


@router.post("/run-full")
def api_run_full(req: Optional[AnalysisRequest] = None):
    """一键执行完整流程：下载 + 分析"""
    if req is None:
        req = AnalysisRequest()
    target_date = req.date or _get_default_date()

    from daily_ops.downloader import download_reports
    from daily_ops.downloader import login as do_login
    from daily_ops.analyzer import analyze_today

    # Step 1: 登录并下载
    token = _get_token()
    if not token:
        token = do_login()
        if not token:
            raise HTTPException(status_code=500, detail="登录远程报表系统失败")

    os.makedirs(DATA_DIR, exist_ok=True)
    dl_result = download_reports(target_date, DATA_DIR, token, include_previous=True)

    if not dl_result.get("success"):
        raise HTTPException(status_code=500, detail=dl_result.get("error", "下载失败"))

    # Step 2: 刷新映射
    device_mapping = _get_device_mapping(force_refresh=True)

    # Step 3: 分析
    analysis_result = analyze_today(target_date, DATA_DIR, token, device_mapping, _room_info_cache)

    if not analysis_result.get("success"):
        raise HTTPException(status_code=500, detail=analysis_result.get("error", "分析失败"))

    return {
        "success": True,
        "date": target_date,
        "downloaded": dl_result.get("downloaded", []),
        "skipped": dl_result.get("skipped", []),
        "summary_text": analysis_result["summary_text"],
        "output_file": analysis_result["output_file"],
        "stats": analysis_result["stats"],
    }


def _parse_report_txt(txt_content: str) -> dict:
    """从汇总报告文本中提取统计数据"""
    stats = {
        "valid_devices": 0, "abnormal_devices": 0, "total_summary": 0,
        "sleep_too_little": 0, "multiple_bed_exit": 0,
        "sleep_abnormal": 0, "vital_abnormal": 0, "status_changes": 0,
    }
    for line in txt_content.split('\n'):
        line = line.strip()
        m = re.search(r'有效设备(\d+)台', line)
        if m: stats["valid_devices"] = int(m.group(1))
        m = re.search(r'异常明细(\d+)条', line)
        if m: stats["abnormal_devices"] = int(m.group(1))
        m = re.search(r'异常汇总(\d+)条', line)
        if m: stats["total_summary"] = int(m.group(1))
        m = re.search(r'睡眠过少(\d+)例', line)
        if m: stats["sleep_too_little"] = int(m.group(1))
        m = re.search(r'多次离床(\d+)例', line)
        if m: stats["multiple_bed_exit"] = int(m.group(1))
        m = re.search(r'睡眠状态异常(\d+)例', line)
        if m: stats["sleep_abnormal"] = int(m.group(1))
        m = re.search(r'体征异常(\d+)例', line)
        if m: stats["vital_abnormal"] = int(m.group(1))
        m = re.search(r'状态变化设备(\d+)台', line)
        if m: stats["status_changes"] = int(m.group(1))
    return stats


@router.get("/report")
def api_get_report(date: Optional[str] = None):
    """获取已有分析报告的摘要（含解析后的统计数据）"""
    target_date = date or _get_default_date()

    txt_file = os.path.join(DATA_DIR, target_date, f"汇总报告_{target_date}.txt")
    if not os.path.exists(txt_file):
        return {
            "success": True,
            "date": target_date,
            "summary_text": f"【{target_date}】\n尚未生成分析报告，请先执行「一键执行」或「运行分析」。",
            "has_report": False,
            "stats": None,
        }

    with open(txt_file, 'r', encoding='utf-8') as f:
        summary_text = f.read()

    return {
        "success": True,
        "date": target_date,
        "summary_text": summary_text,
        "has_report": True,
        "stats": _parse_report_txt(summary_text),
    }


@router.get("/available-dates")
def api_available_dates():
    """获取已有数据的日期列表"""
    if not os.path.exists(DATA_DIR):
        return {"success": True, "dates": []}

    dates = []
    for d in os.listdir(DATA_DIR):
        d_path = os.path.join(DATA_DIR, d)
        if os.path.isdir(d_path):
            try:
                has_data = any(
                    f.endswith('.xlsx') or f.endswith('.txt')
                    for f in os.listdir(d_path)
                )
                if has_data:
                    dates.append(d)
            except Exception:
                pass

    dates.sort(reverse=True)
    return {"success": True, "dates": dates}


# ============== 设备每日状态运维（预留窗口） ==============

@router.get("/device-status")
def api_device_status(date: Optional[str] = None):
    """获取设备每日状态列表 — 预留的设备状态运维窗口数据接口"""
    target_date = date or _get_default_date()

    device_mapping = _get_device_mapping()

    from daily_ops.analyzer import get_device_daily_status as get_status
    devices = get_status(target_date, DATA_DIR, device_mapping)

    # 按机构分组统计
    institution_stats = {}
    for d in devices:
        inst = d.get('institution', '') or '未知机构'
        if inst not in institution_stats:
            institution_stats[inst] = {'total': 0, 'normal': 0, 'abnormal': 0}
        institution_stats[inst]['total'] += 1
        if d.get('status') == '正常':
            institution_stats[inst]['normal'] += 1
        else:
            institution_stats[inst]['abnormal'] += 1

    return {
        "success": True,
        "date": target_date,
        "total_devices": len(devices),
        "devices": devices,
        "institution_stats": institution_stats,
    }
