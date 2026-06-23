"""市场总览 Tab"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import plotly.express as px
from src.analyzer import get_jobs_by_title, job_market_overview, education_distribution, experience_distribution

def render(city: str, title: str):
    df = get_jobs_by_title(title, city)
    overview = job_market_overview(df)

    # 4 个指标卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("📋 岗位数量", overview["total_count"])
    with col2: st.metric("💰 平均薪资", f"{overview['avg_salary']}K")
    with col3: st.metric("📊 薪资中位数", f"{overview['salary_median']}K")
    with col4: st.metric("🏢 招聘公司数", overview["company_count"])

    # 薪资分布直方图
    st.markdown("### 💰 薪资分布")
    if not df.empty and "salary_avg" in df.columns:
        fig = px.histogram(df, x="salary_avg", nbins=15, labels={"salary_avg": "月薪 (K)", "count": "岗位数"}, color_discrete_sequence=["#4C78A8"])
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # 学历 + 经验
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🎓 学历要求")
        edu_df = education_distribution(df)
        if not edu_df.empty:
            fig = px.pie(edu_df, values="count", names="education", color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("暂无学历数据")
    with col2:
        st.markdown("### 📅 经验要求")
        exp_df = experience_distribution(df)
        if not exp_df.empty:
            fig = px.bar(exp_df, x="experience", y="count", labels={"experience": "经验要求", "count": "岗位数"}, color="count", color_continuous_scale="Blues")
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("暂无经验数据")
