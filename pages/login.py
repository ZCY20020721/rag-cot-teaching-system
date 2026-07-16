"""
登录/注册页面
支持教师/学生两种角色，登录与注册模式切换
"""
import streamlit as st
from db import login_user, register_user


def page_login():
    """渲染登录/注册页面"""
    st.title("基于 RAG 与 CoT 的智能教学评估系统")
    st.caption("Retrieval-Augmented Generation + Chain of Thought")

    col_center = st.columns([1, 2, 1])
    with col_center[1]:
        mode = st.radio("选择操作", ["登录", "注册"], horizontal=True)
        role = st.radio("选择角色", ["student", "teacher"],
                       format_func=lambda x: "学生" if x == "student" else "教师",
                       horizontal=True)
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")

        if mode == "登录":
            if st.button("登录", type="primary", use_container_width=True):
                if not username or not password:
                    st.error("请填写用户名和密码")
                else:
                    user = login_user(username, password)
                    if user and user["role"] == role:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.session_state.role = user["role"]
                        st.session_state.user_id = user["id"]
                        st.session_state.username = user["username"]
                        if user["role"] == "student":
                            from db import get_teacher_id
                            st.session_state.chat_with_id = get_teacher_id()
                        st.rerun()
                    else:
                        st.error("用户名、密码或角色不匹配")
        else:
            if st.button("注册", type="primary", use_container_width=True):
                if not username or not password:
                    st.error("请填写用户名和密码")
                elif len(password) < 3:
                    st.error("密码至少3位")
                else:
                    ok, msg = register_user(username, password, role)
                    if ok:
                        st.success(f"{msg}，请切换到登录页面")
                    else:
                        st.error(msg)
