"""简历匹配 Tab"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import plotly.graph_objects as go
from src.analyzer import get_jobs_by_title, resume_match_analysis
from src.config import SKILL_OPTIONS


def _skills_to_str(skills_list: list[str]) -> str:
    return ", ".join(skills_list)

def _str_to_skills(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]

def render(city: str, title: str, user_skills_str: str):
    st.markdown("### 🛠️ 你的技能（从下方选择）")

    # 将首页传来的技能字符串转为列表，作为默认值
    default_selected = _str_to_skills(user_skills_str) if user_skills_str.strip() else []

    selected_skills = st.multiselect(
        "选择你掌握的技能",
        options=SKILL_OPTIONS,
        default=default_selected,
        placeholder="搜索或选择技能...",
        label_visibility="collapsed",
        key=f"skills_multiselect_{title}",
    )

    if not selected_skills:
        st.info("💡 在上方选择你掌握的技能，即可查看与该岗位的匹配度分析")
        st.markdown("""
        <div style='background:#e8f4fd;padding:1rem;border-radius:8px;'>
        <b>提示：</b> 从下拉列表中选择技能，可多选
        </div>
        """, unsafe_allow_html=True)
        return

    user_skills = selected_skills
    df = get_jobs_by_title(title, city)
    if df.empty: st.warning("暂无该岗位数据"); return

    analysis = resume_match_analysis(user_skills, df)
    match_rate = analysis["match_rate"]

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("### 🎯 匹配度")
        bar_color = "#28a745" if match_rate >= 60 else "#ffc107" if match_rate >= 30 else "#dc3545"
        fig = go.Figure(go.Indicator(mode="gauge+number", value=match_rate, domain={"x": [0, 1], "y": [0, 1]}, title={"text": f"对 {title}"}, gauge={"axis": {"range": [0, 100]}, "bar": {"color": bar_color}, "steps": [{"range": [0, 30], "color": "#f8d7da"}, {"range": [30, 60], "color": "#fff3cd"}, {"range": [60, 100], "color": "#d4edda"}]}))
        fig.update_layout(height=300, margin=dict(l=30, r=30, t=50, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📊 匹配详情")
        st.markdown(f"- **需求量 Top {analysis['total_required']} 技能**\n- ✅ 已掌握: **{analysis['total_matched']}** 项\n- ❌ 待补充: **{analysis['total_required'] - analysis['total_matched']}** 项")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ✅ 已掌握技能")
        if analysis["matched_skills"]:
            for skill in analysis["matched_skills"]:
                st.markdown(f"<span style='background:#d4edda;padding:2px 12px;border-radius:12px;margin:2px;display:inline-block;'>{skill} ✅</span>", unsafe_allow_html=True)
        else: st.warning("暂未匹配到需求技能")
    with col2:
        st.markdown("### ❌ 待补充技能")
        if analysis["missing_skills"]:
            for skill in analysis["missing_skills"]:
                st.markdown(f"<span style='background:#f8d7da;padding:2px 12px;border-radius:12px;margin:2px;display:inline-block;'>{skill} ❌</span>", unsafe_allow_html=True)
        else: st.success("🎉 你已掌握所有核心需求技能！")

    st.markdown("---")
    st.markdown("### 📚 学习优先级建议")
    if analysis["missing_skills"]:
        for i, skill in enumerate(analysis["missing_skills"][:5], 1):
            st.markdown(f"{i}. **{skill}** — 该技能在 '{title}' 岗位需求中排名靠前，建议优先学习")
    else: st.success("🎉 你的技能与该岗位高度匹配！")
