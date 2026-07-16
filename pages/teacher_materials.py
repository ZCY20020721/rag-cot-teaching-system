"""
教师端 — 教材管理页面
上传 PDF 教材，构建 RAG 知识库
"""
import os
import tempfile
from pathlib import Path

import streamlit as st

from dependencies import get_rag


def page_teacher_materials():
    """教材管理：上传 PDF → 向量化 → 查看知识库状态"""
    rag = get_rag()

    st.header("教材管理")
    st.caption("上传 PDF 教材，构建 RAG 知识库")

    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("上传 PDF 教材", type="pdf")
        if uploaded_file and st.button("加载到知识库", type="primary"):
            with st.spinner("正在处理 PDF..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name
                try:
                    chunk_count = rag.load_pdf(tmp_path)
                    st.session_state.pdf_loaded = True
                    st.success(f"已加载！切分为 {chunk_count} 个文本块")
                except Exception as e:
                    st.error(f"加载失败：{str(e)}")
                finally:
                    os.unlink(tmp_path)

    with col2:
        st.subheader("已导入教材")
        data_dir = Path("data")
        if data_dir.exists():
            pdf_files = list(data_dir.glob("*.pdf"))
            if pdf_files:
                for f in pdf_files:
                    st.write(f"- {f.name}")
                selected = st.selectbox(
                    "快速加载已有教材", pdf_files,
                    format_func=lambda x: x.name[:60]
                )
                if st.button("加载选中文件"):
                    with st.spinner("正在处理..."):
                        chunk_count = rag.load_pdf(str(selected))
                        st.session_state.pdf_loaded = True
                        st.success(f"已加载！{chunk_count} 个文本块")
            else:
                st.info("data/ 目录中暂无 PDF")

    st.divider()
    chunks = rag.get_chunks_count()
    st.metric("知识库文本块总数", chunks)
    if st.session_state.pdf_loaded:
        st.success("知识库已就绪，可前往「习题生成」页面出题")
