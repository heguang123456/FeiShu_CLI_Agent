"""
配置管理模块
基于pydantic-settings管理环境变量和配置
"""

import os
from pathlib import Path
from typing import Optional, Literal
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class Settings(BaseSettings):
    """应用配置"""
    
    # ==================== LLM配置 ====================
    llm_provider: Literal["openai", "anthropic", "zhipuai"] = Field("openai", env="LLM_PROVIDER")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_api_base: str = Field("https://api.openai.com/v1", env="OPENAI_API_BASE")
    openai_model_name: str = Field("gpt-4-turbo", env="OPENAI_MODEL_NAME")
    
    # 其他LLM提供商（可选）
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    anthropic_model_name: str = Field("claude-3-sonnet-20240229", env="ANTHROPIC_MODEL_NAME")
    zhipuai_api_key: Optional[str] = Field(None, env="ZHIPUAI_API_KEY")
    zhipuai_model_name: str = Field("glm-4", env="ZHIPUAI_MODEL_NAME")
    
    # ==================== 飞书配置 ====================
    feishu_app_id: Optional[str] = Field(None, env="FEISHU_APP_ID")
    feishu_app_secret: Optional[str] = Field(None, env="FEISHU_APP_SECRET")
    mock_mode: bool = Field(False, env="MOCK_MODE")
    
    # ==================== RAG配置 ====================
    vector_store_path: str = Field("./data/vector_store", env="VECTOR_STORE_PATH")
    embedding_model: str = Field("text-embedding-3-small", env="EMBEDDING_MODEL")
    chunk_size: int = Field(1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(200, env="CHUNK_OVERLAP")
    
    # ==================== 会话配置 ====================
    max_history_tokens: int = Field(4000, env="MAX_HISTORY_TOKENS")
    
    # ==================== 日志配置 ====================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("./logs/noteagent.log", env="LOG_FILE")
    
    # ==================== 项目路径 ====================
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @field_validator("vector_store_path", "log_file", mode="before")
    @classmethod
    def resolve_path(cls, v, info):
        """将相对路径转换为绝对路径"""
        if isinstance(v, str) and not os.path.isabs(v):
            project_root = cls.model_config.get("project_root", Path.cwd())
            return str(project_root / v)
        return v
    
    def get_llm_config(self) -> dict:
        """获取LLM配置"""
        return {
            "api_key": self.openai_api_key,
            "base_url": self.openai_api_base,
            "model": self.openai_model_name,
        }
    
    def get_vector_store_config(self) -> dict:
        """获取向量存储配置"""
        return {
            "path": self.vector_store_path,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
        }
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        Path(self.vector_store_path).mkdir(parents=True, exist_ok=True)
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    # 加载.env文件
    load_dotenv()
    
    # 创建配置
    settings = Settings()
    
    # 确保目录存在
    settings.ensure_directories()
    
    return settings


class FeishuAuthError(Exception):
    """飞书认证错误"""
    pass


class FeishuAPIError(Exception):
    """飞书API错误"""
    
    def __init__(self, message: str, code: int = None, solution: str = None):
        self.code = code
        self.solution = solution
        super().__init__(message)
    
    def __str__(self):
        base = super().__str__()
        if self.solution:
            return f"{base}\n解决方案: {self.solution}"
        return base


def handle_feishu_error(error: Exception) -> str:
    """处理飞书CLI错误"""
    error_msg = str(error)
    
    # Token过期
    if "token" in error_msg.lower() and ("expired" in error_msg.lower() or "invalid" in error_msg.lower()):
        raise FeishuAuthError(
            "飞书认证Token已过期或无效。"
            "请执行 'lark-cli auth login' 重新登录。"
        )
    
    # 权限不足
    if "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
        raise FeishuAPIError(
            "权限不足，无法执行此操作。",
            solution="请检查飞书应用权限配置，确保已授权相关API。"
        )
    
    # 命令不存在
    if "command not found" in error_msg.lower() or "not recognized" in error_msg.lower():
        raise FeishuAPIError(
            "lark-cli命令未找到。",
            solution="请确保已安装飞书CLI并添加到系统PATH。"
            "安装指南: https://github.com/larksuite/cli"
        )
    
    # 其他错误
    raise FeishuAPIError(f"飞书CLI执行失败: {error_msg}")