from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import logging.handlers
import traceback
import os
import sys

from database import engine, Base, get_db
from routers import inventory, borrow, ai, dashboard, reminders, analysis, auth, reservation


def setup_logging():
    """配置结构化日志系统：控制台 + 文件双通道"""
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return logging.getLogger(__name__)


logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在初始化数据库表...")
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")
    yield
    logger.info("应用关闭")


app = FastAPI(title="智能库存管理系统", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "detail": str(exc.detail)},
    )


@app.middleware("http")
async def global_exception_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"未捕获异常 [{request.method} {request.url.path}]: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": "服务器内部错误", "detail": str(e)}
        )


# 注册路由
app.include_router(inventory.router)
app.include_router(borrow.router)
app.include_router(ai.router)
app.include_router(dashboard.router)
app.include_router(reminders.router)
app.include_router(analysis.router)
app.include_router(auth.router)
app.include_router(reservation.router)


@app.get("/operation-logs")
def get_operation_logs(
    operation_type: str = None,
    username: str = None,
    skip: int = 0, limit: int = 100,
    db=Depends(get_db)
):
    from crud import get_operation_logs
    return get_operation_logs(db, operation_type=operation_type, username=username, skip=skip, limit=limit)


@app.get("/")
async def root():
    return {"message": "智能库存管理系统 API v2.0", "status": "running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
