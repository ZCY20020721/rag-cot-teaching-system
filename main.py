"""
基于 RAG 与 CoT 的智能教学系统 - 多角色多页面入口（精简版）
页面逻辑已拆分至 pages/ 目录，本文件仅负责初始化与路由分发
"""
import streamlit as st

from db import init_db
from dependencies import get_rag

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="智能教学系统 - RAG + CoT",
    page_icon="📚",
    layout="wide",
)

# ============================================================
# 初始化数据库
# ============================================================
init_db()

# ============================================================
# Session State 初始化
# ============================================================
rag = get_rag()

defaults = {
    "logged_in": False,
    "user": None,
    "role": None,
    "user_id": None,
    "username": None,
    "current_question": None,
    "current_answer_points": None,
    "grading_result": None,
    "current_exercise": None,
    "pdf_loaded": rag.get_chunks_count() > 0,
    "chat_with_id": None,
    "chat_with_name": "",
    "chat_last_id": 0,
    "chat_refresh_key": 0,
    "chat_input_text": "",
    "show_emoji": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# 路由分发
# ============================================================
if not st.session_state.logged_in:
    from pages.login import page_login
    page_login()
else:
    from pages.sidebar import render_sidebar
    render_sidebar(defaults)

    page = st.session_state.get("page", "")

    if page == "teacher_materials":
        from pages.teacher_materials import page_teacher_materials
        page_teacher_materials()
    elif page == "teacher_exercises":
        from pages.teacher_exercises import page_teacher_exercises
        page_teacher_exercises()
    elif page == "teacher_scores":
        from pages.teacher_scores import page_teacher_scores
        page_teacher_scores()
    elif page == "teacher_chat":
        from pages.chat import page_chat
        page_chat(is_teacher=True)
    elif page == "student_answer":
        from pages.student_answer import page_student_answer
        page_student_answer()
    elif page == "student_scores":
        from pages.student_scores import page_student_scores
        page_student_scores()
    elif page == "student_errors":
        from pages.student_errors import page_student_errors
        page_student_errors()
    elif page == "student_chat":
        from pages.chat import page_chat
        page_chat(is_teacher=False)
    else:
        # 首次登录，跳转到默认页
        if st.session_state.role == "teacher":
            st.session_state.page = "teacher_materials"
        else:
            st.session_state.page = "student_answer"
        st.rerun()
