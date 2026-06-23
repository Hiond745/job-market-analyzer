"""公司画像 Tab"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import plotly.express as px
from src.analyzer import get_jobs_by_title, top_companies, industry_distribution

def render(city: str, title: str):
    df = get_jobs_by_title(title, city)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🏢 招聘公司 Top 10")
        companies_df = top_companies(df, top_n=10)
        if not companies_df.empty:
            fig = px.bar(companies_df, x="count", y="company", orientation="h", labels={"count": "招聘数量", "company": ""}, color="count", color_continuous_scale="Blues")
            fig.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0), yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("暂无公司数据")
    with col2:
        st.markdown("### 🏭 行业分布")
        ind_df = industry_distribution(df)
        if not ind_df.empty:
            fig = px.pie(ind_df, values="count", names="industry", color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("暂无行业数据")
