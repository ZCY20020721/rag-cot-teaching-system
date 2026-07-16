"""
学生端 — 习题作答页面
查看教师发布的习题，提交答案，获取 CoT 分步批改反馈
"""
import json

import streamlit as st

from db import get_all_exercises, save_exam_record
from dependencies import get_grader, get_rag


def page_student_answer():
    """习题作答：选题 → 答题 → CoT 批改 → 结构化展示"""
    rag = get_rag()
    grader = get_grader()

    st.header("习题作答")
    st.caption("查看教师发布的习题，提交答案，获取 AI 批改反馈")

    exercises = get_all_exercises()
    if not exercises:
        st.info("教师尚未发布习题")
        return

    ex_options = {f"#{ex['id']} {ex['question'][:80]}...": ex for ex in exercises}
    selected_label = st.selectbox("选择习题", list(ex_options.keys()))
    exercise = ex_options[selected_label]

    with st.container(border=True):
        st.subheader(exercise["question"])
        st.caption(f"满分：{exercise['total_max_score']} 分")
        with st.expander("查看提示"):
            pts = json.loads(exercise['standard_answer_points']) if isinstance(
                exercise['standard_answer_points'], str
            ) else exercise['standard_answer_points']
            st.write(f"本题包含 {len(pts)} 个得分点")

    student_answer = st.text_area("你的答案", height=180, placeholder="在此作答...")

    if st.button("提交批改", type="primary", disabled=not student_answer.strip()):
        with st.spinner("AI 正在分步骤批改..."):
            retrieved_docs = rag.search(exercise["question"], k=5)
            rag_context = "\n\n".join(retrieved_docs)
            result = grader.grade_answer(
                rag_context=rag_context,
                standard_answer_points=exercise["standard_answer_points"],
                student_answer=student_answer,
            )
            if result:
                st.session_state.grading_result = result
                try:
                    pts = json.loads(exercise['standard_answer_points']) if isinstance(
                        exercise['standard_answer_points'], str
                    ) else exercise['standard_answer_points']
                    save_exam_record(
                        question=exercise["question"],
                        standard_answer_points=exercise["standard_answer_points"],
                        student_answer=student_answer,
                        grading_result=result,
                        student_name=st.session_state.username,
                        student_id=st.session_state.user_id,
                        exercise_id=exercise["id"],
                    )
                except Exception:
                    pass
            else:
                st.error("批改失败，请重试")

    if st.session_state.grading_result:
        gr = st.session_state.grading_result
        with st.container(border=True):
            total = gr.get("total_score", 0)
            logic = gr.get("logic_score", 0)
            c1, c2, c3 = st.columns(3)
            c1.metric("总分", f"{total:.1f}")
            c2.metric("逻辑分", f"{logic:.1f}/5")
            pts = sum(s.get("score", 0) for s in gr.get("step_scores", []))
            c3.metric("要点分", f"{pts:.1f}")

            st.divider()
            st.subheader("逐点评分（CoT 思维链）")
            for s in gr.get("step_scores", []):
                score = s.get("score", 0)
                if score >= 4:
                    label = "[优秀]"
                elif score >= 2:
                    label = "[一般]"
                else:
                    label = "[薄弱]"
                st.write(f"{label} **要点 {s.get('point_index', 0)+1}** — 得分：{score}/5")
                st.caption(f"  学生表述：{s.get('student_content', '')}")
                st.caption(f"  评语：{s.get('comment', '')}")

            st.write(f"**逻辑评估**（{logic}/5）：{gr.get('logic_comment', '')}")
            st.divider()
            st.subheader("教师反馈")
            st.info(gr.get("feedback", ""))
            weak_tags = gr.get("weak_tags", [])
            if weak_tags:
                st.warning(f"需要加强：{'、'.join(weak_tags)}")
