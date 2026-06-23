"""岗位匹配引擎：根据专业关键词对岗位进行智能匹配与排序。"""

import sqlite3
from typing import Any

import pandas as pd

from src.config import DB_PATH, MAJOR_KEYWORDS

# 常见技能关键词列表（用于技能提取）
COMMON_SKILLS = [
    "Python", "SQL", "Java", "Scala", "Go", "R",
    "Hadoop", "Spark", "Flink", "Kafka", "Hive", "HBase",
    "Tableau", "PowerBI", "FineBI", "Superset",
    "MySQL", "PostgreSQL", "Oracle", "MongoDB", "Redis",
    "PyTorch", "TensorFlow", "Scikit-learn", "XGBoost",
    "Docker", "Kubernetes", "Linux", "Git",
    "Airflow", "DataX", "SeaTunnel", "DolphinScheduler",
    "StarRocks", "ClickHouse", "Doris",
    "机器学习", "深度学习", "统计分析", "数据建模", "数据治理",
    "ETL开发", "数据仓库", "数据可视化",
]


def get_all_jobs() -> pd.DataFrame:
    """从 SQLite 读取所有岗位数据。

    Returns:
        DataFrame，包含 jobs 表的所有列
    """
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query("SELECT * FROM jobs", conn)
    conn.close()
    return df


def get_city_jobs(df: pd.DataFrame, city: str) -> pd.DataFrame:
    """按城市筛选岗位数据。

    Args:
        df: 完整岗位 DataFrame
        city: 城市名称，传入「全国」返回全部数据

    Returns:
        筛选后的 DataFrame
    """
    if city == "全国":
        return df.copy()
    return df[df["city"] == city].copy()


def _fuzzy_match_major(major: str) -> tuple[str, list[str], list[str]] | None:
    """模糊匹配专业名称，返回 (专业名, title_keywords, broad_keywords)。

    支持子串包含匹配：
    - "数据科学" 可匹配到 "数据科学与大数据技术"
    - 已知专业名包含输入字符串也视为匹配

    Args:
        major: 输入的专业名称

    Returns:
        匹配到的 (专业名, title_keywords列表, broad_keywords列表)，未匹配到返回 None
    """
    if not major or not isinstance(major, str):
        return None

    major = major.strip()

    # 1. 精确匹配
    if major in MAJOR_KEYWORDS:
        title_kw, broad_kw = MAJOR_KEYWORDS[major]
        return major, title_kw, broad_kw

    # 2. 子串包含匹配
    for known_major, (title_kw, broad_kw) in MAJOR_KEYWORDS.items():
        if major in known_major or known_major in major:
            return known_major, title_kw, broad_kw

    # 3. 部分匹配（输入与已知专业有重叠关键词）
    for known_major, (title_kw, broad_kw) in MAJOR_KEYWORDS.items():
        known_parts = set(known_major.replace("与", " ").replace("和", " ").split())
        input_parts = set(major.replace("与", " ").replace("和", " ").split())
        if known_parts & input_parts:
            return known_major, title_kw, broad_kw

    return None


def _extract_top_skills(reqs_text: str, top_n: int = 5) -> list[str]:
    """从需求文本中提取出现频率最高的技能。

    Args:
        reqs_text: 拼接后的需求文本
        top_n: 返回的技能数量

    Returns:
        Top N 技能名称列表
    """
    if not reqs_text or not isinstance(reqs_text, str):
        return []

    skill_counts: dict[str, int] = {}
    for skill in COMMON_SKILLS:
        count = reqs_text.lower().count(skill.lower())
        if count > 0:
            skill_counts[skill] = count

    sorted_skills = sorted(skill_counts.items(), key=lambda x: (-x[1], x[0]))
    return [skill for skill, _ in sorted_skills[:top_n]]


def _generate_reason(title: str, score: float) -> str:
    """根据岗位名称和匹配度生成匹配理由。

    Args:
        title: 岗位名称
        score: 匹配度（0-100）

    Returns:
        匹配理由文案
    """
    if score >= 80:
        level = "高度匹配"
    elif score >= 60:
        level = "良好匹配"
    elif score >= 40:
        level = "中等匹配"
    else:
        level = "基础匹配"

    return (
        f"{title}与你的专业{level}，"
        f"岗位技能要求与专业所学内容有较好的对应关系"
    )


def _fallback_recommendation(
    major: str,
    title_keywords: list[str],
    broad_keywords: list[str],
    top_n: int = 6,
) -> list[dict[str, Any]]:
    """当目标城市无数据时，使用全国数据进行推荐。

    Args:
        major: 专业名称
        title_keywords: 标题关键词列表
        broad_keywords: 描述关键词列表
        top_n: 返回结果数量

    Returns:
        推荐结果列表
    """
    df = get_all_jobs()
    return _compute_recommendations(df, title_keywords, broad_keywords, top_n)


def _compute_recommendations(
    df: pd.DataFrame,
    title_keywords: list[str],
    broad_keywords: list[str],
    top_n: int,
) -> list[dict[str, Any]]:
    """核心计算函数：对 DataFrame 中的岗位按标题分组并计算匹配度。

    Args:
        df: 岗位 DataFrame
        title_keywords: 标题关键词列表
        broad_keywords: 描述关键词列表
        top_n: 返回结果数量

    Returns:
        按匹配度排序的推荐列表
    """
    if df.empty:
        return []

    n_title_kw = len(title_keywords)
    n_broad_kw = len(broad_keywords)

    results: list[dict[str, Any]] = []

    # 按岗位名称分组
    for title, group in df.groupby("title"):
        # ── 标题匹配（最高 40 分） ──
        if n_title_kw > 0:
            title_matched = sum(
                1 for kw in title_keywords if kw.lower() in title.lower()
            )
            title_score = (title_matched / n_title_kw) * 40
        else:
            title_score = 0

        # ── 描述匹配（最高 60 分） ──
        all_reqs = " ".join(group["requirements"].fillna("").tolist())
        all_desc = " ".join(group["description"].fillna("").tolist())
        combined_text = all_reqs + " " + all_desc

        if n_broad_kw > 0:
            desc_matched = sum(
                1 for kw in broad_keywords if kw.lower() in combined_text.lower()
            )
            desc_score = (desc_matched / n_broad_kw) * 60
        else:
            desc_score = 0

        total_score = round(title_score + desc_score, 1)

        # ── 聚合统计 ──
        count = len(group)
        avg_salary = (
            round(group["salary_avg"].mean(), 1)
            if "salary_avg" in group.columns
            else 0
        )

        top_skills = _extract_top_skills(combined_text, top_n=5)
        reason = _generate_reason(title, total_score)

        results.append({
            "title": title,
            "score": total_score,
            "count": count,
            "avg_salary": avg_salary,
            "top_skills": top_skills,
            "reason": reason,
        })

    # 按匹配度降序排序，同分时按岗位数降序
    results.sort(key=lambda x: (-x["score"], -x["count"]))
    return results[:top_n]


def recommend_positions(
    major: str,
    city: str,
    top_n: int = 6,
) -> list[dict[str, Any]]:
    """核心推荐函数。

    根据专业和城市，返回按匹配度排序的岗位方向列表。

    Args:
        major: 专业名称（如 "数据科学与大数据技术"）
        city: 城市名称（如 "天津"）
        top_n: 返回结果数量

    Returns:
        按匹配度排序的岗位方向列表，每条包含：
        - title: 岗位名称
        - score: 匹配度（0-100）
        - count: 该岗位在目标城市的岗位数
        - avg_salary: 平均薪资
        - top_skills: Top 5 技能
        - reason: 匹配理由
    """
    # 1. 模糊匹配专业
    matched = _fuzzy_match_major(major)
    if matched is None:
        return []

    major_name, title_keywords, broad_keywords = matched

    # 2. 从数据库读取所有岗位
    df = get_all_jobs()

    # 3. 按城市筛选
    city_df = get_city_jobs(df, city)

    # 4. 如果目标城市无数据，回退到全国数据
    if city_df.empty:
        return _fallback_recommendation(
            major_name, title_keywords, broad_keywords, top_n
        )

    # 5. 计算推荐
    return _compute_recommendations(city_df, title_keywords, broad_keywords, top_n)
