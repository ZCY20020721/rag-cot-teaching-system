"""
共享依赖模块 — Streamlit 全局单例管理
通过 @st.cache_resource 确保 RAGEngine 和 CoTGrader 全局唯一
"""

import streamlit as st

from cot_grader import CoTGrader
from rag_engine import RAGEngine


@st.cache_resource
def get_rag():
    """获取 RAG 检索引擎全局单例"""
    return RAGEngine(persist_dir="./chroma_db")


@st.cache_resource
def get_grader():
    """获取 CoT 批改引擎全局单例"""
    return CoTGrader()
