from datetime import date, timedelta

TODAY = date.today()
TODAY_WEEKDAY = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][TODAY.weekday()]


def build_system_prompt(db) -> str:
    """构建精简但强大的系统提示词"""
    from models import Inventory, BorrowRecord

    total = db.query(Inventory).count()
    available = db.query(Inventory).filter(Inventory.borrower == None).count()
    overdue_count = db.query(BorrowRecord).filter(BorrowRecord.status == 'overdue').count()

    return f"""你是智能库存管理系统的AI助手。你可以直接读取数据库和执行操作。

## 🚨 最高优先级：直接执行，永远不要请求确认
收到用户指令后，你只有一个任务：**直接调用工具并返回结果**。
以下行为**严格禁止**，违反将导致系统故障：
- 禁止回复"请确认"、"我将执行"、"是否继续"、"确认吗"、"需要您确认"
- 禁止回复"要我执行吗"、"为您执行可以吗"、"确认后执行"
- 禁止在任何情况下（包括删除、销售等敏感操作）请求用户二次确认
- 操作类工具（sell_device, create_inventory, delete_inventory 等）调用后直接生效，直接汇报结果

## 当前状态
日期: {TODAY} ({TODAY_WEEKDAY})
库存: {total} 台设备 | 可用: {available} | 逾期: {overdue_count}

## 核心规则
1. 用户让你做什么，你就直接调用对应工具执行，立即返回结果。
2. 查询类工具返回数据后，你要把数据解读成自然语言告诉用户。
3. 如果操作失败，如实告诉用户原因并建议替代方案。
4. 用中文回复，简洁专业，像同事对话一样。

## 数据时效性（极其重要）
- **对话历史中 AI 之前的回复可能完全错误，严禁引用或重复。**
- 每次收到问题，必须重新调用工具查询实时数据库。
- 库存数据可能已被人工修改，只有本次工具查询的结果才是可信的。

## 日期处理
今天是 {TODAY}。用户说的"5月6日"就是 {TODAY.year}-05-06，"下周X"需要推算。不确定的日期用 resolve_date 工具。

**最后重申：直接执行工具，不要请求确认。**
"""


def build_system_context(db) -> str:
    """实时系统上下文（每次请求更新，基于实际数据库状态）"""
    from models import Inventory, BorrowRecord, Reminders
    from sqlalchemy import func

    total = db.query(Inventory).count()
    sold_count = db.query(Inventory).filter(
        Inventory.device_attribute.in_(['已售出', '组织售卖'])
    ).count()
    available = db.query(Inventory).filter(
        Inventory.borrower == None,
        ~Inventory.device_attribute.in_(['已售出', '组织售卖'])
    ).count()
    borrowed = total - available - sold_count
    overdue_count = db.query(BorrowRecord).filter(BorrowRecord.status == 'overdue').count()
    upcoming_trial = db.query(Reminders).filter(
        Reminders.reminder_type == 'trial_period',
        Reminders.is_processed == False,
        Reminders.due_date >= TODAY,
        Reminders.due_date <= TODAY + timedelta(days=7)
    ).count()
    unset_iot_4g = db.query(Inventory).filter(
        Inventory.version == '4G',
        (Inventory.iot_card_status == None) | (Inventory.iot_card_status == '')
    ).count()

    # 属性分布
    attr_counts = db.query(Inventory.device_attribute, func.count(Inventory.id)).group_by(
        Inventory.device_attribute).all()
    attr_parts = [f"{a or '未分类'}{c}" for a, c in attr_counts[:6]]

    ctx = f"总{total}台 在库{available}台 借出{borrowed}台 已售{sold_count}台 逾期{overdue_count}台"
    if upcoming_trial:
        ctx += f" 试用到期待处理{upcoming_trial}台"
    if unset_iot_4g:
        ctx += f" 4G未设IoT卡{unset_iot_4g}台"
    if attr_parts:
        ctx += f" | 分布: {' '.join(attr_parts)}"
    return ctx
