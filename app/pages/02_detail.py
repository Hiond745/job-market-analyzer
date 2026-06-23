"""岗位方向详情页（4 个 Tab）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from src.config import DEFAULT_CITY
from app.components import overview, skills, companies, resume_match

st.set_page_config(page_title="岗位详情", page_icon="📊", layout="wide")

if "selected_title" not in st.session_state or not st.session_state.selected_title:
    st.warning("请先在推荐结果页选择一个岗位方向")
    if st.button("← 返回推荐结果"): st.switch_page("pages/01_recommend.py")
    st.stop()

title = st.session_state.selected_title
city = st.session_state.get("city", DEFAULT_CITY)
skills_str = st.session_state.get("skills", "")

st.markdown(f"<h1>📊 {title}</h1><p style='color:#666;'>{city}地区 · 市场分析详情</p>", unsafe_allow_html=True)

# 数据来源说明
if city in ("全国",) or city not in ["北京", "上海", "广州", "深圳", "杭州", "天津", "成都", "武汉", "南京", "西安"]:
    st.info("""
    📍 **数据来源说明：** 当前展示的岗位包含 **Glassdoor 真实数据（美国）** 和 **LinkedIn 真实数据（美国）**。
    中国城市数据为基于真实市场模式生成的模拟数据。
    """)
else:
    st.info("""
    📍 **数据来源说明：** 中国城市数据为基于 Glassdoor 和 LinkedIn 真实岗位模式生成的 **高质量模拟数据**，
    包含真实的岗位名称、技能分布、薪资范围和市场趋势，可用于参考分析。
    """)

tab1, tab2, tab3, tab4 = st.tabs(["📋 市场总览", "🔧 技能图谱", "🏢 公司画像", "📝 简历匹配"])
with tab1: overview.render(city, title)
with tab2: skills.render(city, title)
with tab3: companies.render(city, title)
with tab4: resume_match.render(city, title, skills_str)

st.markdown("---")
if st.button("← 返回推荐"): st.switch_page("pages/01_recommend.py")
