"""市场分析引擎：提供岗位数据的多维统计分析与匹配评估。"""

import sqlite3
from typing import Any

import numpy as np
import pandas as pd

from src.config import DB_PATH, EDUCATION_ORDER, EXPERIENCE_ORDER

# 常见技能关键词列表（用于技能提取）
COMMON_SKILLS = [
    "Python", "SQL", "Java", "Spark", "Hadoop", "Flink", "Kafka", "Hive",
    "Tableau", "PowerBI", "Excel",
    "机器学习", "深度学习", "NLP", "CV",
    "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
    "统计学", "AB测试",
    "数据结构", "算法",
    "Linux", "Docker", "Kubernetes",
    "MongoDB", "Redis", "MySQL", "PostgreSQL",
    "Airflow", "ETL", "Git",
    "Go", "C++",
    "数据可视化", "特征工程", "模型部署", "微服务",
]


def get_jobs_by_title(title: str, city: str) -> pd.DataFrame:
    """按岗位名称和城市从 SQLite 查询数据。

    Args:
        title: 岗位名称
        city: 城市名称

    Returns:
        匹配的岗位 DataFrame
    """
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT * FROM jobs WHERE title = ? AND city = ?",
        conn,
        params=(title, city),
    )
    conn.close()
    return df


def job_market_overview(df: pd.DataFrame) -> dict[str, Any]:
    """岗位市场概览统计。

    Args:
        df: 岗位 DataFrame

    Returns:
        dict: total_count, avg_salary, salary_median, salary_min,
              salary_max, company_count
    """
    if df.empty:
        return {
            "total_count": 0,
            "avg_salary": 0.0,
            "salary_median": 0.0,
            "salary_min": 0.0,
            "salary_max": 0.0,
            "company_count": 0,
        }

    salaries = df["salary_avg"].dropna()
    return {
        "total_count": len(df),
        "avg_salary": round(salaries.mean(), 1),
        "salary_median": round(salaries.median(), 1),
        "salary_min": round(salaries.min(), 1),
        "salary_max": round(salaries.max(), 1),
        "company_count": df["company"].nunique(),
    }


def education_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """学历要求分布，按 EDUCATION_ORDER 排序。

    Args:
        df: 岗位 DataFrame

    Returns:
        DataFrame: education, count, proportion
    """
    if df.empty:
        return pd.DataFrame(columns=["education", "count", "proportion"])

    dist = df["education"].value_counts().reset_index()
    # 兼容新旧版 pandas 的列名
    col_name = "education" if "education" in dist.columns else dist.columns[0]
    dist.columns = ["education", "count"]

    # 按 EDUCATION_ORDER 排序，不在排序中的项排末尾
    dist["_order"] = dist["education"].apply(
        lambda x: EDUCATION_ORDER.index(x) if x in EDUCATION_ORDER else len(EDUCATION_ORDER)
    )
    dist = dist.sort_values("_order").drop(columns="_order").reset_index(drop=True)

    total = dist["count"].sum()
    dist["proportion"] = (dist["count"] / total * 100).round(1)
    return dist


def experience_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """经验要求分布，按 EXPERIENCE_ORDER 排序。

    Args:
        df: 岗位 DataFrame

    Returns:
        DataFrame: experience, count, proportion
    """
    if df.empty:
        return pd.DataFrame(columns=["experience", "count", "proportion"])

    dist = df["experience"].value_counts().reset_index()
    col_name = "experience" if "experience" in dist.columns else dist.columns[0]
    dist.columns = ["experience", "count"]

    dist["_order"] = dist["experience"].apply(
        lambda x: (
            EXPERIENCE_ORDER.index(x)
            if x in EXPERIENCE_ORDER
            else len(EXPERIENCE_ORDER)
        )
    )
    dist = dist.sort_values("_order").drop(columns="_order").reset_index(drop=True)

    total = dist["count"].sum()
    dist["proportion"] = (dist["count"] / total * 100).round(1)
    return dist


def skill_demand(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """从 requirements + description 文本统计常见技能出现频率。

    Args:
        df: 岗位 DataFrame
        top_n: 返回的技能数量，默认 20

    Returns:
        DataFrame: skill, count, proportion
    """
    if df.empty:
        return pd.DataFrame(columns=["skill", "count", "proportion"])

    # 拼接所有需求文本和描述文本
    reqs_text = " ".join(df["requirements"].fillna("").tolist())
    desc_text = " ".join(df["description"].fillna("").tolist())
    combined_text = (reqs_text + " " + desc_text).lower()

    total_jobs = len(df)
    skill_counts: dict[str, int] = {}
    for skill in COMMON_SKILLS:
        # 统计包含该技能的岗位数量
        skill_lower = skill.lower()
        count = sum(
            1 for text in df["requirements"].fillna("").tolist() + df["description"].fillna("").tolist()
            if skill_lower in text.lower()
        )
        if count > 0:
            skill_counts[skill] = count

    sorted_skills = sorted(skill_counts.items(), key=lambda x: (-x[1], x[0]))
    top = sorted_skills[:top_n]

    result = pd.DataFrame(top, columns=["skill", "count"])
    result["proportion"] = (result["count"] / total_jobs * 100).round(1)
    return result.reset_index(drop=True)


def top_companies(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """公司招聘数量排行。

    Args:
        df: 岗位 DataFrame
        top_n: 返回的公司数量，默认 10

    Returns:
        DataFrame: company, count
    """
    if df.empty:
        return pd.DataFrame(columns=["company", "count"])

    dist = df["company"].value_counts().head(top_n).reset_index()
    dist.columns = ["company", "count"]
    return dist.reset_index(drop=True)


def industry_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """行业分布。

    Args:
        df: 岗位 DataFrame

    Returns:
        DataFrame: industry, count, proportion
    """
    if df.empty:
        return pd.DataFrame(columns=["industry", "count", "proportion"])

    dist = df["industry"].value_counts().reset_index()
    dist.columns = ["industry", "count"]

    total = dist["count"].sum()
    dist["proportion"] = (dist["count"] / total * 100).round(1)
    return dist.reset_index(drop=True)


def salary_by_experience(df: pd.DataFrame) -> pd.DataFrame:
    """各经验段平均薪资。

    Args:
        df: 岗位 DataFrame

    Returns:
        DataFrame: experience, avg_salary, count
    """
    if df.empty:
        return pd.DataFrame(columns=["experience", "avg_salary", "count"])

    grouped = (
        df.groupby("experience")["salary_avg"]
        .agg(["mean", "count"])
        .reset_index()
    )
    grouped.columns = ["experience", "avg_salary", "count"]
    grouped["avg_salary"] = grouped["avg_salary"].round(1)

    # 按 EXPERIENCE_ORDER 排序
    grouped["_order"] = grouped["experience"].apply(
        lambda x: (
            EXPERIENCE_ORDER.index(x)
            if x in EXPERIENCE_ORDER
            else len(EXPERIENCE_ORDER)
        )
    )
    grouped = grouped.sort_values("_order").drop(columns="_order").reset_index(drop=True)
    return grouped


def resume_match_analysis(
    user_skills: list[str], df: pd.DataFrame
) -> dict[str, Any]:
    """简历匹配分析。

    从岗位的需求文本中提取 Top 15 需求技能，计算用户技能的匹配度。

    Args:
        user_skills: 用户技能列表，如 ["Python", "SQL", "Spark"]
        df: 某个岗位的数据 DataFrame

    Returns:
        dict: {
            match_rate: float,        # 匹配率（0-100）
            matched_skills: list[str], # 匹配上的技能
            missing_skills: list[str], # 缺失的技能
            total_required: int,       # 需求技能总数
            total_matched: int,        # 匹配技能数
        }
    """
    if df.empty or not user_skills:
        return {
            "match_rate": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "total_required": 0,
            "total_matched": 0,
        }

    # 拼接所有需求文本和描述文本
    reqs_text = " ".join(df["requirements"].fillna("").tolist())
    desc_text = " ".join(df["description"].fillna("").tolist())
    combined_text = (reqs_text + " " + desc_text).lower()

    # 统计常见技能在 JD 中的出现频率
    skill_counts: dict[str, int] = {}
    for skill in COMMON_SKILLS:
        count = combined_text.count(skill.lower())
        if count > 0:
            skill_counts[skill] = count

    # 取 Top 15 需求技能
    sorted_skills = sorted(skill_counts.items(), key=lambda x: (-x[1], x[0]))
    required_skills = [skill for skill, _ in sorted_skills[:15]]

    if not required_skills:
        return {
            "match_rate": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "total_required": 0,
            "total_matched": 0,
        }

    # 计算匹配
    user_skills_lower = {s.lower() for s in user_skills}
    matched = []
    missing = []
    for skill in required_skills:
        if skill.lower() in user_skills_lower:
            matched.append(skill)
        else:
            missing.append(skill)

    total_required = len(required_skills)
    total_matched = len(matched)
    match_rate = round(total_matched / total_required * 100, 1)

    return {
        "match_rate": match_rate,
        "matched_skills": matched,
        "missing_skills": missing,
        "total_required": total_required,
        "total_matched": total_matched,
    }
