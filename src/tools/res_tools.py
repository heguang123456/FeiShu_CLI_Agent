"""
资源整理工具模块
封装搜索消息、读写多维表格、搜索知识库的工具
"""

import json
import logging
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .lark_base import get_cli

logger = logging.getLogger(__name__)


class SearchMessagesInput(BaseModel):
    """搜索消息输入参数"""
    query: str = Field(description="搜索关键词")
    chat_id: Optional[str] = Field(default=None, description="指定群聊ID（可选）")
    start_time: Optional[str] = Field(default=None, description="开始时间，格式：2024-01-01（可选）")
    end_time: Optional[str] = Field(default=None, description="结束时间，格式：2024-01-01（可选）")
    count: int = Field(default=20, description="返回结果数量")


class GetChatMessagesInput(BaseModel):
    """获取群聊消息输入参数"""
    chat_id: str = Field(description="群聊ID")
    start_time: Optional[str] = Field(default=None, description="开始时间（可选）")
    end_time: Optional[str] = Field(default=None, description="结束时间（可选）")
    count: int = Field(default=50, description="返回消息数量")


class GetBitableRecordsInput(BaseModel):
    """获取多维表格记录输入参数"""
    app_token: str = Field(description="多维表格应用token")
    table_id: str = Field(description="数据表ID")
    filter_expr: Optional[str] = Field(default=None, description="过滤表达式（可选）")
    sort: Optional[str] = Field(default=None, description="排序表达式（可选）")
    count: int = Field(default=100, description="返回记录数量")


class CreateBitableRecordInput(BaseModel):
    """创建多维表格记录输入参数"""
    app_token: str = Field(description="多维表格应用token")
    table_id: str = Field(description="数据表ID")
    fields: Dict[str, Any] = Field(description="字段数据，格式为JSON对象")


class SearchKnowledgeBaseInput(BaseModel):
    """搜索知识库输入参数"""
    query: str = Field(description="搜索关键词")
    space_id: Optional[str] = Field(default=None, description="知识空间ID（可选）")
    count: int = Field(default=10, description="返回结果数量")


class GetKnowledgeArticleInput(BaseModel):
    """获取知识库文章输入参数"""
    node_token: str = Field(description="知识库节点token")


class GetMinutesInput(BaseModel):
    """获取妙记输入参数"""
    meeting_id: str = Field(description="会议ID")


class SearchMinutesInput(BaseModel):
    """搜索妙记输入参数"""
    query: str = Field(description="搜索关键词")
    start_time: Optional[str] = Field(default=None, description="开始时间（可选）")
    end_time: Optional[str] = Field(default=None, description="结束时间（可选）")
    count: int = Field(default=10, description="返回结果数量")


@tool(args_schema=SearchMessagesInput)
def search_messages(
    query: str,
    chat_id: str = None,
    start_time: str = None,
    end_time: str = None,
    count: int = 20
) -> str:
    """搜索飞书消息。
    
    当用户需要查找聊天记录、搜索群聊消息、寻找讨论内容时使用此工具。
    可以按关键词搜索，也可以指定群聊和时间范围。
    
    Args:
        query: 搜索关键词
        chat_id: 指定群聊ID（可选，不指定则搜索所有群聊）
        start_time: 开始时间，格式：2024-01-01（可选）
        end_time: 结束时间，格式：2024-01-01（可选）
        count: 返回结果数量（默认20）
    
    Returns:
        搜索到的消息列表
    """
    cli = get_cli()
    result = cli.search_messages(query, chat_id, start_time, end_time, count)
    
    if not result.success:
        return f"搜索消息失败: {result.error}"
    
    # 处理不同的返回格式
    data = result.data
    if isinstance(data, dict):
        messages = data.get("items", data.get("messages", []))
    elif isinstance(data, list):
        messages = data
    else:
        messages = []
    
    if not messages:
        return f"未找到与 '{query}' 相关的消息。"
    
    output_lines = [f"找到 {len(messages)} 条相关消息：\n"]
    
    for i, msg in enumerate(messages, 1):
        sender = msg.get("sender", {}).get("name", "未知")
        content = msg.get("content", "")
        chat_name = msg.get("chat_name", "")
        create_time = msg.get("create_time", "")
        
        output_lines.append(f"{i}. [{chat_name}] {sender}")
        if create_time:
            output_lines.append(f"   时间: {create_time}")
        output_lines.append(f"   内容: {content}")
        output_lines.append("")
    
    return "\n".join(output_lines)


@tool(args_schema=GetChatMessagesInput)
def get_chat_messages(
    chat_id: str,
    start_time: str = None,
    end_time: str = None,
    count: int = 50
) -> str:
    """获取群聊的历史消息。
    
    当用户需要查看某个群聊的聊天记录、了解群内讨论内容时使用此工具。
    
    Args:
        chat_id: 群聊ID
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        count: 返回消息数量（默认50）
    
    Returns:
        群聊消息列表
    """
    cli = get_cli()
    result = cli.get_chat_messages(chat_id, start_time, end_time, count)
    
    if not result.success:
        return f"获取群聊消息失败: {result.error}"
    
    # 处理不同的返回格式
    data = result.data
    if isinstance(data, dict):
        messages = data.get("items", data.get("messages", []))
    elif isinstance(data, list):
        messages = data
    else:
        messages = []
    
    if not messages:
        return "该群聊暂无消息。"
    
    output_lines = [f"群聊消息（共 {len(messages)} 条）：\n"]
    
    for msg in messages:
        sender = msg.get("sender", {}).get("name", "未知")
        content = msg.get("content", "")
        create_time = msg.get("create_time", "")
        
        output_lines.append(f"[{create_time}] {sender}: {content}")
    
    return "\n".join(output_lines)


@tool(args_schema=GetBitableRecordsInput)
def read_bitable(
    app_token: str,
    table_id: str,
    filter_expr: str = None,
    sort: str = None,
    count: int = 100
) -> str:
    """读取多维表格的数据记录。
    
    当用户需要查看多维表格内容、获取表格数据、分析表格记录时使用此工具。
    
    Args:
        app_token: 多维表格应用token
        table_id: 数据表ID
        filter_expr: 过滤表达式（可选，如：'CurrentValue.[状态]="已完成"'）
        sort: 排序表达式（可选）
        count: 返回记录数量（默认100）
    
    Returns:
        表格记录数据
    """
    cli = get_cli()
    result = cli.get_bitable_records(app_token, table_id, filter_expr, sort, count)
    
    if not result.success:
        return f"读取多维表格失败: {result.error}"
    
    # 处理不同的返回格式
    data = result.data
    if isinstance(data, dict):
        records = data.get("items", data.get("records", []))
    elif isinstance(data, list):
        records = data
    else:
        records = []
    
    if not records:
        return "未找到符合条件的记录。"
    
    output_lines = [f"多维表格记录（共 {len(records)} 条）：\n"]
    
    for i, record in enumerate(records, 1):
        record_id = record.get("record_id", "未知")
        fields = record.get("fields", {})
        
        output_lines.append(f"记录 {i} (ID: {record_id}):")
        for field_name, field_value in fields.items():
            # 处理不同类型的字段值
            if isinstance(field_value, list):
                field_value = ", ".join(str(v) for v in field_value)
            elif isinstance(field_value, dict):
                field_value = json.dumps(field_value, ensure_ascii=False)
            output_lines.append(f"  {field_name}: {field_value}")
        output_lines.append("")
    
    return "\n".join(output_lines)


@tool(args_schema=CreateBitableRecordInput)
def write_bitable(app_token: str, table_id: str, fields: Dict[str, Any]) -> str:
    """向多维表格写入新记录。
    
    当用户需要添加表格数据、创建新记录、写入多维表格时使用此工具。
    
    Args:
        app_token: 多维表格应用token
        table_id: 数据表ID
        fields: 字段数据，格式为JSON对象，如：{"标题": "xxx", "状态": "进行中"}
    
    Returns:
        创建结果
    """
    cli = get_cli()
    result = cli.create_bitable_record(app_token, table_id, fields)
    
    if not result.success:
        return f"写入多维表格失败: {result.error}"
    
    record_info = result.data
    record_id = record_info.get("record_id", "未知")
    
    return f"记录创建成功！记录ID: {record_id}"


@tool(args_schema=SearchKnowledgeBaseInput)
def search_knowledge_base(
    query: str,
    space_id: str = None,
    count: int = 10
) -> str:
    """搜索飞书知识库。
    
    当用户需要查找知识库文章、搜索文档资料、获取知识库内容时使用此工具。
    
    Args:
        query: 搜索关键词
        space_id: 知识空间ID（可选，不指定则搜索所有知识库）
        count: 返回结果数量（默认10）
    
    Returns:
        搜索到的知识库文章列表
    """
    cli = get_cli()
    result = cli.search_knowledge_base(query, space_id, count)
    
    if not result.success:
        return f"搜索知识库失败: {result.error}"
    
    # 处理不同的返回格式
    data = result.data
    if isinstance(data, dict):
        articles = data.get("items", data.get("articles", []))
    elif isinstance(data, list):
        articles = data
    else:
        articles = []
    
    if not articles:
        return f"未找到与 '{query}' 相关的知识库文章。"
    
    output_lines = [f"找到 {len(articles)} 篇相关文章：\n"]
    
    for i, article in enumerate(articles, 1):
        title = article.get("title", "无标题")
        node_token = article.get("node_token", "")
        space_name = article.get("space_name", "")
        update_time = article.get("update_time", "")
        
        output_lines.append(f"{i}. {title}")
        if space_name:
            output_lines.append(f"   知识空间: {space_name}")
        if node_token:
            output_lines.append(f"   节点token: {node_token}")
        if update_time:
            output_lines.append(f"   更新时间: {update_time}")
        output_lines.append("")
    
    return "\n".join(output_lines)


@tool(args_schema=GetKnowledgeArticleInput)
def get_knowledge_article(node_token: str) -> str:
    """获取知识库文章的详细内容。
    
    当用户需要阅读某篇知识库文章、获取文章全文时使用此工具。
    
    Args:
        node_token: 知识库节点token
    
    Returns:
        文章内容
    """
    cli = get_cli()
    result = cli.get_knowledge_article(node_token)
    
    if not result.success:
        return f"获取知识库文章失败: {result.error}"
    
    article = result.data
    title = article.get("title", "无标题")
    content = article.get("content", "暂无内容")
    
    return f"# {title}\n\n{content}"


@tool(args_schema=GetMinutesInput)
def get_minutes_transcript(meeting_id: str) -> str:
    """获取飞书妙记的逐字稿。
    
    当用户需要查看会议记录、获取会议逐字稿、了解会议内容时使用此工具。
    
    Args:
        meeting_id: 会议ID
    
    Returns:
        会议逐字稿内容
    """
    cli = get_cli()
    result = cli.get_minutes(meeting_id)
    
    if not result.success:
        return f"获取妙记逐字稿失败: {result.error}"
    
    minutes = result.data
    meeting_title = minutes.get("title", "未知会议")
    transcript = minutes.get("transcript", "")
    
    return f"# {meeting_title} - 逐字稿\n\n{transcript}"


@tool(args_schema=SearchMinutesInput)
def search_minutes(
    query: str,
    start_time: str = None,
    end_time: str = None,
    count: int = 10
) -> str:
    """搜索飞书妙记。
    
    当用户需要查找会议记录、搜索会议内容、寻找某次会议的讨论时使用此工具。
    
    Args:
        query: 搜索关键词
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        count: 返回结果数量（默认10）
    
    Returns:
        搜索到的妙记列表
    """
    cli = get_cli()
    result = cli.search_minutes(query, start_time, end_time, count)
    
    if not result.success:
        return f"搜索妙记失败: {result.error}"
    
    # 处理不同的返回格式
    data = result.data
    if isinstance(data, dict):
        minutes_list = data.get("items", data.get("minutes", []))
    elif isinstance(data, list):
        minutes_list = data
    else:
        minutes_list = []
    
    if not minutes_list:
        return f"未找到与 '{query}' 相关的妙记。"
    
    output_lines = [f"找到 {len(minutes_list)} 条相关妙记：\n"]
    
    for i, minutes in enumerate(minutes_list, 1):
        title = minutes.get("title", "未知会议")
        meeting_id = minutes.get("meeting_id", "")
        start_time = minutes.get("start_time", "")
        duration = minutes.get("duration", "")
        
        output_lines.append(f"{i}. {title}")
        if meeting_id:
            output_lines.append(f"   会议ID: {meeting_id}")
        if start_time:
            output_lines.append(f"   开始时间: {start_time}")
        if duration:
            output_lines.append(f"   时长: {duration}")
        output_lines.append("")
    
    return "\n".join(output_lines)


# 工具列表，用于注册到Agent
RESOURCE_TOOLS = [
    search_messages,
    get_chat_messages,
    read_bitable,
    write_bitable,
    search_knowledge_base,
    get_knowledge_article,
    get_minutes_transcript,
    search_minutes,
]