# Import all tool modules to trigger @register decorators
# These must come AFTER tool_registry is defined
from . import inventory, borrow, sales, assign, iot, reports, lifecycle, date_utils  # noqa
