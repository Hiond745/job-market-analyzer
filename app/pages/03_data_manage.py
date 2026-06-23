"""数据管理页面：导入真实数据集、查看数据库状态"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import pandas as pd
import streamlit as st
from src.config import DB_PATH
from src.etl import run_etl, import_csv_to_db

st.set_page_config(page_title="数据管理", page_icon="🗄️", layout="wide")

st.markdown("# 🗄️ 数据管理")
st.markdown("管理招聘数据集：导入真实 CSV 数据、查看数据库状态、重置数据。")

# ─────────────────────────────────────────────
# 数据库状态
# ─────────────────────────────────────────────
st.markdown("## 📊 当前数据库状态")

try:
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 总记录数
    cur.execute("SELECT COUNT(*) FROM jobs")
    total = cur.fetchone()[0]

    # 城市分布
    cur.execute("SELECT city, COUNT(*) as cnt FROM jobs GROUP BY city ORDER BY cnt DESC")
    cities = cur.fetchall()

    # 岗位分布
    cur.execute("SELECT title, COUNT(*) as cnt FROM jobs GROUP BY title ORDER BY cnt DESC")
    titles = cur.fetchall()

    # 薪资范围
    cur.execute("SELECT MIN(salary_avg), MAX(salary_avg), AVG(salary_avg) FROM jobs")
    salary_stats = cur.fetchone()

    conn.close()

    # 展示指标
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("📋 总岗位数", total)
    with col2: st.metric("🏙️ 覆盖城市", len(cities))
    with col3: st.metric("💼 岗位种类", len(titles))
    with col4: st.metric("💰 薪资范围", f"{salary_stats[0]:.0f}K ~ {salary_stats[1]:.0f}K")

    # 城市 + 岗位分布
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🏙️ 城市分布")
        city_df = pd.DataFrame(cities, columns=["城市", "岗位数"])
        st.dataframe(city_df, use_container_width=True, hide_index=True)
    with col2:
        st.markdown("#### 💼 岗位分布")
        title_df = pd.DataFrame(titles, columns=["岗位", "岗位数"])
        st.dataframe(title_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"无法读取数据库: {e}")
    st.info("请先生成模拟数据或导入 CSV。")

# ─────────────────────────────────────────────
# 导入 CSV
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown("## 📥 导入真实数据（CSV）")

st.markdown("""
### 数据格式要求
CSV 文件应包含以下列（中文/英文列名均可自动识别）：

| 必需列 | 可选列 |
|--------|--------|
| `title` / 岗位名称 / 职位 | `company` / 公司 |
| `location` / 城市 / 工作地点 | `salary` / 薪资 |
| | `description` / 职位描述 |
| | `requirements` / 技能要求 |
| | `education` / 学历要求 |
| | `experience` / 经验要求 |
| | `industry` / 行业 |

> **推荐数据集：** Kaggle 搜索 "Data Science Job Postings"、"LinkedIn Job Postings" 等
> 支持最多 **200MB** 的 CSV 文件
""")

with st.expander("📤 上传 CSV 文件", expanded=False):
    uploaded_file = st.file_uploader("选择 CSV 文件", type=["csv"], label_visibility="collapsed")

    if uploaded_file is not None:
        # 预览前 5 行
        try:
            preview_df = pd.read_csv(uploaded_file, nrows=5)
            st.markdown(f"**文件:** {uploaded_file.name}  |  **大小:** {uploaded_file.size / 1024:.1f} KB")
            st.markdown("**数据预览（前 5 行）:**")
            st.dataframe(preview_df, use_container_width=True)

            # 列名识别
            from src.etl import COLUMN_ALIASES
            recognized = []
            unrecognized = []
            for col in preview_df.columns:
                if col in COLUMN_ALIASES or col.lower() in [c.lower() for c in COLUMN_ALIASES]:
                    recognized.append(col)
                else:
                    unrecognized.append(col)

            if unrecognized:
                st.info(f"✅ 已识别列: {', '.join(recognized)}")
                st.warning(f"⚠️ 未自动识别的列（将被忽略）: {', '.join(unrecognized)}")
            else:
                st.success(f"✅ 所有列均已识别")

            # 导入按钮
            if st.button("🚀 导入数据", type="primary", use_container_width=True):
                uploaded_file.seek(0)
                with st.spinner("正在导入数据，请稍候..."):
                    # 保存上传文件到临时位置
                    temp_path = Path("data/raw") / uploaded_file.name
                    temp_path.parent.mkdir(parents=True, exist_ok=True)
                    temp_path.write_bytes(uploaded_file.getbuffer())

                    result = import_csv_to_db(str(temp_path))

                if result["status"] == "ok":
                    st.success(result["message"])
                    st.balloons()
                    st.info("数据已导入！请刷新页面查看更新后的统计。")
                else:
                    st.error(result["message"])

        except Exception as e:
            st.error(f"读取 CSV 失败: {e}")

# ─────────────────────────────────────────────
# 重置 / 重新生成数据
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🔄 重置数据")

col1, col2 = st.columns(2)
with col1:
    st.markdown("#### 重新生成模拟数据")
    sample_size = st.number_input("数据条数", min_value=100, max_value=50000, value=5000, step=1000)
    if st.button("🔄 重新生成", use_container_width=True):
        with st.spinner(f"正在生成 {sample_size} 条模拟数据..."):
            run_etl(use_sample=True, sample_size=sample_size)
        st.success(f"模拟数据已重新生成（{sample_size} 条）")
        st.info("请刷新页面查看更新。")

with col2:
    st.markdown("#### ⚠️ 危险操作")
    if st.button("🗑️ 清空所有数据", type="secondary", use_container_width=True):
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("DROP TABLE IF EXISTS jobs")
        conn.execute("DROP TABLE IF EXISTS companies")
        conn.execute("DROP TABLE IF EXISTS skills")
        conn.execute("DROP TABLE IF EXISTS major_keywords")
        conn.commit()
        conn.close()
        st.success("数据库已清空！请重新生成或导入数据。")

# 使用说明
st.markdown("---")
st.markdown("""
### 📖 使用说明

**场景一：使用真实数据**
1. 从 Kaggle 等平台下载招聘 CSV 数据集
2. 在本页面上传并导入
3. 导入完成后，返回首页使用真实数据进行分析

**场景二：使用模拟数据**
- 系统已预置 5000 条模拟数据，覆盖 10 个城市、8 种岗位
- 可直接在首页使用，适合体验功能和调试

> 💡 **数据保留：** 数据库文件位于 `data/database.db`，导入的真实数据和生成的模拟数据都保存在此文件中。
""")
