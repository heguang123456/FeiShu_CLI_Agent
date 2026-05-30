"""
向量存储管理模块
负责文档的向量化、存储和检索
"""

import logging
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import lru_cache

from langchain_community.vectorstores import Chroma, FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class MockEmbeddings(Embeddings):
    """模拟嵌入模型（用于测试）"""
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表"""
        return [self._get_embedding(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本"""
        return self._get_embedding(text)
    
    def _get_embedding(self, text: str) -> List[float]:
        """生成简单的模拟嵌入向量（基于文本哈希）"""
        hash_value = hashlib.md5(text.encode()).hexdigest()
        # 将哈希值转换为 128 维的浮点数向量
        embedding = []
        for i in range(0, len(hash_value), 2):
            val = int(hash_value[i:i+2], 16) / 255.0
            embedding.append(val)
        return embedding


class SearchDocumentsInput(BaseModel):
    """搜索文档输入参数"""
    query: str = Field(description="搜索查询内容")
    k: int = Field(default=5, description="返回的文档数量")
    filter_metadata: Optional[Dict[str, str]] = Field(
        default=None, 
        description="元数据过滤条件（可选），如：{'source': 'feishu'}"
    )


class AddDocumentsInput(BaseModel):
    """添加文档输入参数"""
    texts: List[str] = Field(description="文档文本列表")
    metadatas: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="每个文档的元数据列表（可选）"
    )


class IndexFeishuDocumentInput(BaseModel):
    """索引飞书文档输入参数"""
    document_id: str = Field(description="飞书文档ID")
    title: Optional[str] = Field(default=None, description="文档标题（可选，用于元数据）")


class RagQueryInput(BaseModel):
    """RAG查询输入参数"""
    query: str = Field(description="查询内容")
    k: int = Field(default=3, description="返回的相关文档数量（默认3）")


class VectorStoreManager:
    """向量存储管理器"""
    
    def __init__(self, store_type: str = "chroma"):
        """
        初始化向量存储管理器
        
        Args:
            store_type: 向量存储类型，支持 "chroma" 或 "faiss"
        """
        self.settings = get_settings()
        self.store_type = store_type
        
        # 根据模式选择嵌入模型
        if self.settings.mock_mode:
            self.embeddings = MockEmbeddings()
            logger.info("使用模拟嵌入模型（MockEmbeddings）")
        else:
            self.embeddings = OpenAIEmbeddings(
                model=self.settings.embedding_model,
                openai_api_key=self.settings.openai_api_key,
                openai_api_base=self.settings.openai_api_base,
            )
        self._vector_store = None
    
    @property
    def vector_store(self):
        """懒加载向量存储"""
        if self._vector_store is None:
            self._vector_store = self._create_vector_store()
        return self._vector_store
    
    def _create_vector_store(self):
        """创建向量存储实例"""
        store_path = Path(self.settings.vector_store_path)
        store_path.mkdir(parents=True, exist_ok=True)
        
        if self.store_type == "chroma":
            return Chroma(
                persist_directory=str(store_path),
                embedding_function=self.embeddings,
                collection_name="noteagent_docs"
            )
        elif self.store_type == "faiss":
            index_path = store_path / "faiss_index"
            if index_path.exists():
                return FAISS.load_local(
                    str(index_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
            empty_index = FAISS.from_texts(
                ["__faiss_init_placeholder__"],
                self.embeddings,
                metadata=[{"source": "system", "type": "placeholder"}]
            )
            empty_index.delete([0])
            empty_index.save_local(str(index_path))
            logger.info("创建空FAISS索引")
            return empty_index
        else:
            raise ValueError(f"不支持的向量存储类型: {self.store_type}")
    
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        添加文本文档到向量存储
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
        
        Returns:
            添加的文档ID列表
        """
        if not texts:
            return []
        
        # FAISS 首次写入时创建索引
        if self.store_type == "faiss" and self._vector_store is None:
            self._vector_store = FAISS.from_texts(texts, self.embeddings, metadatas=metadatas)
            self._persist_faiss()
            logger.info(f"创建 FAISS 索引并添加了 {len(texts)} 个文档")
            return list(range(len(texts)))
        
        ids = self.vector_store.add_texts(texts, metadatas)
        
        # 持久化FAISS索引
        if self.store_type == "faiss":
            self._persist_faiss()
        
        logger.info(f"添加了 {len(texts)} 个文档到向量存储")
        return ids
    
    def add_texts_with_dedup(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        dedup_key: str = "document_id"
    ) -> List[str]:
        """
        添加文本到向量存储，基于 dedup_key 去重（先删旧数据再插入）
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
            dedup_key: 去重用的元数据字段名
        
        Returns:
            添加的文档ID列表
        """
        if not texts:
            return []
        
        # 先尝试删除已有的同源文档
        if metadatas and self.store_type == "chroma":
            for meta in metadatas:
                doc_id = meta.get(dedup_key)
                if doc_id:
                    try:
                        existing = self.vector_store.get(
                            where={dedup_key: doc_id}
                        )
                        if existing and existing.get("ids"):
                            self.vector_store.delete(ids=existing["ids"])
                            logger.info(f"删除旧文档 chunks: {len(existing['ids'])} 个 (document_id={doc_id})")
                    except Exception as e:
                        logger.debug(f"去重查询跳过: {e}")
        
        return self.add_texts(texts, metadatas)
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        添加Document对象到向量存储
        
        Args:
            documents: Document对象列表
        
        Returns:
            添加的文档ID列表
        """
        if not documents:
            return []
        
        ids = self.vector_store.add_documents(documents)
        
        if self.store_type == "faiss":
            self._persist_faiss()
        
        logger.info(f"添加了 {len(documents)} 个文档到向量存储")
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, str]] = None
    ) -> List[Document]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filter_metadata: 元数据过滤条件
        
        Returns:
            相似文档列表
        """
        if self._vector_store is None and self.store_type == "faiss":
            logger.warning("FAISS 索引尚未创建，无法搜索")
            return []
        
        kwargs = {}
        if filter_metadata:
            kwargs["filter"] = filter_metadata
        
        results = self.vector_store.similarity_search(
            query,
            k=k,
            **kwargs
        )
        
        logger.info(f"搜索 '{query}' 找到 {len(results)} 个结果")
        return results
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, str]] = None
    ) -> List[tuple]:
        """
        带分数的相似度搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filter_metadata: 元数据过滤条件
        
        Returns:
            (Document, score)元组列表
        """
        kwargs = {}
        if filter_metadata:
            kwargs["filter"] = filter_metadata
        
        results = self.vector_store.similarity_search_with_score(
            query,
            k=k,
            **kwargs
        )
        
        logger.info(f"搜索 '{query}' 找到 {len(results)} 个结果（带分数）")
        return results
    
    def delete(self, ids: List[str]) -> None:
        """
        删除文档
        
        Args:
            ids: 要删除的文档ID列表
        """
        self.vector_store.delete(ids)
        
        if self.store_type == "faiss":
            self._persist_faiss()
        
        logger.info(f"删除了 {len(ids)} 个文档")
    
    def _persist_faiss(self):
        """持久化FAISS索引"""
        if self.store_type == "faiss" and self._vector_store:
            store_path = Path(self.settings.vector_store_path)
            index_path = store_path / "faiss_index"
            self._vector_store.save_local(str(index_path))
    
    def as_retriever(self, **kwargs):
        """获取检索器"""
        return self.vector_store.as_retriever(**kwargs)


# 全局实例
_vector_store_manager = None


def get_vector_store_manager(store_type: str = "chroma") -> VectorStoreManager:
    """获取向量存储管理器单例"""
    global _vector_store_manager
    if _vector_store_manager is None:
        _vector_store_manager = VectorStoreManager(store_type)
    return _vector_store_manager


@tool(args_schema=SearchDocumentsInput)
def search_documents_in_store(
    query: str,
    k: int = 5,
    filter_metadata: Dict[str, str] = None
) -> str:
    """在本地知识库中搜索相关文档。
    
    当用户需要查找已索引的文档、搜索本地知识库、检索相关资料时使用此工具。
    这个工具会搜索之前已经添加到向量数据库中的文档内容。
    
    Args:
        query: 搜索查询内容，描述你要查找的信息
        k: 返回的文档数量（默认5）
        filter_metadata: 元数据过滤条件（可选），如：{'source': 'feishu'}
    
    Returns:
        搜索到的相关文档内容
    """
    manager = get_vector_store_manager()
    results = manager.similarity_search(query, k, filter_metadata)
    
    if not results:
        return "本地知识库中未找到相关文档。"
    
    output_lines = [f"在本地知识库中找到 {len(results)} 个相关文档：\n"]
    
    for i, doc in enumerate(results, 1):
        content = doc.page_content
        source = doc.metadata.get("source", "未知来源")
        
        # 截断过长的内容
        if len(content) > 500:
            content = content[:500] + "..."
        
        output_lines.append(f"--- 文档 {i} (来源: {source}) ---")
        output_lines.append(content)
        output_lines.append("")
    
    return "\n".join(output_lines)


@tool(args_schema=AddDocumentsInput)
def add_documents_to_store(
    texts: List[str],
    metadatas: List[Dict[str, Any]] = None
) -> str:
    """将文档添加到本地知识库。
    
    当用户需要索引新文档、将内容存入知识库、建立文档索引时使用此工具。
    添加后可以通过search_documents_in_store进行语义搜索。
    
    Args:
        texts: 文档文本列表，每个元素是一个文档的内容
        metadatas: 每个文档的元数据列表（可选），如：[{'source': 'feishu', 'title': '文档标题'}]
    
    Returns:
        添加结果
    """
    manager = get_vector_store_manager()
    ids = manager.add_texts(texts, metadatas)
    
    return f"成功添加 {len(ids)} 个文档到本地知识库。"


@tool(args_schema=IndexFeishuDocumentInput)
def index_feishu_document(document_id: str, title: str = None) -> str:
    """将飞书云文档索引到本地知识库（加载→分块→向量化→存储）。
    
    当用户需要将飞书文档添加到知识库、建立文档索引、以便后续语义搜索时使用此工具。
    完成后可通过 search_documents_in_store 或 rag_query 进行检索。
    
    Args:
        document_id: 飞书文档ID
        title: 文档标题（可选，用于元数据标记）
    
    Returns:
        索引结果，包含分块数量等信息
    """
    from .document_loader import DocumentLoader
    
    loader = DocumentLoader()
    chunks = loader.load_and_split_feishu_document(document_id)
    
    if not chunks:
        return f"文档 {document_id} 加载失败或内容为空，无法索引。"
    
    texts = [c.page_content for c in chunks]
    metadatas = []
    for c in chunks:
        meta = dict(c.metadata)
        meta["document_id"] = document_id
        if title:
            meta["title"] = title
        metadatas.append(meta)
    
    manager = get_vector_store_manager()
    ids = manager.add_texts_with_dedup(texts, metadatas, dedup_key="document_id")
    
    return f"文档 {document_id} 索引成功！共 {len(ids)} 个分块已存入本地知识库。"


@tool(args_schema=RagQueryInput)
def rag_query(query: str, k: int = 3) -> str:
    """基于本地知识库的 RAG 问答：检索相关文档片段并返回结构化上下文。
    
    当用户需要根据已索引的文档内容回答问题、查找相关信息时使用此工具。
    它会从向量数据库中检索最相关的文档片段，作为回答问题的参考依据。
    
    Args:
        query: 查询内容
        k: 返回的相关文档片段数量（默认3）
    
    Returns:
        检索到的相关文档片段，可作为回答问题的参考
    """
    manager = get_vector_store_manager()
    results = manager.similarity_search(query, k)
    
    if not results:
        return "本地知识库中未找到相关内容。请先使用 index_feishu_document 索引相关文档。"
    
    context_parts = []
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("title", doc.metadata.get("source", "未知"))
        content = doc.page_content
        if len(content) > 800:
            content = content[:800] + "..."
        context_parts.append(f"[来源{i}: {source}]\n{content}")
    
    return "以下是本地知识库中与查询最相关的内容：\n\n" + "\n\n---\n\n".join(context_parts)


# RAG工具列表
RAG_TOOLS = [
    search_documents_in_store,
    add_documents_to_store,
    index_feishu_document,
    rag_query,
]