"""
报表下载模块
功能：登录远程 API 并下载指定日期的原始数据报表

设计说明：
- 为未来数据库直连预留接口，当前使用远程 API
- 支持文件缓存，避免重复下载
"""

import requests
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BASE_URL = "http://dev.cloud.racobit.com:18000"
LOGIN_URL = f"{BASE_URL}/auth/login"
EXPORT_URL = f"{BASE_URL}/ReportService/exportRawDataReportOfAll"

USERNAME = "neiceliye"
PASSWORD_MD5 = "e10adc3949ba59abbe56e057f20f883e"


def login() -> Optional[str]:
    """登录系统，获取 token"""
    logger.info("正在登录报表系统...")
    url = f"{LOGIN_URL}?username={USERNAME}&password={PASSWORD_MD5}"
    headers = {"Accept": "application/json"}

    try:
        response = requests.post(url, headers=headers, timeout=10)
        if response.status_code == 200:
            token = response.cookies.get("token")
            if token:
                logger.info(f"登录成功，Token: {token[:8]}...")
                return token
    except requests.RequestException as e:
        logger.error(f"登录失败: {e}")
    return None


def export_report(token: str, target_date: str) -> Optional[bytes]:
    """导出指定日期的报表数据"""
    logger.info(f"正在导出 {target_date} 的报表...")
    headers = {
        "Accept": "application/json",
        "Cookie": f"token={token}",
    }
    payload = {
        "startDate": target_date,
        "endDate": target_date,
        "rawDataReportTypes": [1]
    }

    try:
        response = requests.post(EXPORT_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            logger.info(f"报表导出成功: {target_date}")
            return response.content
    except requests.RequestException as e:
        logger.error(f"导出失败: {e}")
    return None


def save_excel(data: bytes, target_date: str, data_dir: str) -> str:
    """保存 Excel 文件到日期文件夹，返回文件路径"""
    date_folder = os.path.join(data_dir, target_date)
    os.makedirs(date_folder, exist_ok=True)

    filename = f"原始数据_{target_date}.xlsx"
    filepath = os.path.join(date_folder, filename)

    with open(filepath, "wb") as f:
        f.write(data)

    logger.info(f"文件已保存: {filepath}")
    return filepath


def download_reports(target_date: str, data_dir: str, token: str = None,
                     include_previous: bool = True) -> dict:
    """
    下载指定日期的报表数据

    Args:
        target_date: 目标日期 YYYY-MM-DD
        data_dir: 数据存储目录
        token: 可选的已有 token
        include_previous: 是否同时下载前一天的数据（用于状态对比）

    Returns:
        dict: {success, token, date, files: [下载的文件路径列表]}
    """
    if token is None:
        token = login()
    if not token:
        return {"success": False, "error": "登录失败"}

    downloaded = []
    skipped = []
    dates_to_fetch = [target_date]

    if include_previous:
        prev_date = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        dates_to_fetch.insert(0, prev_date)

    for date_str in dates_to_fetch:
        file_path = os.path.join(data_dir, date_str, f"原始数据_{date_str}.xlsx")
        if os.path.exists(file_path):
            skipped.append(date_str)
            logger.info(f"跳过已存在的文件: {date_str}")
            continue

        data = export_report(token, date_str)
        if data:
            path = save_excel(data, date_str, data_dir)
            downloaded.append(path)
        else:
            return {"success": False, "error": f"下载 {date_str} 数据失败"}

    return {
        "success": True,
        "token": token,
        "date": target_date,
        "downloaded": downloaded,
        "skipped": skipped,
    }
