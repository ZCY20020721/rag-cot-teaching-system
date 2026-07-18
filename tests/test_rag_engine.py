"""rag_engine.py 单元测试 - 使用 mock 隔离 ChromaDB 和 PDF 加载"""
import os
from unittest.mock import MagicMock, patch

import pytest

from rag_engine import RAGEngine


class TestRAGEngineInit:
    """初始化与配置测试"""

    def test_text_splitter_config(self):
        engine = RAGEngine(persist_dir="/tmp/test")
        assert engine.text_splitter._chunk_size == 500
        assert engine.text_splitter._chunk_overlap == 50

    def test_separators_priority(self):
        engine = RAGEngine(persist_dir="/tmp/test")
        separators = engine.text_splitter._separators
        assert "\n\n" in separators
        assert "." in separators
        assert " " in separators


class TestLoadPDF:
    """PDF 加载测试"""

    @patch("rag_engine.PyPDFLoader")
    @patch("rag_engine.Chroma")
    def test_load_pdf_first_time_creates_vectorstore(self, mock_chroma, mock_loader):
        mock_doc = MagicMock()
        mock_doc.page_content = "第一章内容。包含多个句子。用于测试。"
        mock_doc.metadata = {"page": 0}
        mock_loader.return_value.load.return_value = [mock_doc]

        engine = RAGEngine(persist_dir="/fake/chroma")
        engine.vectorstore = None
        count = engine.load_pdf("/fake/test.pdf")

        assert count >= 1
        mock_loader.assert_called_once_with("/fake/test.pdf")
        mock_chroma.from_documents.assert_called_once()
        assert mock_doc.metadata.get("source") == "test.pdf"

    @patch("rag_engine.PyPDFLoader")
    @patch("rag_engine.Chroma")
    def test_load_pdf_subsequent_adds_documents(self, mock_chroma, mock_loader):
        mock_doc = MagicMock()
        mock_doc.page_content = "测试内容"
        mock_doc.metadata = {"page": 0}
        mock_loader.return_value.load.return_value = [mock_doc]

        existing_vs = MagicMock()
        engine = RAGEngine(persist_dir="/fake/chroma")
        engine.vectorstore = existing_vs
        count = engine.load_pdf("/fake/test.pdf")

        assert count >= 1
        existing_vs.add_documents.assert_called_once()
        mock_chroma.from_documents.assert_not_called()

    @patch("rag_engine.PyPDFLoader")
    @patch("rag_engine.Chroma")
    def test_load_pdf_adds_source_metadata(self, mock_chroma, mock_loader):
        mock_doc = MagicMock()
        mock_doc.page_content = "测试内容"
        mock_doc.metadata = {}
        mock_loader.return_value.load.return_value = [mock_doc]

        engine = RAGEngine(persist_dir="/fake/chroma")
        engine.load_pdf("/path/to/algorithm.pdf")

        assert mock_doc.metadata.get("source") == "algorithm.pdf"


class TestSearch:
    """检索功能测试"""

    def test_search_without_vectorstore_returns_error(self):
        engine = RAGEngine(persist_dir="/fake/chroma")
        engine.vectorstore = None
        results = engine.search("测试问题")
        assert len(results) == 1
        assert "错误" in results[0]

    def test_search_with_sources_without_vectorstore_returns_empty(self):
        engine = RAGEngine(persist_dir="/fake/chroma")
        engine.vectorstore = None
        results = engine.search_with_sources("测试")
        assert results == []

    def test_search_returns_page_contents(self):
        engine = RAGEngine(persist_dir="/fake/chroma")

        mock_doc1 = MagicMock()
        mock_doc1.page_content = "二叉树相关内容"
        mock_doc2 = MagicMock()
        mock_doc2.page_content = "另一个片段"

        mock_vs = MagicMock()
        mock_vs.similarity_search.return_value = [mock_doc1, mock_doc2]
        engine.vectorstore = mock_vs

        results = engine.search("二叉树", k=2)
        assert results == ["二叉树相关内容", "另一个片段"]
        mock_vs.similarity_search.assert_called_once_with("二叉树", k=2)

    def test_search_with_sources_returns_metadata(self):
        engine = RAGEngine(persist_dir="/fake/chroma")

        mock_doc = MagicMock()
        mock_doc.page_content = "数据结构章节"
        mock_doc.metadata = {"page": 5, "source": "book.pdf"}

        mock_vs = MagicMock()
        mock_vs.similarity_search.return_value = [mock_doc]
        engine.vectorstore = mock_vs

        results = engine.search_with_sources("数据结构", k=1)
        assert len(results) == 1
        assert results[0]["content"] == "数据结构章节"
        assert results[0]["source"] == "book.pdf"
        assert results[0]["page"] == 5


class TestChunksCount:
    """文本块计数测试"""

    def test_count_zero_without_vectorstore(self):
        engine = RAGEngine(persist_dir="/fake/chroma")
        engine.vectorstore = None
        assert engine.get_chunks_count() == 0

    def test_count_from_vectorstore(self):
        engine = RAGEngine(persist_dir="/fake/chroma")
        mock_vs = MagicMock()
        mock_vs._collection.count.return_value = 42
        engine.vectorstore = mock_vs
        assert engine.get_chunks_count() == 42

    def test_count_handles_exception(self):
        engine = RAGEngine(persist_dir="/fake/chroma")
        mock_vs = MagicMock()
        mock_vs._collection.count.side_effect = Exception("db error")
        engine.vectorstore = mock_vs
        assert engine.get_chunks_count() == 0


class TestPersistence:
    """持久化加载测试"""

    @patch("rag_engine.HuggingFaceEmbeddings")
    @patch("rag_engine.Chroma")
    def test_existing_vectorstore_is_loaded(self, mock_chroma, mock_embeddings):
        mock_chroma.return_value = MagicMock()

        with patch("os.path.exists", return_value=True), \
             patch("os.listdir", return_value=["chroma.sqlite3"]):
            engine = RAGEngine(persist_dir="/fake/exists")

        assert engine.vectorstore is not None
        mock_chroma.assert_called_once()

    @patch("rag_engine.HuggingFaceEmbeddings")
    @patch("rag_engine.Chroma")
    def test_empty_dir_does_not_load_vectorstore(self, mock_chroma, mock_embeddings):
        with patch("os.path.exists", return_value=True), \
             patch("os.listdir", return_value=[]):
            engine = RAGEngine(persist_dir="/fake/empty")

        assert engine.vectorstore is None
        mock_chroma.assert_not_called()


class TestEmbeddingModel:
    """嵌入模型配置测试"""

    @patch("rag_engine.HuggingFaceEmbeddings")
    def test_embeddings_model_name(self, mock_embeddings):
        mock_instance = MagicMock()
        mock_instance.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        mock_embeddings.return_value = mock_instance

        engine = RAGEngine(persist_dir="/fake/chroma")
        assert "all-MiniLM-L6-v2" in engine.embeddings.model_name
        mock_embeddings.assert_called_once()
