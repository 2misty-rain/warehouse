"""AI 工具集: 工厂函数 get_all_tools(db) 返回 db 绑定的 LangChain Tools"""
from .inventory import make_inventory_tools
from .borrow import make_borrow_tools
from .sales import make_sales_tools
from .reports import make_report_tools
from .assign import make_assign_tools
from .iot import make_iot_tools
from .lifecycle import make_lifecycle_tools
from .date_utils import make_date_tools
from .reminder_tools import make_reminder_tools
from .reservation_tools import make_reservation_tools
from .alert_tools import make_alert_tools


def get_all_tools(db) -> list:
    """返回所有 db 绑定的 LangChain Tools (共19个)"""
    tools = []
    tools.extend(make_inventory_tools(db))
    tools.extend(make_borrow_tools(db))
    tools.extend(make_sales_tools(db))
    tools.extend(make_report_tools(db))
    tools.extend(make_assign_tools(db))
    tools.extend(make_iot_tools(db))
    tools.extend(make_lifecycle_tools(db))
    tools.extend(make_date_tools(db))
    tools.extend(make_reminder_tools(db))
    tools.extend(make_reservation_tools(db))
    tools.extend(make_alert_tools(db))
    return tools
