"""
文档加载与处理模块
负责从飞书加载文档并进行分块处理
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, JSONLoader

from ..config.settings import get_settings
from ..tools.lark_base import get_cli

logger = logging.getLogger(__name__)


class DocumentLoader:
    """文档加载器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.cli = get_cli()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )
    
    def load_feishu_document(self, document_id: str) -> Optional[Document]:
        """
        加载飞书云文档
        
        Args:
            document_id: 文档ID
        
        Returns:
            Document对象或None
        """
        result = self.cli.get_document(document_id)
        
        if not result.success:
            logger.error(f"加载文档失败: {result.error}")
            return None
        
        doc_data = result.data
        content = doc_data.get("content", "")
        title = doc_data.get("title", "无标题")
        
        if not content:
            logger.warning(f"文档 {document_id} 内容为空")
            return None
        
        return Document(
            page_content=content,
            metadata={
                "source": "feishu_doc",
                "document_id": document_id,
                "title": title,
                "type": "document"
            }
        )
    
    def load_feishu_documents(self, document_ids: List[str]) -> List[Document]:
        """
        批量加载飞书云文档
        
        Args:
            document_ids: 文档ID列表
        
        Returns:
            Document对象列表
        """
        documents = []
        
        for doc_id in document_ids:
            doc = self.load_feishu_document(doc_id)
            if doc:
                documents.append(doc)
        
        logger.info(f"成功加载 {len(documents)}/{len(document_ids)} 个文档")
        return documents
    
    def load_knowledge_article(self, node_token: str) -> Optional[Document]:
        """
        加载知识库文章
        
        Args:
            node_token: 知识库节点token
        
        Returns:
            Document对象或None
        """
        result = self.cli.get_knowledge_article(node_token)
        
        if not result.success:
            logger.error(f"加载知识库文章失败: {result.error}")
            return None
        
        article_data = result.data
        content = article_data.get("content", "")
        title = article_data.get("title", "无标题")
        
        if not content:
            logger.warning(f"知识库文章 {node_token} 内容为空")
            return None
        
        return Document(
            page_content=content,
            metadata={
                "source": "feishu_wiki",
                "node_token": node_token,
                "title": title,
                "type": "wiki_article"
            }
        )
    
    def load_minutes_transcript(self, meeting_id: str) -> Optional[Document]:
        """
        加载妙记逐字稿
        
        Args:
            meeting_id: 会议ID
        
        Returns:
            Document对象或None
        """
        result = self.cli.get_minutes(meeting_id)
        
        if not result.success:
            logger.error(f"加载妙记逐字稿失败: {result.error}")
            return None
        
        minutes_data = result.data
        transcript = minutes_data.get("transcript", "")
        title = minutes_data.get("title", "未知会议")
        
        if not transcript:
            logger.warning(f"会议 {meeting_id} 逐字稿为空")
            return None
        
        return Document(
            page_content=transcript,
            metadata={
                "source": "feishu_minutes",
                "meeting_id": meeting_id,
                "title": title,
                "type": "minutes_transcript"
            }
        )
    
    def load_local_file(self, file_path: str) -> Optional[Document]:
        """
        加载本地文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            Document对象或None
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"文件不存在: {file_path}")
            return None
        
        try:
            if path.suffix == ".json":
                loader = JSONLoader(file_path, jq_schema=".", text_content=False)
            else:
                loader = TextLoader(file_path, encoding="utf-8")
            
            documents = loader.load()
            
            if documents:
                doc = documents[0]
                doc.metadata["source"] = "local_file"
                doc.metadata["file_path"] = file_path
                doc.metadata["file_name"] = path.name
                return doc
            
            return None
            
        except Exception as e:
            logger.error(f"加载本地文件失败: {e}")
            return None
    
    def split_document(self, document: Document) -> List[Document]:
        """
        将文档分割成小块
        
        Args:
            document: Document对象
        
        Returns:
            分割后的Document对象列表
        """
        chunks = self.text_splitter.split_documents([document])
        
        # 为每个chunk添加索引
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)
        
        logger.info(f"文档 '{document.metadata.get('title', '未知')}' 分割为 {len(chunks)} 个块")
        return chunks
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        批量分割文档
        
        Args:
            documents: Document对象列表
        
        Returns:
            分割后的Document对象列表
        """
        all_chunks = []
        
        for doc in documents:
            chunks = self.split_document(doc)
            all_chunks.extend(chunks)
        
        logger.info(f"共分割 {len(documents)} 个文档，得到 {len(all_chunks)} 个块")
        return all_chunks
    
    def load_and_split_feishu_document(self, document_id: str) -> List[Document]:
        """
        加载并分割飞书文档
        
        Args:
            document_id: 文档ID
        
        Returns:
            分割后的Document对象列表
        """
        doc = self.load_feishu_document(document_id)
        if doc:
            return self.split_document(doc)
        return []
    
    def load_and_split_knowledge_article(self, node_token: str) -> List[Document]:
        """
        加载并分割知识库文章
        
        Args:
            node_token: 知识库节点token
        
        Returns:
            分割后的Document对象列表
        """
        doc = self.load_knowledge_article(node_token)
        if doc:
            return self.split_document(doc)
        return []
    
    def load_and_split_minutes(self, meeting_id: str) -> List[Document]:
        """
        加载并分割妙记逐字稿
        
        Args:
            meeting_id: 会议ID
        
        Returns:
            分割后的Document对象列表
        """
        doc = self.load_minutes_transcript(meeting_id)
        if doc:
            return self.split_document(doc)
        return []
    
    def create_document_from_text(
        self,
        text: str,
        title: str = "自定义文档",
        metadata: Dict[str, Any] = None
    ) -> Document:
        """
        从文本创建Document对象
        
        Args:
            text: 文本内容
            title: 文档标题
            metadata: 额外的元数据
        
        Returns:
            Document对象
        """
        base_metadata = {
            "source": "custom_text",
            "title": title,
            "type": "text"
        }
        
        if metadata:
            base_metadata.update(metadata)
        
        return Document(page_content=text, metadata=base_metadata)