"""
API 客户端模块
功能：
1. 批量查询所有机构的设备，建立 deviceId -> personId 映射
2. 查询离床时间事件
3. 查询设备房间信息
4. 格式化输出

设计说明：
- 所有函数均为无副作用纯函数，缓存由调用方管理
- 为未来数据库连接预留 DataSource 抽象接口
"""

import requests
import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# ============== 配置 ==============
BASE_URL = "http://dev.cloud.racobit.com:18000"
DEVICE_API_URL = f"{BASE_URL}/DeviceService/findDeviceByAny"
SLEEP_API_URL = f"{BASE_URL}/SleepService/findSleepAndBodyMovementList"

USERNAME = "neiceliye"
PASSWORD_MD5 = "e10adc3949ba59abbe56e057f20f883e"  # 123456 的 MD5

# 机构全名->简称映射
ORG_FULL_TO_SHORT = {
    "外部设备管理平台": "外部设备",
    "三代商机": "三代商机",
    "温泉镇": "温泉镇",
    "颐寿轩-白纸坊": "白纸坊",
    "生命雷达测试": "生命雷达测试",
    "仁善康复": "仁善康复",
    "紫竹院": "紫竹院",
    "兴谷养老": "兴谷养老",
    "智能看护平台": "智能看护平台",
    "紫竹院街道": "紫竹院",
    "生命雷达内测": "内测",
    "星星雨": "星星雨",
    "苏家坨镇养老服务中心": "老年福",
    "冬竹园康养中心": "冬竹园",
    "植乡居智慧看护平台": "植乡居",
    "紫竹院街道养老服务中心": "紫竹院机构",
    "北京康养颐寿嘉园空港": "空港",
    "北京展厅智能看护平台": "北京展厅",
    "彩鸟露营智能看护": "彩鸟露营",
    "第一视频公司": "第一视频公司",
    "彭州熙湖人家养老院": "彭州熙湖人家养老院",
    "上海展会": "智能看护平台",
    "上海展会2": "智能看护平台",
    "模式口西里老年福": "石景山老年福",
    "银丰康养中心": "银丰康养中心",
    "北京东方综合养老院": "北京东方综合养老院",
    "广州博览会": "广州博览会",
    "安宁疗护": "安宁疗护",
    "四季青论坛": "四季青论坛",
    "韵慈善常青智慧医养中心": "韵慈善",
    "海淀第二十二离职干部修养所照料中心": "干休所",
    "北康养颐寿嘉园（善果寺）": "善果寺",
    "太平路驿站样板间": "太平路驿站样板间",
    "昌平区敬老院": "马池口养老中心",
    "银龄爱护": "银龄爱护",
    "民岳家园": "民岳家园",
    "山东亚华": "山东亚华",
    "理工社区": "理工社区",
    "通运街道养老服务中心": "通运街道养老服务中心",
    "北康养居家项目": "北康养居家",
    "赤峰养老院": "赤峰养老院",
    "青城山护理平台": "青城山护理平台",
    "合肥智慧看护": "合肥智慧看护",
    "渭南智慧看护": "渭南智慧看护",
    "宝鸡智慧看护": "宝鸡智慧看护",
    "四代产品试用": "四代试用",
    "高碑店养老服务中心": "高碑店养老服务中心",
    "苏州阳澄湖护理院": "苏州阳澄湖护理院",
    "陶坝社区党群服务中心": "陶坝社区党群服务中心",
    "中车康养": "中车康养",
    "大家的家合肥梧桐里城心社区": "梧桐里城心社区",
    "曲江养老院": "曲江养老院",
    "青橙医养康复院": "青橙医养康复院",
    "颐瑞府": "颐瑞府",
    "溪翁镇社会福利中心": "溪翁镇社会福利中心",
    "万寿路海军干休所": "万寿路海军干休所",
    "光明老年护理院": "骥枥众城",
    "和熹会": "和熹会",
    "鹏瑞利康养社区": "鹏瑞利康养社区",
    "北京瀚海文化": "北京瀚海文化",
    "东城前门养老照料中心": "东城前门养老照料中心",
    "悠享时光包河康养中心": "悠享时光包河康养中心",
    "梁园镇护城社区养老院": "梁园镇护城社区养老院",
    "无锡智慧看护平台": "无锡智慧看护平台",
    "智慧看护系统": "智慧看护系统",
    "合肥演示": "合肥演示"
}

# 需要查询的机构 ID 列表
ORGANIZATION_IDS = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18,
    21, 22, 23, 24, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
    41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56,
    57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73
]


# ============== DataSource 抽象接口 ==============
# 为未来数据库直连预留，当前使用 API 实现

class DataSource:
    """数据源抽象基类 — 未来可替换为数据库直连实现"""

    def get_device_mapping(self) -> Dict[str, dict]:
        raise NotImplementedError

    def get_device_room_info(self, device_id: str) -> str:
        raise NotImplementedError

    def get_bed_exit_events(self, device_id: str, start_date: str, end_date: str) -> List[dict]:
        raise NotImplementedError


class APIDataSource(DataSource):
    """基于远程 API 的数据源实现"""

    def __init__(self, token: str, device_mapping_cache: dict, room_info_cache: dict):
        self.token = token
        self.device_mapping_cache = device_mapping_cache
        self.room_info_cache = room_info_cache

    def get_device_mapping(self) -> Dict[str, dict]:
        return self.device_mapping_cache

    def get_device_room_info(self, device_id: str) -> str:
        return get_room_info(device_id, self.token, self.room_info_cache)

    def get_bed_exit_events(self, device_id: str, start_date: str, end_date: str) -> List[dict]:
        events = query_bed_exit_events(device_id, start_date, end_date, self.token, self.device_mapping_cache)
        return filter_bed_exit_events_for_today(events, start_date)


# ============== 认证 ==============

def login() -> Optional[str]:
    """登录系统，获取 token"""
    url = f"{BASE_URL}/auth/login?username={USERNAME}&password={PASSWORD_MD5}"
    headers = {"Accept": "application/json"}
    try:
        response = requests.post(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.cookies.get("token")
    except requests.RequestException as e:
        logger.error(f"登录失败: {e}")
    return None


# ============== 房间信息 ==============

def fetch_room_info_by_device_id(device_id: str, token: str) -> dict:
    """根据设备ID查询房间信息（遍历所有机构）"""
    headers = {
        "Accept": "application/json",
        "Cookie": f"token={token}",
    }

    for org_id in ORGANIZATION_IDS:
        payload = {"pageIndex": 0, "pageSize": 1000, "organizationId": org_id}
        try:
            response = requests.post(DEVICE_API_URL, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    for device in result.get("data", {}).get("content", []):
                        if device.get("deviceId") == device_id:
                            room_name = device.get("roomName", "") or ""
                            return {"roomInfo": room_name, "roomName": room_name, "bedName": "", "personName": ""}
        except Exception:
            continue

    return {"roomInfo": "", "roomName": "", "bedName": "", "personName": ""}


def get_room_info(device_id: str, token: str, room_info_cache: dict = None) -> str:
    """获取设备房间信息，带缓存"""
    if room_info_cache is None:
        room_info_cache = {}

    if device_id in room_info_cache:
        return room_info_cache[device_id].get("roomInfo", "")

    room_info = fetch_room_info_by_device_id(device_id, token)
    room_info_cache[device_id] = room_info
    return room_info.get("roomInfo", "")


# ============== 设备映射 ==============

def fetch_device_mapping(token: str) -> Dict[str, dict]:
    """查询所有机构的设备，建立 deviceId -> {personId, organizationName} 映射"""
    headers = {
        "Accept": "application/json",
        "Cookie": f"token={token}",
    }

    logger.info(f"开始查询 {len(ORGANIZATION_IDS)} 个机构的设备...")
    device_mapping = {}

    for org_id in ORGANIZATION_IDS:
        page_index = 0
        page_size = 100
        total_fetched = 0

        while True:
            payload = {"pageIndex": page_index, "pageSize": page_size, "organizationId": org_id}
            try:
                response = requests.post(DEVICE_API_URL, headers=headers, json=payload, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        content = result.get("data", {}).get("content", [])
                        if not content:
                            break

                        for device in content:
                            device_id = device.get("deviceId")
                            person_id = device.get("personId")
                            org_full_name = device.get("organizationName", "")
                            if device_id and person_id:
                                org_short = ORG_FULL_TO_SHORT.get(org_full_name, org_full_name)
                                device_mapping[device_id] = {
                                    "personId": person_id,
                                    "organizationName": org_short,
                                }

                        total_fetched += len(content)
                        total_elements = result.get("data", {}).get("totalElements", 0)
                        if total_fetched >= total_elements:
                            break
                        page_index += 1
                    else:
                        break
                else:
                    break
            except Exception as e:
                logger.warning(f"查询机构 {org_id} 异常: {e}")
                break

    logger.info(f"设备映射完成，共 {len(device_mapping)} 个设备")
    return device_mapping


def load_device_mapping(token: str, cache_dir: str = None, force_refresh: bool = False) -> Dict[str, dict]:
    """加载设备映射（优先使用缓存）"""
    if cache_dir is None:
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache')

    cache_file = os.path.join(cache_dir, "device_mapping.json")

    if force_refresh or not os.path.exists(cache_file):
        mapping_data = fetch_device_mapping(token)
        if mapping_data:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, ensure_ascii=False, indent=2)
            return mapping_data
        return {}
    else:
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载设备映射缓存失败: {e}")
            return {}


def get_person_id(device_id: str, device_mapping_cache: dict) -> Optional[int]:
    """获取设备号对应的 personId"""
    entry = device_mapping_cache.get(device_id, {})
    if isinstance(entry, dict):
        return entry.get("personId")
    return None


# ============== 离床事件 ==============

def query_bed_exit_events(device_id: str, start_date: str, end_date: str = None,
                          token: str = None, device_mapping_cache: dict = None) -> List[dict]:
    """查询指定设备在日期范围内的离床事件"""
    if not device_id:
        return []
    if end_date is None:
        end_date = start_date
    if device_mapping_cache is None:
        device_mapping_cache = {}

    person_id = get_person_id(device_id, device_mapping_cache)
    if person_id is None:
        return []

    headers = {
        "Accept": "application/json",
        "Cookie": f"token={token}",
    }

    payload = {
        "pageIndex": 0,
        "pageSize": 100,
        "type": 21,
        "startDate": start_date,
        "endDate": end_date,
        "personId": person_id,
    }

    try:
        response = requests.post(SLEEP_API_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                data = result.get("data")
                if isinstance(data, dict):
                    events = data.get("content", [])
                    if isinstance(events, list):
                        return events
    except Exception as e:
        logger.warning(f"查询设备 {device_id} 离床事件异常: {e}")

    return []


def filter_bed_exit_events_for_today(events: List[dict], today_str: str) -> List[dict]:
    """过滤出属于今天睡眠时段的离床事件（昨天18:00 ~ 今天10:00）"""
    today = datetime.strptime(today_str, "%Y-%m-%d")
    yesterday = today - timedelta(days=1)
    start_boundary = yesterday.replace(hour=18, minute=0, second=0)
    end_boundary = today.replace(hour=10, minute=0, second=0)

    filtered = []
    for event in events:
        start_time_str = event.get("startTime", "")
        if not start_time_str:
            continue
        try:
            start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            if start_boundary <= start_time <= end_boundary:
                filtered.append(event)
        except ValueError:
            continue
    return filtered


def format_duration(milliseconds: int) -> str:
    """将毫秒转换为可读格式"""
    total_seconds = int(milliseconds / 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    if minutes > 0 and seconds > 0:
        return f"{minutes}分钟{seconds}秒"
    elif minutes > 0:
        return f"{minutes}分钟"
    return f"{seconds}秒"


def format_bed_exit_events(events: List[dict]) -> str:
    """格式化离床事件列表为显示文本"""
    if not events:
        return "离床0次"

    count = len(events)
    lines = [f"离床{count}次"]

    for event in events:
        start_time = event.get("startTime", "")
        end_time = event.get("endTime", "")
        duration = event.get("duration", 0)

        start_time_part = start_time.split(" ")[1] if " " in start_time else start_time
        end_time_part = end_time.split(" ")[1] if " " in end_time else end_time

        if ":" in start_time_part:
            start_display = ":".join(start_time_part.split(":")[:2])
        else:
            start_display = start_time_part

        if ":" in end_time_part:
            end_display = ":".join(end_time_part.split(":")[:2])
        else:
            end_display = end_time_part

        duration_display = format_duration(duration)
        lines.append(f"{start_display}到{end_display}，{duration_display}")

    return "\n".join(lines)
