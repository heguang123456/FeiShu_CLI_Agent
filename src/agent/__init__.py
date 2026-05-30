"""
Agent核心大脑模块
负责任务拆解、意图识别、路由分发和上下文管理
"""

from .brain import NoteAgent
from .prompts import get_system_prompt

__all__ = ["NoteAgent", "get_system_prompt"]