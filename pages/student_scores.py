"""
学生端 — 我的成绩页面
查看历次答题得分记录与统计数据
"""
import streamlit as st

from db import get_student_records


def page_student_scores():
    """我的成绩：个人答题记录 + 得分统计"""
    st.header("我的成绩")
    st.caption("查看历次答题得分情况")

    records = get_student_records(st.session_state.user_id, limit=50)
    if records:
        total = len(records)
        scores = [r["total_score"] or 0 for r in records]
        avg_score = sum(scores) / total if total else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("答题次数", total)
        c2.metric("平均分", f"{avg_score:.1f}")
        c3.metric("最高分", f"{max(scores):.1f}")

        st.divider()
        for r in records:
            with st.expander(
                f"[{r['created_at']}] {r['question'][:60]}... — {r['total_score']}分"
            ):
                st.write(f"**题目：** {r['question']}")
                st.write(f"**你的答案：** {r['student_answer']}")
                st.write(f"**总分：** {r['total_score']} | 逻辑分：{r['logic_score']}")
                st.write(f"**反馈：** {r['feedback']}")
    else:
        st.info("暂无答题记录，请先前往「习题作答」页面答题")
