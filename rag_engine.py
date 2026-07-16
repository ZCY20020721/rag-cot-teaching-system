"""
RAG 检索引擎 - 基于教材的检索增强生成
支持 PDF 加载、文本切分、向量化存储、相似度检索
使用本地 HuggingFace 嵌入模型，无需额外 API
"""
import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


class RAGEngine:
    """轻量化 RAG 检索引擎，基于 ChromaDB 本地向量存储"""

    def __init__(self, persist_dir: str = "./chroma_db"):
        # 使用本地 HuggingFace 嵌入模型，完全免费，无需 API Key
        # all-MiniLM-L6-v2: 轻量级，384维，英文为主，中英文混合也可用
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

        self.persist_dir = persist_dir
        self.vectorstore: Optional[Chroma] = None

        # 尝试加载已有的向量库
        if os.path.exists(persist_dir) and os.listdir(persist_dir):
            try:
                self.vectorstore = Chroma(
                    persist_directory=persist_dir,
                    embedding_function=self.embeddings,
                )
            except Exception:
                pass

    def load_pdf(self, pdf_path: str) -> int:
        """加载 PDF 并向量化存储，返回切分后的文本块数量"""
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()

        # 为每个文档添加来源标记
        pdf_name = os.path.basename(pdf_path)
        for doc in documents:
            doc.metadata["source"] = pdf_name

        chunks = self.text_splitter.split_documents(documents)

        if self.vectorstore is None:
            self.vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=self.persist_dir,
            )
        else:
            self.vectorstore.add_documents(chunks)

        return len(chunks)

    def search(self, query: str, k: int = 5) -> List[str]:
        """检索与查询最相关的文本片段"""
        if self.vectorstore is None:
            return ["[错误] 请先上传PDF教材，构建知识库。"]

        docs = self.vectorstore.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]

    def search_with_sources(self, query: str, k: int = 5) -> List[dict]:
        """检索并返回文本片段及其来源"""
        if self.vectorstore is None:
            return []

        docs = self.vectorstore.similarity_search(query, k=k)
        return [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "未知"),
                "page": doc.metadata.get("page", -1),
            }
            for doc in docs
        ]

    def get_chunks_count(self) -> int:
        """获取当前向量库中的文本块数量"""
        if self.vectorstore is None:
            return 0
        try:
            return self.vectorstore._collection.count()
        except Exception:
            return 0
