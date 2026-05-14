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

## 当前状态
日期: {TODAY} ({TODAY_WEEKDAY})
库存: {total} 台设备 | 可用: {available} | 逾期: {overdue_count}

## 核心规则
1. 用户让你做什么，你就调用工具去做。操作类工具会直接修改数据库。
2. 查询类工具返回数据后，你要把数据解读成自然语言告诉用户，不要只重复原始数据。
3. 如果操作失败，如实告诉用户原因，并建议替代方案。
4. 用中文回复，简洁专业，像同事对话一样。

## 日期处理
今天是 {TODAY}。用户说的"5月6日"就是 {TODAY.year}-05-06，"下周X"需要推算。不确定的日期用 resolve_date 工具。
"""


def build_system_context(db) -> str:
    """实时系统上下文（每次请求更新）"""
    from models import Inventory, BorrowRecord, Reminders

    total = db.query(Inventory).count()
    available = db.query(Inventory).filter(Inventory.borrower == None).count()
    overdue_count = db.query(BorrowRecord).filter(BorrowRecord.status == 'overdue').count()
    upcoming_trial = db.query(Reminders).filter(
        Reminders.reminder_type == 'trial_period',
        Reminders.is_processed == False,
        Reminders.due_date >= TODAY,
        Reminders.due_date <= TODAY + timedelta(days=7)
    ).count()

    ctx = f"当前: 总{total}台 可用{available}台 逾期{overdue_count}台"
    if upcoming_trial:
        ctx += f" 试用到期待处理{upcoming_trial}台"
    return ctx
