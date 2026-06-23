"""招聘市场智能分析工具 - Streamlit 入口"""

import streamlit as st
from src.config import DEFAULT_MAJOR, DEFAULT_CITY
from src.matcher import recommend_positions

st.set_page_config(
    page_title="招聘市场智能分析",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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
            major = st.text_input("📚 你的专业", value=DEFAULT_MAJOR,
                                  help="输入你的专业全称，如：数据科学与大数据技术")
            city = st.text_input("📍 目标地区", value=DEFAULT_CITY,
                                 help="输入你想找工作的城市，如：天津、北京")
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
