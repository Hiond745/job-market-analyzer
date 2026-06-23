"""技能图谱 Tab"""
import streamlit as st
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from src.analyzer import get_jobs_by_title, skill_demand

def render(city: str, title: str):
    df = get_jobs_by_title(title, city)
    skills_df = skill_demand(df, top_n=20)
    if skills_df.empty: st.info("暂无技能数据"); return

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("### 📊 Top 20 需求技能")
        fig = px.bar(skills_df.head(20), x="count", y="skill", orientation="h",
                     labels={"count": "出现次数", "skill": ""}, color="count", color_continuous_scale="Viridis")
        fig.update_layout(height=500, margin=dict(l=0, r=0, t=20, b=0), yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("### ☁️ 技能词云")
        word_freq = dict(zip(skills_df["skill"].head(30), skills_df["count"].head(30)))
        if word_freq:
            wc = WordCloud(width=400, height=350, background_color="white", max_words=30, colormap="viridis").generate_from_frequencies(word_freq)
            fig, ax = plt.subplots(figsize=(4, 3.5))
            ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
            st.pyplot(fig)
        else: st.info("词云数据不足")
