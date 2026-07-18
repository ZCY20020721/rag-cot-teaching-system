"""
教师端 — 习题生成页面
基于教材 RAG 检索，AI 自动生成考题并发布
"""

import json

import streamlit as st

from db import get_all_exercises, save_exercise
from dependencies import get_grader, get_rag


@st.cache_data(ttl=10)
def _cached_exercises():
    return get_all_exercises()


@st.cache_data(ttl=60)
def _cached_search_context(query: str, k: int = 5):
    """缓存 RAG 检索结果，避免重复调用 Embedding API"""
    return "\n\n".join(get_rag().search(query, k=k))


def page_teacher_exercises():
    """习题生成：RAG 出题 → 教师审阅 → 发布给学生"""
    rag = get_rag()
    grader = get_grader()

    st.header("习题生成")
    st.caption("基于教材内容，AI 自动生成考题并发布")

    if not st.session_state.pdf_loaded:
        st.warning("请先在「教材管理」页面导入 PDF 教材")
        return

    if st.button("基于教材生成考题", type="primary"):
        with st.spinner("AI 正在分析教材并生成考题..."):
            rag_context = _cached_search_context("提取核心概念和关键知识点，用于出题", k=5)
            if rag_context and rag_context[0].startswith("["):
                st.error(rag_context)
            else:
                result = grader.generate_question(rag_context)
                if result:
                    st.session_state.current_question = result
                    st.session_state.current_answer_points = json.dumps(
                        result.get("standard_answer_points", []), ensure_ascii=False
                    )
                    st.session_state.grading_result = None
                else:
                    st.error("出题失败，请重试")

    if st.session_state.current_question:
        q = st.session_state.current_question
        with st.container(border=True):
            st.subheader(q.get("question", ""))
            st.caption(f"满分：{q.get('total_max_score', 15)} 分")
            with st.expander("查看标准答案要点"):
                for i, pt in enumerate(q.get("standard_answer_points", [])):
                    st.write(f"**要点 {i+1}** [{pt.get('tag', '')}] ({pt.get('max_score', 5)}分)")
                    st.write(f"  {pt.get('point', '')}")

        if st.button("发布此题给学生", type="primary"):
            eid = save_exercise(
                teacher_id=st.session_state.user_id,
                question=q["question"],
                standard_answer_points=st.session_state.current_answer_points,
                total_max_score=q.get("total_max_score", 15),
            )
            st.success(f"习题已发布！学生可在「习题作答」页面查看")
            st.session_state.current_question = None

    st.divider()
    st.subheader("已发布习题列表")
    exercises = _cached_exercises()
    if exercises:
        for ex in exercises:
            with st.expander(f"[{ex['created_at']}] {ex['question'][:100]}..."):
                st.write(f"**题目：** {ex['question']}")
                st.write(f"**满分：** {ex['total_max_score']}")
                pts = (
                    json.loads(ex["standard_answer_points"])
                    if isinstance(ex["standard_answer_points"], str)
                    else ex["standard_answer_points"]
                )
                st.write("**标准答案要点：**")
                for pt in pts:
                    st.write(f"  - [{pt.get('tag', '')}] {pt.get('point', '')}")
    else:
        st.info("暂无已发布的习题")
