"""
侧边栏导航模块
根据用户角色动态渲染不同的菜单项
"""
import streamlit as st


def render_sidebar(defaults: dict):
    """渲染左侧边栏：用户信息 + 角色自适应菜单 + 退出按钮"""

    def logout():
        """退出登录，清空 session_state"""
        for k in defaults:
            st.session_state[k] = defaults[k]
        st.rerun()

    with st.sidebar:
        st.subheader(f"当前用户：{st.session_state.username}")
        role_label = "教师" if st.session_state.role == "teacher" else "学生"
        st.caption(f"角色：{role_label}")

        st.divider()
        st.header("导航菜单")

        if st.session_state.role == "teacher":
            pages = {
                "教材管理": "teacher_materials",
                "习题生成": "teacher_exercises",
                "学生成绩": "teacher_scores",
                "师生聊天": "teacher_chat",
            }
        else:
            pages = {
                "习题作答": "student_answer",
                "我的成绩": "student_scores",
                "错题集": "student_errors",
                "师生聊天": "student_chat",
            }

        for label, key in pages.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True,
                        type="primary" if st.session_state.get("page", "") == key else "secondary"):
                st.session_state.page = key
                st.session_state.current_question = None
                st.session_state.grading_result = None
                st.rerun()

        st.divider()
        st.button("退出登录", on_click=logout, use_container_width=True)
