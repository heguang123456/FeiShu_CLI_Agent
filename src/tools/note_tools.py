"""
笔记记录工具模块
封装创建云文档、更新正文、追加内容的工具
"""

import logging
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .lark_base import get_cli

logger = logging.getLogger(__name__)


class CreateDocumentInput(BaseModel):
    """创建文档输入参数"""
    title: str = Field(description="文档标题")
    content: str = Field(default="", description="文档初始内容（可选）")
    folder_token: Optional[str] = Field(default=None, description="目标文件夹token（可选）")


class GetDocumentInput(BaseModel):
    """获取文档输入参数"""
    document_id: str = Field(description="文档ID")


class UpdateDocumentInput(BaseModel):
    """更新文档输入参数"""
    document_id: str = Field(description="文档ID")
    content: str = Field(description="新的文档内容")


class AppendToDocumentInput(BaseModel):
    """追加文档内容输入参数"""
    document_id: str = Field(description="文档ID")
    content: str = Field(description="要追加的内容")


class DeleteDocumentInput(BaseModel):
    """删除文档输入参数"""
    document_id: str = Field(description="文档ID")
    confirm: bool = Field(default=False, description="是否确认删除（必须先确认再删除）")


class SearchDocumentInput(BaseModel):
    """搜索文档输入参数"""
    query: str = Field(description="搜索关键词")
    count: int = Field(default=10, description="返回结果数量")


@tool(args_schema=CreateDocumentInput)
def create_document(title: str, content: str = "", folder_token: str = None) -> str:
    """创建新的飞书云文档。
    
    当用户需要创建新文档、新建笔记、写入新内容时使用此工具。
    返回创建的文档ID和访问链接。
    
    Args:
        title: 文档标题
        content: 文档初始内容（可选）
        folder_token: 目标文件夹token（可选，不指定则创建在根目录）
    
    Returns:
        创建结果，包含文档ID和链接
    """
    cli = get_cli()
    result = cli.create_document(title, folder_token)
    
    if not result.success:
        return f"创建文档失败: {result.error}"
    
    doc_info = result.data
    
    # 如果有初始内容，追加内容
    if content and doc_info.get("document_id"):
        doc_id = doc_info["document_id"]
        update_result = cli.update_document(doc_id, content)
        if not update_result.success:
            return f"文档已创建，但写入内容失败: {update_result.error}"
    
    return f"""文档创建成功！
文档ID: {doc_info.get('document_id', '未知')}
标题: {title}
链接: {doc_info.get('url', '未知')}
    
您可以使用此文档ID来更新或追加内容。"""


@tool(args_schema=GetDocumentInput)
def get_document(document_id: str) -> str:
    """获取飞书云文档的内容。
    
    当用户需要查看文档内容、读取文档全文、获取文档详情时使用此工具。
    
    Args:
        document_id: 文档ID
    
    Returns:
        文档内容，包含标题和正文
    """
    cli = get_cli()
    result = cli.get_document(document_id)
    
    if not result.success:
        return f"获取文档失败: {result.error}"
    
    doc_info = result.data
    title = doc_info.get("title", "无标题")
    content = doc_info.get("content", "暂无内容")
    
    return f"# {title}\n\n{content}"


@tool(args_schema=UpdateDocumentInput)
def update_document(document_id: str, content: str) -> str:
    """更新飞书云文档的内容。
    
    当用户需要修改文档内容、重写文档、更新笔记时使用此工具。
    这会完全替换文档的现有内容。
    
    Args:
        document_id: 文档ID
        content: 新的文档内容（将替换原有内容）
    
    Returns:
        更新结果
    """
    cli = get_cli()
    result = cli.update_document(document_id, content)
    
    if not result.success:
        return f"更新文档失败: {result.error}"
    
    return f"文档更新成功！文档ID: {document_id}"


@tool(args_schema=AppendToDocumentInput)
def append_to_document(document_id: str, content: str) -> str:
    """向飞书云文档追加内容。
    
    当用户需要在现有文档末尾添加内容、补充笔记、追加新段落时使用此工具。
    这不会覆盖原有内容，而是在末尾追加。
    
    Args:
        document_id: 文档ID
        content: 要追加的内容
    
    Returns:
        追加结果
    """
    cli = get_cli()
    result = cli.append_to_document(document_id, content)
    
    if not result.success:
        return f"追加内容失败: {result.error}"
    
    return f"内容追加成功！文档ID: {document_id}"


@tool(args_schema=DeleteDocumentInput)
def delete_document(document_id: str, confirm: bool = False) -> str:
    """删除飞书云文档。
    
    当用户需要删除文档、移除笔记、清理无用文档时使用此工具。
    注意：删除操作不可撤销，请先确认用户意图后再执行。
    
    ⚠️ 必须分两步执行：
    1. 第一次调用时 confirm=false，工具会返回确认提示
    2. 向用户确认意图后，再次调用 confirm=true 才会真正删除
    
    Args:
        document_id: 文档ID
        confirm: 是否确认删除（默认false，必须用户确认后设为true）
    
    Returns:
        删除结果或确认提示
    """
    if not confirm:
        return (
            f"⚠️ 即将删除文档 {document_id}，此操作不可撤销！\n"
            f"请向用户确认是否真的要删除，如果用户确认，请再次调用此工具并将 confirm 设为 true。"
        )
    
    cli = get_cli()
    result = cli.delete_document(document_id)
    
    if not result.success:
        return f"删除文档失败: {result.error}"
    
    return f"文档删除成功！文档ID: {document_id}"


@tool(args_schema=SearchDocumentInput)
def search_documents(query: str, count: int = 10) -> str:
    """搜索飞书云文档。
    
    当用户需要查找文档、搜索笔记、寻找相关资料时使用此工具。
    
    Args:
        query: 搜索关键词
        count: 返回结果数量（默认10）
    
    Returns:
        搜索结果列表
    """
    cli = get_cli()
    result = cli.search_documents(query, count)
    
    if not result.success:
        return f"搜索文档失败: {result.error}"
    
    # 处理不同的返回格式
    data = result.data
    if isinstance(data, dict):
        documents = data.get("items", data.get("documents", []))
    elif isinstance(data, list):
        documents = data
    else:
        documents = []
    
    if not documents:
        return f"未找到与 '{query}' 相关的文档。"
    
    output_lines = [f"找到 {len(documents)} 个相关文档：\n"]
    
    for i, doc in enumerate(documents, 1):
        title = doc.get("title", "无标题")
        doc_id = doc.get("document_id", "未知")
        url = doc.get("url", "")
        update_time = doc.get("update_time", "")
        
        output_lines.append(f"{i}. {title}")
        output_lines.append(f"   文档ID: {doc_id}")
        if url:
            output_lines.append(f"   链接: {url}")
        if update_time:
            output_lines.append(f"   更新时间: {update_time}")
        output_lines.append("")
    
    return "\n".join(output_lines)


# 工具列表，用于注册到Agent
NOTE_TOOLS = [
    create_document,
    get_document,
    update_document,
    append_to_document,
    delete_document,
    search_documents,
]