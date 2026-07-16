"""
教师端 — 学生成绩页面
查看所有学生的答题记录、成绩统计与薄弱知识点分布
"""

import json

import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_all_exam_records, get_error_statistics


def page_teacher_scores():
    """学生成绩：全局答题记录 + 知识点错误统计柱状图"""
    st.header("学生成绩")
    st.caption("查看所有学生的答题记录与成绩统计")

    records = get_all_exam_records(limit=100)
    if records:
        total = len(records)
        avg_score = sum(r["total_score"] or 0 for r in records) / total if total else 0
        col1, col2 = st.columns(2)
        col1.metric("总答题次数", total)
        col2.metric("平均分", f"{avg_score:.1f}")

        st.divider()
        for r in records:
            with st.expander(
                f"[{r['created_at']}] {r['student_name']} — "
                f"{r['question'][:60]}... — 得分：{r['total_score']}"
            ):
                st.write(f"**学生：** {r['student_name']}")
                st.write(f"**题目：** {r['question']}")
                st.write(f"**答案：** {r['student_answer']}")
                st.write(f"**总分：** {r['total_score']} | 逻辑分：{r['logic_score']}")
                st.write(f"**反馈：** {r['feedback']}")
                weak = json.loads(r["weak_tags"]) if r["weak_tags"] else []
                if weak:
                    st.write(f"**薄弱点：** {'、'.join(weak)}")
    else:
        st.info("暂无答题记录")

    st.divider()
    st.subheader("知识点错误统计")
    error_stats = get_error_statistics()
    if error_stats:
        df = pd.DataFrame(error_stats)
        fig = px.bar(
            df,
            x="tag",
            y="count",
            title="薄弱知识点分布",
            labels={"tag": "知识点", "count": "错误次数"},
            color="count",
            color_continuous_scale="Reds",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无统计数据")
