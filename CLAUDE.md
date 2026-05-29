# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Custom Slash Commands

| 命令 | 作用 |
|------|------|
| `/check` | 快速健康检查：后端导入、前端编译、登录、6个核心API |
| `/sync-test` | 完整端到端测试：重启服务→配置生产库→刷新设备→工单流转 |
| `/status` | 项目状态一览：代码、数据库、服务运行状态 |

## Automated Hooks

- **SessionStart**: 每次新会话自动显示 git 分支/变更/路由数
- **PostToolUse**: 每次编辑 `.py` 文件后自动语法检查

## Project Overview

AI-powered inventory management system (智能库存管理系统) for managing device inventory with natural language AI commands. Built with FastAPI + Vue 3 + MySQL, using DashScope (阿里云通义千问) for AI Function Calling.

## Commands

### Backend (Python/FastAPI)

```bash
# Install dependencies
cd backend && pip install -r requirements.txt

# Start the backend server (port 8000)
cd backend && python main.py

# Initialize MySQL database and tables with sample data
cd backend && python init_mysql_db.py
```

### Frontend (Vue 3/Vite)

```bash
# Install dependencies
cd frontend && npm install

# Start dev server (port 3000, proxies /api → backend :8000)
cd frontend && npm run dev

# Build for production
cd frontend && npm run build
```

### Docker

```bash
docker-compose up -d   # Starts MySQL + backend + frontend
```

### Testing

Tests are standalone Python scripts in `backend/` — run directly:
```bash
cd backend && python test_api.py
cd backend && python test_db.py
cd backend && python test_smart_ai.py
```

## Architecture

### Backend (`backend/`)

- **`main.py`** — FastAPI app with ALL API routes (inventory CRUD, import/export, reminders, AI chat/execute, dashboard stats, borrow records). Routes do NOT have `/api` prefix — the Vite dev proxy strips it.
- **`database.py`** — SQLAlchemy engine, `SessionLocal`, and `Base` declarative base. Uses `pydantic-settings` to read `DATABASE_URL` from `.env`. Creates tables via `Base.metadata.create_all()`.
- **`models.py`** — ORM models: `Inventory` (inventory table), `Reminders`, `AILogs`, `BorrowRecord` (borrow_records table). All extend `Base` from `database.py`.
- **`schemas.py`** — Pydantic models: `InventoryCreate`, `InventoryUpdate`, `InventoryResponse`, `ReminderCreate`/`ReminderResponse`, `AIParseRequest`/`AIParseResponse`, `DashboardStats`, `BorrowRecordCreate`/`BorrowRecordReturn`/`BorrowRecordResponse`.
- **`crud.py`** — All DB operations: inventory CRUD, reminder CRUD, AI log creation, dashboard stats aggregation, borrow record CRUD with overdue tracking.
- **`smart_ai.py`** — The main AI module. Defines 8 function-calling tools (create_inventory, batch_create_inventory, batch_create_inventory_range, update_inventory, delete_inventory, create_borrow, return_borrow, sell_device). Calls DashScope API via raw HTTP requests. Manages per-user conversation history in memory. Also includes `detect_anomalies()` and `get_inventory_analysis()` for analytics.
- **`ai_parser.py`** — Legacy keyword-based command parser (not used by the main AI flow, kept for compatibility).
- **`ai_settings.py`** — Reads `DASHSCOPE_API_KEY` from `.env` via pydantic-settings.
- **`app.py`** / **`db.py`** — Flask-based legacy modules, separate from the FastAPI app. Contain Flask routes and Flask-SQLAlchemy config. Not used by the main application.

### Frontend (`frontend/src/`)

- **`App.vue`** — Root component with sidebar navigation (6 pages: Dashboard, Inventory, BorrowManagement, AIAssistant, Reminders, Analytics) and conditional rendering via `v-if`.
- **`api/index.js`** — Axios instance (`/api` base URL) and all API methods grouped by domain: `inventoryAPI`, `reminderAPI`, `aiAPI`, `dashboardAPI`, `borrowAPI`.
- **`main.js`** — Creates Vue app, registers Element Plus and all icons globally.
- Components: `Dashboard.vue`, `Inventory.vue`, `BorrowManagement.vue`, `AIAssistant.vue`, `Reminders.vue`, `Analytics.vue`.

### Database

Tables: `inventory` (device records), `reminders` (trial/IoT card reminders), `ai_logs` (AI operation audit), `borrow_records` (device borrowing with status tracking).

MySQL is the primary database (configured via `DATABASE_URL`). SQLite init scripts exist as fallbacks but are not the main path.

### AI Flow

1. User types natural language in the AI Assistant UI
2. Frontend calls `POST /ai/chat` with `{user_input: "..."}` (60s timeout)
3. `smart_ai.py` sends conversation history + system instructions + tool definitions to DashScope API
4. AI returns either a text response or a tool call (function name + arguments)
5. If a tool call is returned, the frontend shows a confirmation dialog
6. User confirms → frontend calls `POST /ai/execute-action` with `{action, params, user_input}`
7. Backend executes the operation and logs it to `ai_logs`

### Key Details

- **Vite proxy**: In dev mode, `/api/*` requests are proxied to `http://127.0.0.1:8000` with the `/api` prefix stripped. This means the backend routes are bare (e.g., `/inventory`, `/ai/chat`), not `/api/inventory`.
- **Environment**: Copy `backend/.env.example` to `backend/.env` and set `DASHSCOPE_API_KEY` for AI features. Database URL defaults to `mysql+pymysql://root:123456@localhost/inventory_db`.
- **Enum values**: `version` = `WiFi` | `4G`, `type` = `睡眠` | `跌倒`, `packaging` = `简约` | `精品`, `device_attribute` values are Chinese strings defined in `models.py`.
- **CSV import/export**: Import expects Chinese column headers matching the inventory fields. Export generates CSV with UTF-8 BOM.
- **Borrow lifecycle**: `borrowed` → `overdue` (auto, if past `expected_return_date`) → `returned`. There's also a `terminated` status for forced returns.
