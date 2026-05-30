"""
Agent核心大脑模块
负责任务拆解、意图识别、路由分发和上下文管理
"""

import logging
from typing import List, Optional, Dict, Any, AsyncIterator
from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.agents import create_agent

from ..config.settings import get_settings
from ..tools.note_tools import NOTE_TOOLS
from ..tools.res_tools import RESOURCE_TOOLS
from ..rag.vector_store import RAG_TOOLS
from ..storage.chat_history import get_chat_history_manager
from .prompts import get_chat_prompt

logger = logging.getLogger(__name__)


class NoteAgent:
    """笔记智能体"""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = self._create_llm()
        self.tools = self._load_tools()
        self.system_prompt = self._get_system_prompt()
        self.agent = self._create_agent()
        self.chat_histories: Dict[str, InMemoryChatMessageHistory] = {}
        self.chat_store = get_chat_history_manager()
    
    def _create_llm(self):
        """根据配置创建LLM实例，支持多提供商路由"""
        provider = self.settings.llm_provider
        logger.info(f"LLM提供商: {provider}")
        
        if provider == "anthropic":
            if not self.settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY 未配置")
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=self.settings.anthropic_model_name,
                anthropic_api_key=self.settings.anthropic_api_key,
                temperature=0.7,
                streaming=True,
            )
        
        elif provider == "zhipuai":
            if not self.settings.zhipuai_api_key:
                raise ValueError("ZHIPUAI_API_KEY 未配置")
            return ChatOpenAI(
                model=self.settings.zhipuai_model_name,
                openai_api_key=self.settings.zhipuai_api_key,
                openai_api_base="https://open.bigmodel.cn/api/paas/v4",
                temperature=0.7,
                streaming=True,
            )
        
        else:  # openai 及兼容 API
            return ChatOpenAI(
                model=self.settings.openai_model_name,
                openai_api_key=self.settings.openai_api_key,
                openai_api_base=self.settings.openai_api_base,
                temperature=0.7,
                streaming=True,
            )
    
    def _load_tools(self) -> List:
        """加载所有工具"""
        tools = []
        
        # 添加笔记工具
        tools.extend(NOTE_TOOLS)
        logger.info(f"加载笔记工具: {len(NOTE_TOOLS)} 个")
        
        # 添加资源工具
        tools.extend(RESOURCE_TOOLS)
        logger.info(f"加载资源工具: {len(RESOURCE_TOOLS)} 个")
        
        # 添加RAG工具
        tools.extend(RAG_TOOLS)
        logger.info(f"加载RAG工具: {len(RAG_TOOLS)} 个")
        
        logger.info(f"总共加载 {len(tools)} 个工具")
        return tools
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        from .prompts import get_system_prompt
        return get_system_prompt()
    
    def _create_agent(self):
        """创建Agent"""
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt,
        )
    
    def _get_chat_history(self, session_id: str) -> InMemoryChatMessageHistory:
        """获取或创建会话历史（优先从 SQLite 加载）"""
        if session_id not in self.chat_histories:
            history = InMemoryChatMessageHistory()
            persisted = self.chat_store.get_messages(session_id)
            if persisted:
                history.messages = persisted
                logger.info(f"从 SQLite 加载会话历史: {session_id} ({len(persisted)} 条)")
            self.chat_histories[session_id] = history
        return self.chat_histories[session_id]
    
    def _save_to_store(self, session_id: str, user_input: str, output: str):
        """将对话保存到 SQLite"""
        self.chat_store.add_message(session_id, "user", user_input)
        self.chat_store.add_message(session_id, "assistant", output)
    
    def _estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数量（中文约 1.5 token/字，英文约 0.75 token/word）"""
        import re
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.4)
    
    def _trim_messages(self, messages: List) -> List:
        """根据 token 预算裁剪历史消息，保留最近的对话"""
        max_tokens = self.settings.max_history_tokens
        total_tokens = 0
        trimmed = []
        
        for msg in reversed(messages):
            content = msg.content if hasattr(msg, 'content') else str(msg)
            msg_tokens = self._estimate_tokens(content)
            if total_tokens + msg_tokens > max_tokens and trimmed:
                break
            trimmed.append(msg)
            total_tokens += msg_tokens
        
        trimmed.reverse()
        if len(trimmed) < len(messages):
            logger.info(f"历史消息裁剪: {len(messages)} → {len(trimmed)} 条 (约 {total_tokens} tokens)")
        return trimmed
    
    def run(
        self,
        user_input: str,
        session_id: str = "default",
        stream: bool = False
    ) -> str:
        """
        执行用户指令
        
        Args:
            user_input: 用户输入
            session_id: 会话ID
            stream: 是否流式输出
        
        Returns:
            Agent的回复
        """
        logger.info(f"用户输入: {user_input}")
        
        # 获取会话历史
        chat_history = self._get_chat_history(session_id)
        
        # 准备输入消息（带 token 裁剪）
        messages = self._trim_messages(list(chat_history.messages))
        messages.append(HumanMessage(content=user_input))
        
        try:
            # 执行Agent
            result = self.agent.invoke({"messages": messages})
            
            # 获取回复（从result中提取最后一条AI消息）
            output = ""
            if hasattr(result, 'messages') and result.messages:
                last_message = result.messages[-1]
                if hasattr(last_message, 'content'):
                    output = last_message.content
            
            # 保存到会话历史
            chat_history.add_user_message(user_input)
            chat_history.add_ai_message(output)
            self._save_to_store(session_id, user_input, output)
            
            logger.info(f"Agent回复: {output[:100]}...")
            return output
            
        except Exception as e:
            error_msg = f"执行出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
    
    async def arun(
        self,
        user_input: str,
        session_id: str = "default"
    ) -> str:
        """
        异步执行用户指令
        
        Args:
            user_input: 用户输入
            session_id: 会话ID
        
        Returns:
            Agent的回复
        """
        logger.info(f"用户输入: {user_input}")
        
        chat_history = self._get_chat_history(session_id)
        
        # 准备输入消息（带 token 裁剪）
        messages = self._trim_messages(list(chat_history.messages))
        messages.append(HumanMessage(content=user_input))
        
        try:
            result = await self.agent.ainvoke({"messages": messages})
            
            # 获取回复
            output = ""
            if hasattr(result, 'messages') and result.messages:
                last_message = result.messages[-1]
                if hasattr(last_message, 'content'):
                    output = last_message.content
            
            chat_history.add_user_message(user_input)
            chat_history.add_ai_message(output)
            self._save_to_store(session_id, user_input, output)
            
            logger.info(f"Agent回复: {output[:100]}...")
            return output
            
        except Exception as e:
            error_msg = f"执行出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
    
    async def astream(
        self,
        user_input: str,
        session_id: str = "default"
    ) -> AsyncIterator[str]:
        """
        流式执行用户指令
        
        Args:
            user_input: 用户输入
            session_id: 会话ID
        
        Yields:
            Agent的回复片段
        """
        logger.info(f"用户输入（流式）: {user_input}")
        
        chat_history = self._get_chat_history(session_id)
        
        # 准备输入消息（带 token 裁剪）
        messages = self._trim_messages(list(chat_history.messages))
        messages.append(HumanMessage(content=user_input))
        
        full_output = ""
        tool_started = False
        
        try:
            async for event in self.agent.astream_events({"messages": messages}, version="v2"):
                kind = event.get("event", "")
                
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", None)
                    content = ""
                    if chunk and hasattr(chunk, 'content'):
                        content = chunk.content
                    elif chunk and isinstance(chunk, str):
                        content = chunk
                    if content:
                        full_output += content
                        yield content
                        
                elif kind == "on_tool_start":
                    if not tool_started:
                        tool_name = event.get("name", "")
                        yield f"\x00TOOL_START:{tool_name}"
                        tool_started = True
                    
                elif kind == "on_tool_end":
                    yield "\x00TOOL_END"
                    tool_started = False
            
            # 保存到会话历史
            chat_history.add_user_message(user_input)
            chat_history.add_ai_message(full_output)
            self._save_to_store(session_id, user_input, full_output)
            
        except Exception as e:
            error_msg = f"\n执行出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            yield error_msg
    
    def clear_history(self, session_id: str = "default"):
        """清除会话历史"""
        if session_id in self.chat_histories:
            del self.chat_histories[session_id]
            logger.info(f"清除会话历史: {session_id}")
    
    def get_history(self, session_id: str = "default") -> List[Dict[str, str]]:
        """获取会话历史"""
        chat_history = self._get_chat_history(session_id)
        
        history = []
        for msg in chat_history.messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        
        return history
    
    def get_tool_descriptions(self) -> List[Dict[str, str]]:
        """获取所有工具的描述"""
        descriptions = []
        
        for tool in self.tools:
            descriptions.append({
                "name": tool.name,
                "description": tool.description,
            })
        
        return descriptions


# 全局Agent实例
_agent_instance = None


def get_agent() -> NoteAgent:
    """获取Agent单例"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = NoteAgent()
    return _agent_instance