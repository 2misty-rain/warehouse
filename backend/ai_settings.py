from pydantic_settings import BaseSettings
from typing import Optional


class AISettings(BaseSettings):
    """AI配置设置"""
    dashscope_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# 创建全局实例
ai_settings = AISettings()
