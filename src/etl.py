"""ETL 数据管道：数据加载、清洗、模拟数据生成、数据库构建"""

import re
import sqlite3
import random
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.config import (
    ROOT,
    DATA_RAW,
    DB_PATH,
    CITY_DISTRICT_MAP,
    EDUCATION_ORDER,
    EXPERIENCE_ORDER,
    MAJOR_KEYWORDS,
    SALARY_BINS,
    SALARY_LABELS,
)

# ─────────────────────────────────────────────
# 1. 数据清洗函数
# ─────────────────────────────────────────────

# 常见列名映射（统一为标准列名）
COLUMN_ALIASES: dict[str, str] = {
    # --- Title ---
    "title": "title",
    "Job Title": "title",
    "job_title": "title",
    "职位": "title",
    "岗位": "title",
    "岗位名称": "title",
    "职位名称": "title",
    # --- Company ---
    "company": "company",
    "Company Name": "company",
    "company_name": "company",
    "公司": "company",
    "公司名称": "company",
    "企业": "company",
    # --- Location ---
    "location": "location",
    "Location": "location",
    "地区": "location",
    "城市": "location",
    "工作地点": "location",
    "所在地": "location",
    # --- Description ---
    "description": "description",
    "Description": "description",
    "Job Description": "description",
    "job_description": "description",
    "描述": "description",
    "职位描述": "description",
    "岗位描述": "description",
    # --- Requirements ---
    "requirements": "requirements",
    "skill": "requirements",
    "skills": "requirements",
    "skills_desc": "requirements",
    "Skills": "requirements",
    "要求": "requirements",
    "任职要求": "requirements",
    "岗位要求": "requirements",
    # --- Salary ---
    "salary": "salary",
    "Salary": "salary",
    "Salary Estimate": "salary",
    "med_salary": "salary",
    "min_salary": "salary",
    "max_salary": "salary",
    "normalized_salary": "salary",
    "薪资": "salary",
    "薪酬": "salary",
    "待遇": "salary",
    # --- Education ---
    "education": "education",
    "Education": "education",
    "学历": "education",
    "学历要求": "education",
    # --- Experience ---
    "experience": "experience",
    "Experience": "experience",
    "formatted_experience_level": "experience",
    "经验": "experience",
    "经验要求": "experience",
    "工作经验": "experience",
    # --- Industry ---
    "industry": "industry",
    "Industry": "industry",
    "行业": "industry",
    "领域": "industry",
}

# 学历标准化映射
EDUCATION_MAP = {
    "不限": "不限",
    "大专": "大专",
    "本科": "本科",
    "硕士": "硕士",
    "博士": "博士",
    "高中": "不限",
    "中专": "大专",
    "专科": "大专",
    "研究生": "硕士",
    "及以上": "",
}

# 经验标准化映射
EXPERIENCE_MAP = {
    "应届": "应届",
    "应届生": "应届",
    "1年以下": "1年以下",
    "1年": "1年以下",
    "1-3年": "1-3年",
    "1-3": "1-3年",
    "3-5年": "3-5年",
    "3-5": "3-5年",
    "5-10年": "5-10年",
    "5-10": "5-10年",
    "10年以上": "10年以上",
    "10年": "10年以上",
    "10年+": "10年以上",
    "经验不限": "不限",
    "无经验": "应届",
}


def load_raw_data(csv_name: str) -> pd.DataFrame:
    """从 CSV 加载原始数据，统一列名。

    Args:
        csv_name: CSV 文件名（相对于 DATA_RAW 目录）

    Returns:
        列名统一后的 DataFrame
    """
    csv_path = DATA_RAW / csv_name
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")

    df = pd.read_csv(csv_path)

    # 统一列名：将原列名映射到标准列名
    rename_map = {}
    for col in df.columns:
        col_stripped = col.strip()
        if col_stripped in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[col_stripped]

    df = df.rename(columns=rename_map)

    # 只保留标准列
    standard_columns = [
        "title", "company", "location", "description",
        "requirements", "salary", "education", "experience", "industry",
    ]
    keep_cols = [c for c in standard_columns if c in df.columns]
    return df[keep_cols]


def _parse_salary(s: str) -> Optional[float]:
    """将薪资字符串解析为月薪均值（单位：K）。

    支持的格式：
        - "15-25K"       -> 20.0
        - "15K-25K"      -> 20.0
        - "20-30万/年"   -> 20.83
        - "20万/年"      -> 16.67
        - "面议" / 空值   -> NaN
        - "20K以上"      -> 25.0 (取最低值 + 5K 估算)

    Returns:
        月薪均值（K），无法解析时返回 None
    """
    if not isinstance(s, str) or not s.strip():
        return None

    s = s.strip()

    # 处理 "面议"、"薪资面议" 等
    if "面议" in s or s in ("", "无"):
        return None

    # 处理 "20K以上" / "25K以上" 等
    above_match = re.search(r"(\d+(?:\.\d+)?)\s*K?\s*以上", s)
    if above_match:
        base = float(above_match.group(1))
        return base + 5.0  # 估算：最低值 + 5K

    # 处理 "20-30万/年"、"15-25万/年"
    year_match = re.search(r"(\d+(?:\.\d+)?)\s*[-~]\s*(\d+(?:\.\d+)?)\s*万/年", s)
    if year_match:
        low = float(year_match.group(1)) * 10000 / 12 / 1000  # 万/年 -> K/月
        high = float(year_match.group(2)) * 10000 / 12 / 1000
        return round((low + high) / 2, 2)

    # 处理 "20万/年"（单一值年包）
    single_year_match = re.search(r"(\d+(?:\.\d+)?)\s*万/年", s)
    if single_year_match:
        val = float(single_year_match.group(1)) * 10000 / 12 / 1000
        return round(val, 2)

    # 处理 "15-25K" / "15K-25K" / "15K-25K"
    month_match = re.search(r"(\d+(?:\.\d+)?)\s*K?\s*[-~]\s*(\d+(?:\.\d+)?)\s*K?", s)
    if month_match:
        low = float(month_match.group(1))
        high = float(month_match.group(2))
        return round((low + high) / 2, 2)

    # 处理 "20K" / "20k"（单一值）
    single_k_match = re.search(r"(\d+(?:\.\d+)?)\s*K", s)
    if single_k_match:
        return float(single_k_match.group(1))

    # 尝试直接提取数字作为月薪 K
    num_match = re.search(r"(\d+(?:\.\d+)?)", s)
    if num_match:
        return float(num_match.group(1))

    return None


def _normalize_city(location: str) -> str:
    """将地点标准化为城市名。

    使用 CITY_DISTRICT_MAP 进行反向映射：
    - "北京海淀" -> "北京"
    - "天津市南开区" -> "天津"
    - "上海" -> "上海"（未在映射中的返回原值）
    - 空值 -> "天津"（默认）
    """
    if not isinstance(location, str) or not location.strip():
        return "天津"

    loc = location.strip()

    # 反向查找：如果 location 包含某个区的关键词，返回对应的城市
    for city, districts in CITY_DISTRICT_MAP.items():
        for district in districts:
            if district in loc:
                return city

    # 如果 location 本身就是城市名（直接匹配）
    for city in CITY_DISTRICT_MAP:
        if city in loc:
            return city

    # 如果包含"市"，提取城市名
    city_match = re.search(r"(\S+?)市", loc)
    if city_match:
        city_name = city_match.group(1)
        # 检查是否是已知城市
        for city in CITY_DISTRICT_MAP:
            if city_name in city or city in city_name:
                return city
        return city_name + "市"

    return loc


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """清洗 DataFrame 数据。

    - 删除重复行
    - 空值处理：title 为空则删除，其他字段填充默认值
    - 薪资解析：将 salary 文本转为数值列 salary_avg
    - 城市标准化：新增 city 列
    - 学历/经验标准化
    """
    df = df.copy()

    # 删除重复行
    df = df.drop_duplicates()

    # 删除 title 为空的行
    df = df.dropna(subset=["title"])

    # 填充空值
    df["company"] = df["company"].fillna("未知企业")
    df["location"] = df["location"].fillna("")
    df["description"] = df["description"].fillna("")
    df["requirements"] = df["requirements"].fillna("")
    df["salary"] = df["salary"].fillna("")
    df["education"] = df["education"].fillna("不限")
    df["experience"] = df["experience"].fillna("不限")
    df["industry"] = df["industry"].fillna("未知")

    # 薪资解析
    df["salary_avg"] = df["salary"].apply(_parse_salary)

    # 城市标准化
    df["city"] = df["location"].apply(_normalize_city)

    # 学历标准化
    def _norm_edu(e: str) -> str:
        if not isinstance(e, str):
            return "不限"
        e = e.strip()
        # 处理 "本科及以上" -> "本科"
        for key in ["博士", "硕士", "本科", "大专"]:
            if key in e:
                return key
        return "不限"

    df["education"] = df["education"].apply(_norm_edu)

    # 经验标准化
    def _norm_exp(e: str) -> str:
        if not isinstance(e, str):
            return "不限"
        e = e.strip()
        for key, val in EXPERIENCE_MAP.items():
            if key in e:
                return val
        return "不限"

    df["experience"] = df["experience"].apply(_norm_exp)

    return df


# ─────────────────────────────────────────────
# 2. 模拟数据生成
# ─────────────────────────────────────────────

# 岗位配置
JOB_TEMPLATES = [
    {
        "title": "数据分析师",
        "salary_range": ("8-15K", "12-20K", "15-25K"),
        "education_weights": {"本科": 0.6, "硕士": 0.3, "大专": 0.1},
        "experience_weights": {"1-3年": 0.35, "3-5年": 0.3, "应届": 0.2, "5-10年": 0.15},
        "industries": ["互联网", "金融", "电商", "医疗", "教育", "制造业", "咨询"],
        "descriptions": [
            "负责业务数据的收集、清洗和分析，为业务决策提供数据支持",
            "参与数据指标体系的搭建和维护，输出数据分析报告",
            "通过数据挖掘和分析，发现业务增长点和优化方向",
            "与业务团队协作，推动数据驱动决策落地",
        ],
        "requirements_list": [
            "熟练使用SQL、Python进行数据处理和分析",
            "熟悉Tableau、PowerBI等可视化工具",
            "具备良好的业务理解能力和沟通能力",
            "有统计学背景者优先",
        ],
    },
    {
        "title": "大数据开发工程师",
        "salary_range": ("15-25K", "20-30K", "25-40K"),
        "education_weights": {"本科": 0.7, "硕士": 0.25, "大专": 0.05},
        "experience_weights": {"1-3年": 0.25, "3-5年": 0.35, "5-10年": 0.3, "应届": 0.1},
        "industries": ["互联网", "金融", "电商", "通信", "物流", "制造业"],
        "descriptions": [
            "负责大数据平台的建设和维护",
            "设计和开发数据处理流程，保障数据可靠性和时效性",
            "优化大数据存储和计算引擎性能",
            "参与数据治理和数据质量建设",
        ],
        "requirements_list": [
            "精通Java或Scala，熟悉Hadoop/Spark生态系统",
            "熟悉Hive、HBase、Kafka等大数据组件",
            "有大规模数据处理经验",
            "熟悉数据仓库建模方法",
        ],
    },
    {
        "title": "数据挖掘工程师",
        "salary_range": ("15-25K", "20-35K", "25-45K"),
        "education_weights": {"硕士": 0.5, "本科": 0.4, "博士": 0.1},
        "experience_weights": {"1-3年": 0.2, "3-5年": 0.35, "5-10年": 0.35, "应届": 0.1},
        "industries": ["互联网", "金融", "电商", "广告", "游戏", "咨询"],
        "descriptions": [
            "利用机器学习算法挖掘海量数据中的模式和规律",
            "构建用户画像和推荐系统",
            "开发和优化风控模型和定价模型",
            "探索新的数据挖掘方法并落地应用",
        ],
        "requirements_list": [
            "精通机器学习算法，包括分类、回归、聚类等",
            "熟练使用Python和常见的ML/DL框架",
            "有数据挖掘竞赛经验者优先",
            "具备扎实的统计学基础",
        ],
    },
    {
        "title": "数据科学家",
        "salary_range": ("20-30K", "25-40K", "30-50K"),
        "education_weights": {"硕士": 0.5, "博士": 0.3, "本科": 0.2},
        "experience_weights": {"3-5年": 0.35, "5-10年": 0.4, "1-3年": 0.15, "10年以上": 0.1},
        "industries": ["互联网", "金融", "人工智能", "医疗", "科研", "咨询"],
        "descriptions": [
            "设计和实施A/B实验，评估产品策略效果",
            "构建统计模型和机器学习模型解决复杂业务问题",
            "推动数据科学方法论在团队内的应用",
            "与产品和技术团队协作，将数据分析转化为产品决策",
        ],
        "requirements_list": [
            "统计学、计算机、数学等相关专业硕士及以上学历",
            "精通Python/R和SQL，有扎实的统计分析能力",
            "有机器学习项目落地经验",
            "良好的英文文献阅读能力",
        ],
    },
    {
        "title": "BI工程师",
        "salary_range": ("10-18K", "15-25K", "18-30K"),
        "education_weights": {"本科": 0.7, "大专": 0.15, "硕士": 0.15},
        "experience_weights": {"1-3年": 0.35, "3-5年": 0.35, "应届": 0.2, "5-10年": 0.1},
        "industries": ["互联网", "金融", "零售", "制造业", "物流", "房地产"],
        "descriptions": [
            "负责BI报表平台和数据可视化建设",
            "设计和维护数据仓库，搭建数据集市",
            "响应业务部门的数据分析需求，提供数据产品支持",
            "提升数据查询效率和报表性能",
        ],
        "requirements_list": [
            "熟悉SQL和数据仓库建模理论",
            "掌握Tableau、PowerBI或FineBI等BI工具",
            "有ETL开发经验",
            "具备良好的需求分析和沟通能力",
        ],
    },
    {
        "title": "后端开发工程师",
        "salary_range": ("15-22K", "20-30K", "25-40K"),
        "education_weights": {"本科": 0.7, "硕士": 0.2, "大专": 0.1},
        "experience_weights": {"1-3年": 0.3, "3-5年": 0.35, "5-10年": 0.25, "应届": 0.1},
        "industries": ["互联网", "金融", "电商", "企业服务", "教育", "游戏"],
        "descriptions": [
            "负责后端服务的设计、开发和维护",
            "参与系统架构设计，保障系统高可用和高性能",
            "编写高质量的代码和单元测试",
            "与前端和产品团队协作，按时交付功能",
        ],
        "requirements_list": [
            "精通Java/Python/Go等至少一种后端语言",
            "熟悉Spring Boot/Django/FastAPI等框架",
            "熟悉MySQL、Redis等数据库技术",
            "了解微服务架构和分布式系统",
        ],
    },
    {
        "title": "算法工程师",
        "salary_range": ("20-30K", "25-40K", "30-50K"),
        "education_weights": {"硕士": 0.5, "博士": 0.3, "本科": 0.2},
        "experience_weights": {"3-5年": 0.35, "1-3年": 0.25, "5-10年": 0.3, "应届": 0.1},
        "industries": ["人工智能", "互联网", "金融", "自动驾驶", "安防", "医疗"],
        "descriptions": [
            "研究和开发机器学习/深度学习算法",
            "优化模型性能，推动算法在业务场景中的落地",
            "跟踪前沿技术，持续提升算法效果",
            "参与算法平台的建设和优化",
        ],
        "requirements_list": [
            "计算机、数学等相关专业硕士及以上学历",
            "精通Python，熟悉PyTorch/TensorFlow等框架",
            "在CV/NLP/推荐等方向有深入研究者优先",
            "有顶会论文发表经验者优先",
        ],
    },
    {
        "title": "数据仓库工程师",
        "salary_range": ("15-25K", "20-35K", "25-40K"),
        "education_weights": {"本科": 0.7, "硕士": 0.25, "大专": 0.05},
        "experience_weights": {"1-3年": 0.25, "3-5年": 0.35, "5-10年": 0.3, "应届": 0.1},
        "industries": ["互联网", "金融", "电商", "物流", "制造业", "通信"],
        "descriptions": [
            "负责数据仓库的规划设计、模型设计和开发",
            "建设高质量的数据基础，支撑数据分析与决策",
            "制定数据治理规范，保障数据质量和安全",
            "优化数仓ETL流程，提升数据处理效率",
        ],
        "requirements_list": [
            "熟悉数据仓库建模理论（星型/雪花模型）",
            "精通SQL，有大规模SQL优化经验",
            "熟练使用Hive、Spark等大数据技术",
            "有数据治理和数据质量经验者优先",
        ],
    },
]

# 公司名称
COMPANY_NAMES = [
    "字节跳动", "阿里巴巴", "腾讯", "百度", "京东", "美团", "小米",
    "快手", "网易", "拼多多", "滴滴", "小红书", "哔哩哔哩",
    "华为", "中兴通讯", "联想", "海康威视", "大疆创新",
    "中国平安", "招商银行", "蚂蚁集团", "中信证券", "工商银行",
    "中科曙光", "浪潮信息", "用友网络", "金蝶国际", "恒生电子",
    "科大讯飞", "商汤科技", "旷视科技", "第四范式", "依图科技",
    "天津飞腾", "天津麒麟", "天津超算中心", "中科蓝鲸",
    "南开大学", "天津大学",
]

# 城市列表（天津占比较大）
CITIES = [
    "天津", "天津", "天津", "天津", "天津",  # 天津占比高
    "北京", "北京", "北京",
    "上海", "上海",
    "深圳", "广州", "杭州", "成都", "武汉",
    "南京", "西安", "长沙", "重庆", "厦门",
]


def _weighted_choice(options, weights):
    """根据权重随机选择"""
    total = sum(weights)
    r = random.random() * total
    cumulative = 0
    for opt, w in zip(options, weights):
        cumulative += w
        if r < cumulative:
            return opt
    return options[-1]


def generate_sample_data(n: int = 5000) -> pd.DataFrame:
    """生成模拟招聘数据。

    Args:
        n: 生成记录数，默认 5000

    Returns:
        包含模拟招聘数据的 DataFrame
    """
    random.seed(42)
    np.random.seed(42)

    records = []
    for _ in range(n):
        # 随机选择一个岗位模板
        template = random.choice(JOB_TEMPLATES)
        title = template["title"]

        # 公司
        company = random.choice(COMPANY_NAMES)

        # 城市
        city = random.choice(CITIES)
        # 生成具体地点（含区级信息）
        if city == "天津":
            district = random.choice(CITY_DISTRICT_MAP["天津"][1:])  # 非 "天津" 本身
            location = f"天津市{district}区"
        elif city == "北京":
            district = random.choice(CITY_DISTRICT_MAP["北京"][1:])
            location = f"北京市{district}区"
        else:
            location = city

        # 薪资
        salary_str = random.choice(template["salary_range"])

        # 学历
        edu_keys = list(template["education_weights"].keys())
        edu_weights = list(template["education_weights"].values())
        education = _weighted_choice(edu_keys, edu_weights)

        # 经验
        exp_keys = list(template["experience_weights"].keys())
        exp_weights = list(template["experience_weights"].values())
        experience = _weighted_choice(exp_keys, exp_weights)

        # 行业
        industry = random.choice(template["industries"])

        # 描述和要求
        description = random.choice(template["descriptions"])
        num_reqs = random.randint(2, 4)
        reqs = random.sample(template["requirements_list"], num_reqs)
        requirements = "; ".join(reqs)

        records.append({
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "requirements": requirements,
            "salary": salary_str,
            "education": education,
            "experience": experience,
            "industry": industry,
        })

    df = pd.DataFrame(records)

    # 应用清洗
    df = clean_data(df)

    return df


# ─────────────────────────────────────────────
# 3. 数据库构建
# ─────────────────────────────────────────────

def build_database(df: pd.DataFrame, db_path: Optional[Path] = None) -> None:
    """将 DataFrame 写入 SQLite 数据库。

    创建 jobs, companies, skills, major_keywords 四张表。

    Args:
        df: 清洗后的数据
        db_path: 数据库文件路径，默认使用 config.DB_PATH
    """
    if db_path is None:
        db_path = DB_PATH

    # 确保父目录存在
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))

    # 写入数据
    df.to_sql("jobs", conn, if_exists="replace", index=False)

    # 创建索引以加速查询
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON jobs(title)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_city ON jobs(city)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_education ON jobs(education)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_experience ON jobs(experience)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_salary ON jobs(salary_avg)")

    # ── companies 表：从 jobs 去重提取 ──
    cursor.execute("DROP TABLE IF EXISTS companies")
    cursor.execute("""
        CREATE TABLE companies AS
        SELECT DISTINCT company, industry FROM jobs
        WHERE company IS NOT NULL AND company != ''
        ORDER BY company
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_name ON companies(company)")

    # ── skills 表：预定义常见技能列表 ──
    skills = [
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
    cursor.execute("DROP TABLE IF EXISTS skills")
    cursor.execute("""
        CREATE TABLE skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT
        )
    """)
    for skill in skills:
        # 粗略分类
        if skill in ("Python", "SQL", "Java", "Scala", "Go", "R"):
            category = "编程语言"
        elif skill in ("Hadoop", "Spark", "Flink", "Kafka", "Hive", "HBase"):
            category = "大数据组件"
        elif skill in ("Tableau", "PowerBI", "FineBI", "Superset"):
            category = "可视化工具"
        elif skill in ("MySQL", "PostgreSQL", "Oracle", "MongoDB", "Redis"):
            category = "数据库"
        elif skill in ("PyTorch", "TensorFlow", "Scikit-learn", "XGBoost"):
            category = "机器学习框架"
        elif skill in ("Docker", "Kubernetes", "Linux", "Git"):
            category = "工程工具"
        elif skill in ("Airflow", "DataX", "SeaTunnel", "DolphinScheduler"):
            category = "调度工具"
        elif skill in ("StarRocks", "ClickHouse", "Doris"):
            category = "OLAP引擎"
        else:
            category = "通用技能"
        cursor.execute(
            "INSERT OR IGNORE INTO skills (name, category) VALUES (?, ?)",
            (skill, category),
        )

    # ── major_keywords 表：从 config.MAJOR_KEYWORDS 写入 ──
    cursor.execute("DROP TABLE IF EXISTS major_keywords")
    cursor.execute("""
        CREATE TABLE major_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            major TEXT NOT NULL,
            keyword TEXT NOT NULL,
            type TEXT NOT NULL
        )
    """)
    for major, (exact_list, broad_list) in MAJOR_KEYWORDS.items():
        for kw in exact_list:
            cursor.execute(
                "INSERT INTO major_keywords (major, keyword, type) VALUES (?, ?, 'exact')",
                (major, kw),
            )
        for kw in broad_list:
            cursor.execute(
                "INSERT INTO major_keywords (major, keyword, type) VALUES (?, ?, 'broad')",
                (major, kw),
            )

    conn.commit()
    conn.close()

    print(f"数据库已创建: {db_path}")
    print(f"   共写入 {len(df)} 条记录")
    print(f"   companies: {df[['company', 'industry']].drop_duplicates().shape[0]} 条")
    print(f"   skills: {len(skills)} 条")
    total_kw = sum(len(e) + len(b) for e, b in MAJOR_KEYWORDS.values())
    print(f"   major_keywords: {total_kw} 条")


# ─────────────────────────────────────────────
# 4. 主入口
# ─────────────────────────────────────────────

def run_etl(
    use_sample: bool = True,
    sample_size: int = 5000,
    csv_name: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> pd.DataFrame:
    """ETL 主入口。

    Args:
        use_sample: 是否使用模拟数据
        sample_size: 模拟数据条数
        csv_name: CSV 文件名（仅 use_sample=False 时使用）
        db_path: 数据库路径

    Returns:
        清洗后的 DataFrame
    """
    if use_sample:
        print(f"生成模拟数据 ({sample_size} 条)...")
        df = generate_sample_data(n=sample_size)
    else:
        if csv_name is None:
            raise ValueError("使用真实数据时必须指定 csv_name")
        print(f"加载原始数据: {csv_name}")
        df = load_raw_data(csv_name)
        print(f"清洗数据...")
        df = clean_data(df)

    print(f"构建数据库...")
    build_database(df, db_path=db_path)

    # 打印统计摘要
    print("\n数据统计摘要:")
    print(f"   岗位数量: {df['title'].nunique()}")
    print(f"   城市数量: {df['city'].nunique()}")
    print(f"   薪资范围: {df['salary_avg'].min():.1f}K ~ {df['salary_avg'].max():.1f}K")

    return df


if __name__ == "__main__":
    run_etl()


def import_csv_to_db(csv_path: str | Path, db_path: Optional[Path] = None) -> dict:
    """从 CSV 文件导入真实招聘数据到数据库。

    Args:
        csv_path: CSV 文件路径
        db_path: 目标数据库路径，默认使用 config.DB_PATH

    Returns:
        导入结果统计: {"status": "ok"/"error", "records": n, "message": "..."}
    """
    try:
        print(f"加载 CSV: {csv_path}")
        df = pd.read_csv(csv_path)

        # 统一列名
        df = df.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in df.columns})

        # 检查必需列
        required_cols = ["title", "location"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            # 尝试从已有列名猜测
            available = list(df.columns)
            return {
                "status": "error",
                "records": 0,
                "message": f"缺少必需列: {', '.join(missing)}\nCSV 中的列: {', '.join(available)}",
            }

        # 清洗
        df = clean_data(df)

        # 过滤无城市数据
        before = len(df)
        df = df[df["city"] != "未知"]
        after = len(df)
        if after == 0:
            return {"status": "error", "records": 0,
                    "message": "所有数据都无法识别城市，请检查 location 列是否包含城市名"}

        # 构建数据库（追加模式）
        build_database(df, db_path=db_path)

        return {
            "status": "ok",
            "records": after,
            "filtered": before - after,
            "message": f"成功导入 {after} 条记录（{before - after} 条因城市无法识别被过滤）",
        }
    except Exception as e:
        return {"status": "error", "records": 0, "message": f"导入失败: {str(e)}"}
