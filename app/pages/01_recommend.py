"""岗位推荐结果页"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from src.config import CITIES
from src.analyzer import get_jobs_by_title, resume_match_analysis

st.set_page_config(page_title="推荐结果", page_icon="🎯", layout="wide")

if "recommendations" not in st.session_state or st.session_state.recommendations is None:
    st.warning("请先在首页输入专业和地区")
    if st.button("← 返回首页"):
        st.switch_page("main.py")
    st.stop()

recs = st.session_state.recommendations
major = st.session_state.get("major", "")
city = st.session_state.get("city", "")
skills_list = st.session_state.get("skills_list", [])
skill_text = f" · 已选 {len(skills_list)} 项技能" if skills_list else " · 未选技能（可在详情页填写）"

st.markdown(f"""<div style='padding: 0.5rem 0;'>
    <h1>🎯 为你推荐的岗位方向</h1>
    <p style='color: #666; font-size: 1.1rem;'>
        {major} · {city}{skill_text}
    </p>
</div>""", unsafe_allow_html=True)

if not recs:
    st.warning(f"在 {city} 暂未找到与 {major} 匹配度较高的岗位数据")
    if st.button("← 返回重新搜索"):
        st.switch_page("main.py")
    st.stop()

st.markdown("### 📊 按专业匹配度排序")

for i, rec in enumerate(recs):
    score_color = "#28a745" if rec["score"] >= 60 else "#ffc107" if rec["score"] >= 30 else "#dc3545"

    with st.container(border=True):
        cols = st.columns([3, 1, 1, 1, 2])
        with cols[0]:
            st.markdown(f"#### {rec['title']}")
        with cols[1]:
            st.markdown(f"<h3 style='color: {score_color}; text-align: center;'>{rec['score']}%</h3>",
                       unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #888; font-size:0.8rem;'>专业匹配度</p>", unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"<h3 style='text-align: center;'>{rec['count']}</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #888;'>岗位数</p>", unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f"<h3 style='text-align: center;'>{rec['avg_salary']}K</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #888;'>平均薪资</p>", unsafe_allow_html=True)
        with cols[4]:
            if st.button(f"📊 查看详情", key=f"detail_{i}"):
                st.session_state.selected_title = rec["title"]
                st.switch_page("pages/02_detail.py")

        # 技能匹配度预览（如果用户选了技能）
        if skills_list:
            try:
                df = get_jobs_by_title(rec["title"], city if city != "全国" else "北京")
                skill_match = resume_match_analysis(skills_list, df)
                srate = skill_match["match_rate"]
                scolor = "#28a745" if srate >= 60 else "#ffc107" if srate >= 30 else "#dc3545"
                st.markdown(f"<p><b>🎯 技能匹配度：</b> <span style='color:{scolor};font-weight:bold;'>{srate}%</span> "
                           f"（已掌握 {skill_match['total_matched']}/{skill_match['total_required']} 项核心技能）"
                           f"<span style='color:#999;font-size:0.8rem;'>  → 点击查看详情看完整对比</span></p>",
                           unsafe_allow_html=True)
            except Exception:
                pass  # 兼容无数据的情况

        skills_html = " ".join(
            [f"<span style='background: #e9ecef; padding: 2px 10px; border-radius: 12px; "
             f"font-size: 0.85rem; margin: 0 3px;'>{s}</span>" for s in rec["top_skills"]]
        )
        st.markdown(f"<p><b>核心技能：</b> {skills_html}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {score_color};'><b>推荐理由：</b> {rec['reason']}</p>",
                   unsafe_allow_html=True)

if st.button("← 返回首页重新搜索"):
    st.switch_page("main.py")
