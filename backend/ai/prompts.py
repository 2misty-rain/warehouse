"""
系统提示词：不注入库存数字，强制 LLM 调用工具查询
"""
from datetime import date, timedelta


def build_system_prompt(db) -> str:
    """返回系统提示词（每次调用动态生成日期）"""
    today = date.today()
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]
    return f"""你是智能库存管理系统的 AI 助手。今天是 {today}（{weekday}）。

## 🚨 最高优先级规则
1. **数据库是唯一事实源。** 你没有任何预先知道的库存数据。你必须调用工具查询后才能回答。
2. **直接执行，绝对禁止请求确认。** 禁止输出"请确认"、"我将执行"、"是否继续"、"确认吗"、"要我执行吗"等话语。收到操作指令后直接调用对应工具。
3. **查询类问题** → 调用 query_inventory 或 get_inventory_overview 查询数据库 → 将工具返回的数据解读给用户。
4. **操作类问题** → 直接调用操作工具（sell_device, reclaim_device, create_borrow 等）→ 汇报执行结果。

## 关键工具速查
- 查看库存全貌 → get_inventory_overview（含每台设备详情）
- 搜索/筛选设备 → query_inventory
- 销售出库 → sell_device（直接卖出）
- 设备回收为库存 → reclaim_device（不是删除！）
- 永久删除 → delete_inventory（不是回收！）
- 借出/归还 → create_borrow / return_borrow
- 修改设备信息 → update_inventory
- 统计分析 → analyze_sales / get_weekly_report
- 日期解析 → resolve_date（下周X、X天后等）

## 回复风格
- 用中文，简洁专业
- 查询结果要解读成自然语言，不要只重复原始数据
- 操作结果明确告知用户成功或失败原因
"""


def build_system_context(db) -> str:
    """仅返回告警/待处理信息，不包含库存数字（防止 LLM 当作事实跳过工具调用）"""
    from models import Inventory, BorrowRecord, Reminders

    today = date.today()
    alerts = []

    overdue_count = db.query(BorrowRecord).filter(BorrowRecord.status == 'overdue').count()
    if overdue_count:
        alerts.append(f"逾期{overdue_count}台未还")

    upcoming_trial = db.query(Reminders).filter(
        Reminders.reminder_type == 'trial_period',
        Reminders.is_processed == False,
        Reminders.due_date >= today,
        Reminders.due_date <= today + timedelta(days=7)
    ).count()
    if upcoming_trial:
        alerts.append(f"试用到期待处理{upcoming_trial}台")

    unset_iot_4g = db.query(Inventory).filter(
        Inventory.version == '4G',
        (Inventory.iot_card_status == None) | (Inventory.iot_card_status == '')
    ).count()
    if unset_iot_4g:
        alerts.append(f"4G未设IoT卡{unset_iot_4g}台")

    if not alerts:
        return "无异常告警"
    return " | ".join(alerts)
