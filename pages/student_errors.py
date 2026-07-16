"""
学生端 — 错题集页面
按知识点标签汇总薄弱环节，可视化个人知识短板
"""

import json

import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_student_error_statistics, get_student_records


def page_student_errors():
    """错题集：薄弱知识点柱状图 + 错题回顾"""
    st.header("错题集")
    st.caption("按知识点标签汇总薄弱环节")

    error_stats = get_student_error_statistics(st.session_state.user_id)
    if error_stats:
        df = pd.DataFrame(error_stats)
        fig = px.bar(
            df,
            x="tag",
            y="count",
            title="个人薄弱知识点分布",
            labels={"tag": "知识点", "count": "错误次数"},
            color="count",
            color_continuous_scale="Reds",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("错题回顾")
    records = get_student_records(st.session_state.user_id, limit=50)
    weak_records = [
        r
        for r in records
        if (
            r["weak_tags"]
            and json.loads(r["weak_tags"] if isinstance(r["weak_tags"], str) else "[]")
        )
    ]
    if weak_records:
        for r in weak_records:
            weak = (
                json.loads(r["weak_tags"])
                if isinstance(r["weak_tags"], str)
                else (r["weak_tags"] or [])
            )
            with st.expander(f"[{r['created_at']}] {'、'.join(weak)} — {r['question'][:50]}..."):
                st.write(f"**题目：** {r['question']}")
                st.write(f"**你的答案：** {r['student_answer']}")
                st.write(f"**得分：** {r['total_score']}")
                st.write(f"**反馈：** {r['feedback']}")
    else:
        st.info("暂无错题记录，继续加油！")
