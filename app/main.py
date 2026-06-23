"""招聘市场智能分析工具 - Streamlit 入口"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from src.config import DEFAULT_MAJOR, DEFAULT_CITY, MAJORS, CITIES
from src.matcher import recommend_positions

st.set_page_config(
    page_title="招聘市场智能分析",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 侧边栏导航
with st.sidebar:
    st.markdown("### 🎯 导航")
    if st.button("🏠 首页", use_container_width=True):
        st.switch_page("main.py")
    if st.button("🗄️ 数据管理", use_container_width=True):
        st.switch_page("pages/03_data_manage.py")
    st.markdown("---")
    st.markdown("**当前版本:** v0.1.0")
    st.markdown("**数据量:** 预置5000条模拟数据")

# 初始化 Session State
if "major" not in st.session_state:
    st.session_state.major = ""
if "city" not in st.session_state:
    st.session_state.city = ""
if "skills" not in st.session_state:
    st.session_state.skills = ""
if "recommendations" not in st.session_state:
    st.session_state.recommendations = None
if "selected_title" not in st.session_state:
    st.session_state.selected_title = ""

# 标题区域
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0 1rem 0;'>
        <h1>🎯 招聘市场智能分析</h1>
        <p style='font-size: 1.2rem; color: #666;'>
            输入你的专业和地区，系统自动推荐最适合的岗位方向
        </p>
    </div>
    """, unsafe_allow_html=True)

# 输入区域
with st.container():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("input_form"):
            major = st.selectbox("📚 你的专业", options=["其他"] + MAJORS,
                                 index=MAJORS.index(DEFAULT_MAJOR) + 1 if DEFAULT_MAJOR in MAJORS else 0,
                                 help="选择你的专业，未列出可选「其他」手动输入")
            if major == "其他":
                major = st.text_input("请手动输入专业名称", value="",
                                      placeholder="如：统计学、信息管理与信息系统")

            city = st.selectbox("📍 目标地区", options=["全国"] + CITIES,
                                index=CITIES.index(DEFAULT_CITY) + 1,
                                help="选择你想找工作的城市，选「全国」查看所有地区")
            skills = st.text_input("🛠️ 你的技能（可选）", placeholder="Python, SQL, Spark, ...",
                                   help="用逗号分隔你掌握的技能，用于简历匹配分析")

            submitted = st.form_submit_button("🚀 开始分析", use_container_width=True)

            if submitted:
                if not major.strip():
                    st.error("请输入专业名称")
                elif not city.strip():
                    st.error("请输入目标地区")
                else:
                    with st.spinner("🔍 正在分析市场数据..."):
                        recs = recommend_positions(major.strip(), city.strip())
                        st.session_state.major = major.strip()
                        st.session_state.city = city.strip()
                        st.session_state.skills = skills.strip()
                        st.session_state.recommendations = recs
                        st.session_state.selected_title = ""
                        st.switch_page("pages/01_recommend.py")

# 底部信息
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #999; font-size: 0.9rem;'>
    💡 数据基于公开招聘数据集分析 · 仅供求职参考
</div>
""", unsafe_allow_html=True)
