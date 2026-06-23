"""
数据迁移脚本：导入真实数据集 + 生成增强模拟数据
运行方式：python -m src.migrate_data
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re
import sqlite3
import random
from collections import Counter
import pandas as pd
import numpy as np

from src.config import DB_PATH, DATA_RAW, CITY_DISTRICT_MAP
from src.etl import build_database, clean_data, _parse_salary, COLUMN_ALIASES


def load_glassdoor() -> pd.DataFrame:
    """加载并清洗 Glassdoor 数据科学岗位数据集"""
    path = DATA_RAW / "glassdoor_ds_jobs.csv"
    if not path.exists():
        print("⚠️ Glassdoor 数据集未找到，跳过")
        return pd.DataFrame()

    df = pd.read_csv(path)

    # 列名映射
    mapper = {
        "Job Title": "title",
        "Salary Estimate": "salary",
        "Job Description": "description",
        "Company Name": "company",
        "Location": "location",
        "Industry": "industry",
        "Sector": "sector",
    }
    df = df.rename(columns={k: v for k, v in mapper.items() if k in df.columns})

    # 只保留需要的列
    keep = ["title", "salary", "description", "company", "location", "industry", "sector"]
    df = df[[c for c in keep if c in df.columns]]

    # 清洗
    df["salary"] = df["salary"].apply(_parse_salary)
    df["description"] = df["description"].fillna("")
    df["company"] = df["company"].fillna("未知企业")
    df["location"] = df["location"].fillna("")
    df["industry"] = df["industry"].fillna("")

    # 从 description 提取技能关键词作为 requirements
    common_skills = [
        "Python", "R", "SQL", "Java", "Scala", "Spark", "Hadoop",
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
        "TensorFlow", "PyTorch", "Scikit-learn", "Keras",
        "Statistics", "A/B Testing", "Experimental Design",
        "Data Visualization", "Tableau", "Power BI",
        "Pandas", "NumPy", "Excel",
        "Git", "Docker", "AWS", "GCP", "Azure",
    ]
    df["requirements"] = df["description"].apply(
        lambda desc: "; ".join(
            [s for s in common_skills if s.lower() in desc.lower()]
        ) if isinstance(desc, str) else ""
    )

    # 城市标准化
    df["city"] = df["location"].apply(lambda loc: loc.split(",")[0].strip() if isinstance(loc, str) and "," in loc else loc)

    # 添加虚拟字段
    df["education"] = "本科"
    df["experience"] = "1-3年"

    print(f"✅ Glassdoor: {len(df)} 条真实数据科学岗位")
    return df


def load_linkedin_sample() -> pd.DataFrame:
    """加载并清洗 LinkedIn 岗位数据集"""
    path = DATA_RAW / "linkedin_sample.csv"
    if not path.exists():
        print("⚠️ LinkedIn 数据集未找到，跳过")
        return pd.DataFrame()

    # 分块读取以节省内存
    chunks = []
    for chunk in pd.read_csv(path, chunksize=50000,
                              usecols=["title", "description", "med_salary", "min_salary",
                                        "max_salary", "location", "company_name",
                                        "formatted_experience_level", "skills_desc"]):
        chunk = chunk.dropna(subset=["title"])
        chunk = chunk[chunk["title"].str.strip() != ""]

        # 只保留数据/AI/开发相关的岗位
        keywords = ["data", "analyst", "analytics", "scientist", "engineer",
                     "machine learning", "deep learning", "ai", "artificial intelligence",
                     "business intelligence", "bi", "developer", "software",
                     "big data", "cloud", "devops", "ml", "nlp",
                     "数据", "分析", "开发", "算法"]
        mask = chunk["title"].str.lower().apply(
            lambda t: any(kw in t for kw in keywords)
        )
        chunk = chunk[mask].copy()

        if len(chunk) == 0:
            continue

        # 映射列名
        chunk["company"] = chunk["company_name"].fillna("")
        chunk["salary"] = chunk["med_salary"].fillna(
            chunk["min_salary"].fillna(0) + chunk["max_salary"].fillna(0)
        ).div(2)  # 取中位数或均值
        # LinkedIn 薪资是年薪，转为月薪 K
        chunk["salary"] = chunk["salary"] / 12 / 1000

        chunk["location"] = chunk["location"].fillna("")
        chunk["city"] = chunk["location"].apply(
            lambda loc: loc.split(",")[0].strip() if isinstance(loc, str) and "," in loc else loc
        )

        # 经验映射
        exp_map = {
            "Entry level": "应届",
            "Associate": "1年以下",
            "Mid-Senior level": "3-5年",
            "Director": "5-10年",
            "Executive": "10年以上",
            "Internship": "应届",
        }
        chunk["experience"] = chunk["formatted_experience_level"].map(exp_map).fillna("1-3年")

        chunk["education"] = "本科"
        chunk["requirements"] = chunk["skills_desc"].fillna("")
        chunk["description"] = chunk["description"].fillna("")
        chunk["industry"] = ""

        keep = ["title", "company", "location", "description",
                "requirements", "salary", "education", "experience", "industry", "city"]
        chunk = chunk[[c for c in keep if c in chunk.columns]]

        chunks.append(chunk)

    if not chunks:
        return pd.DataFrame()

    df = pd.concat(chunks, ignore_index=True)
    # 去重
    df = df.drop_duplicates(subset=["title", "company", "city"])
    print(f"✅ LinkedIn: {len(df)} 条真实岗位数据（数据/AI/开发相关）")
    return df


def generate_enhanced_china_data(n: int = 30000) -> pd.DataFrame:
    """基于真实数据模式，生成高质量的带中国城市的数据"""
    np.random.seed(42)
    random.seed(42)

    # 真实的岗位模板（从 Glassdoor + LinkedIn 提炼）
    job_templates = [
        {
            "title": "数据分析师",
            "salary_range": (8, 20),
            "skills": ["SQL", "Python", "Excel", "Tableau", "PowerBI", "统计学", "数据可视化", "Pandas", "NumPy"],
            "edu_weights": {"本科": 0.7, "硕士": 0.2, "大专": 0.1},
            "exp_weights": {"应届": 0.3, "1-3年": 0.4, "3-5年": 0.2, "5-10年": 0.1},
        },
        {
            "title": "高级数据分析师",
            "salary_range": (15, 30),
            "skills": ["SQL", "Python", "Tableau", "统计学", "A/B测试", "机器学习", "数据建模", "特征工程"],
            "edu_weights": {"本科": 0.5, "硕士": 0.4, "博士": 0.1},
            "exp_weights": {"1-3年": 0.2, "3-5年": 0.4, "5-10年": 0.3, "10年以上": 0.1},
        },
        {
            "title": "大数据开发工程师",
            "salary_range": (12, 30),
            "skills": ["Hadoop", "Spark", "Flink", "Hive", "Kafka", "Java", "SQL", "Scala", "Docker"],
            "edu_weights": {"本科": 0.6, "硕士": 0.3, "大专": 0.1},
            "exp_weights": {"应届": 0.2, "1-3年": 0.3, "3-5年": 0.3, "5-10年": 0.2},
        },
        {
            "title": "数据挖掘工程师",
            "salary_range": (15, 35),
            "skills": ["Python", "机器学习", "数据挖掘", "SQL", "统计学", "特征工程", "模型调优", "Scikit-learn"],
            "edu_weights": {"本科": 0.4, "硕士": 0.4, "博士": 0.2},
            "exp_weights": {"1-3年": 0.3, "3-5年": 0.4, "5-10年": 0.3},
        },
        {
            "title": "数据科学家",
            "salary_range": (18, 45),
            "skills": ["Python", "机器学习", "深度学习", "统计学", "SQL", "实验设计", "A/B测试", "TensorFlow", "PyTorch"],
            "edu_weights": {"硕士": 0.5, "博士": 0.3, "本科": 0.2},
            "exp_weights": {"1-3年": 0.3, "3-5年": 0.4, "5-10年": 0.3},
        },
        {
            "title": "BI工程师",
            "salary_range": (10, 25),
            "skills": ["SQL", "Tableau", "PowerBI", "ETL", "数据建模", "Hive", "报表开发", "FineBI"],
            "edu_weights": {"本科": 0.7, "大专": 0.2, "硕士": 0.1},
            "exp_weights": {"应届": 0.2, "1-3年": 0.4, "3-5年": 0.3, "5-10年": 0.1},
        },
        {
            "title": "算法工程师",
            "salary_range": (20, 50),
            "skills": ["Python", "C++", "深度学习", "机器学习", "NLP", "CV", "模型部署", "TensorFlow", "PyTorch"],
            "edu_weights": {"硕士": 0.4, "博士": 0.4, "本科": 0.2},
            "exp_weights": {"1-3年": 0.3, "3-5年": 0.4, "5-10年": 0.3},
        },
        {
            "title": "数据仓库工程师",
            "salary_range": (12, 30),
            "skills": ["Hive", "SQL", "数仓建模", "ETL", "Spark", "Airflow", "Doris", "ClickHouse"],
            "edu_weights": {"本科": 0.6, "硕士": 0.3, "大专": 0.1},
            "exp_weights": {"应届": 0.2, "1-3年": 0.3, "3-5年": 0.3, "5-10年": 0.2},
        },
        {
            "title": "机器学习工程师",
            "salary_range": (20, 45),
            "skills": ["Python", "机器学习", "深度学习", "MLOps", "Docker", "Kubernetes", "模型部署", "TensorFlow", "PyTorch"],
            "edu_weights": {"硕士": 0.4, "本科": 0.3, "博士": 0.3},
            "exp_weights": {"1-3年": 0.3, "3-5年": 0.4, "5-10年": 0.3},
        },
        {
            "title": "后端开发工程师",
            "salary_range": (10, 30),
            "skills": ["Java", "Python", "Go", "Spring", "MySQL", "Redis", "微服务", "Docker", "Kubernetes"],
            "edu_weights": {"本科": 0.6, "硕士": 0.3, "大专": 0.1},
            "exp_weights": {"应届": 0.2, "1-3年": 0.4, "3-5年": 0.3, "5-10年": 0.1},
        },
        {
            "title": "数据产品经理",
            "salary_range": (12, 30),
            "skills": ["数据分析", "产品设计", "SQL", "用户研究", "A/B测试", "Axure", "项目管理"],
            "edu_weights": {"本科": 0.6, "硕士": 0.3, "大专": 0.1},
            "exp_weights": {"应届": 0.1, "1-3年": 0.3, "3-5年": 0.3, "5-10年": 0.3},
        },
        {
            "title": "ETL开发工程师",
            "salary_range": (10, 25),
            "skills": ["SQL", "ETL", "Hive", "Spark", "Airflow", "DataX", "Python", "Shell"],
            "edu_weights": {"本科": 0.6, "硕士": 0.2, "大专": 0.2},
            "exp_weights": {"应届": 0.3, "1-3年": 0.4, "3-5年": 0.2, "5-10年": 0.1},
        },
    ]

    # 中国公司（真实大厂 + 天津本地企业）
    companies = [
        # 一线大厂
        "字节跳动", "阿里巴巴", "腾讯", "百度", "美团", "京东", "滴滴",
        "快手", "小米", "华为", "网易", "拼多多", "哔哩哔哩", "小红书", "蔚来",
        "理想汽车", "知乎", "微博", "贝壳找房", "携程",
        # 数据/AI 公司
        "第四范式", "商汤科技", "旷视科技", "科大讯飞", "海康威视",
        "浪潮信息", "中科曙光", "明略科技", "神策数据", "GrowingIO",
        # 天津/武清企业
        "天津超算中心", "飞腾信息", "麒麟软件", "南大通用", "中科曙光天津",
        "科大讯飞天津", "字节跳动天津", "阿里巴巴天津",
        # 金融/银行
        "中国银行", "工商银行", "建设银行", "招商银行", "平安科技",
        "蚂蚁集团", "京东数科", "度小满金融",
        # 咨询/外企
        "埃森哲", "IBM", "微软中国", "英特尔中国", "德勤", "普华永道",
    ]

    # 行业分布
    industries = [
        "互联网/科技", "金融/银行", "人工智能", "大数据",
        "企业服务/SaaS", "电商/零售", "游戏/娱乐", "教育/培训",
        "医疗/健康", "制造/工业", "物流/供应链", "房地产",
    ]

    # 城市（加权，天津靠前）
    cities = []
    city_weights = []
    for city in CITY_DISTRICT_MAP:
        cities.append(city)
        if city == "天津":
            city_weights.append(25)  # 天津占 25%
        elif city in ("北京", "上海"):
            city_weights.append(15)
        elif city in ("深圳", "杭州", "广州"):
            city_weights.append(10)
        else:
            city_weights.append(5)

    # 城市→区级后缀映射
    city_district_map = {
        "北京": ["朝阳区", "海淀区", "丰台区", "西城区", "东城区", "大兴区"],
        "上海": ["浦东新区", "静安区", "徐汇区", "长宁区", "黄浦区"],
        "广州": ["天河区", "越秀区", "海珠区", "番禺区"],
        "深圳": ["南山区", "福田区", "宝安区", "龙华区"],
        "杭州": ["西湖区", "滨江区", "余杭区"],
        "天津": ["武清区", "滨海新区", "南开区", "河西区", "河东区", "西青区", "津南区"],
        "成都": ["高新区", "锦江区", "武侯区"],
        "武汉": ["光谷", "洪山区", "武昌区"],
        "南京": ["鼓楼区", "江宁区", "栖霞区"],
        "西安": ["高新区", "雁塔区", "长安区"],
    }

    rows = []
    for _ in range(n):
        template = random.choice(job_templates)
        title = template["title"]

        company = random.choice(companies)

        # 城市
        city = random.choices(cities, weights=city_weights, k=1)[0]
        districts = city_district_map.get(city, ["中心区"])
        district = random.choice(districts)
        location = f"{city}{district}"

        # 薪资（根据城市调整系数）
        city_salary_mult = {
            "北京": 1.3, "上海": 1.2, "深圳": 1.2, "广州": 1.0, "杭州": 1.1,
            "天津": 0.85, "成都": 0.8, "武汉": 0.75, "南京": 0.9, "西安": 0.7,
        }
        mult = city_salary_mult.get(city, 0.85)
        salary_low = template["salary_range"][0] * mult
        salary_high = template["salary_range"][1] * mult
        salary_avg = round(random.uniform(salary_low, salary_high), 1)

        # 学历（按权重）
        edu_keys = list(template["edu_weights"].keys())
        edu_vals = list(template["edu_weights"].values())
        education = random.choices(edu_keys, weights=edu_vals, k=1)[0]

        # 经验（按权重）
        exp_keys = list(template["exp_weights"].keys())
        exp_vals = list(template["exp_weights"].values())
        experience = random.choices(exp_keys, weights=exp_vals, k=1)[0]

        # 行业
        industry = random.choice(industries)

        # 技能
        num_skills = random.randint(3, min(7, len(template["skills"])))
        selected_skills = random.sample(template["skills"], num_skills)
        requirements = "; ".join(selected_skills)

        # 描述
        exp_desc = {
            "应届": "负责协助团队完成",
            "1-3年": "负责独立完成",
            "3-5年": "负责主导",
            "5-10年": "负责带领团队完成",
            "10年以上": "负责整体规划和",
        }
        desc_prefix = exp_desc.get(experience, "负责")
        description = f"{desc_prefix}{title}相关工作，涉及{'、'.join(selected_skills[:4])}等技术。具备{experience}相关经验，{education}及以上学历。"

        rows.append({
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "requirements": requirements,
            "salary_avg": salary_avg,
            "education": education,
            "experience": experience,
            "industry": industry,
            "city": city,
            "salary": f"{int(salary_low)}-{int(salary_high)}K",
        })

    df = pd.DataFrame(rows)
    print(f"✅ 增强模拟数据: {len(df)} 条（覆盖 {len(cities)} 个城市）")
    return df


def run_migration():
    """执行数据迁移：合并所有数据源"""
    print("=" * 50)
    print("🚀 开始数据迁移")
    print("=" * 50)

    all_data = []

    # 1. 加载真实数据
    glassdoor_df = load_glassdoor()
    if not glassdoor_df.empty:
        all_data.append(glassdoor_df)

    linkedin_df = load_linkedin_sample()
    if not linkedin_df.empty:
        all_data.append(linkedin_df)

    # 2. 生成增强模拟数据（中国城市）
    china_df = generate_enhanced_china_data(30000)
    all_data.append(china_df)

    if not all_data:
        print("❌ 没有任何数据源")
        return

    # 3. 合并
    merged = pd.concat(all_data, ignore_index=True, sort=False)
    print(f"\n📊 合并后共 {len(merged)} 条记录")

    # 4. 补充缺失的 salary_avg
    if "salary_avg" not in merged.columns:
        merged["salary_avg"] = merged.get("salary", 0).apply(
            lambda s: _parse_salary(str(s)) if isinstance(s, str) else (s if pd.notna(s) else 0)
        )
    merged["salary_avg"] = merged["salary_avg"].fillna(0)

    # 5. 确保所有标准列存在
    for col in ["title", "company", "location", "description", "requirements",
                 "salary", "salary_avg", "education", "experience", "industry", "city"]:
        if col not in merged.columns:
            merged[col] = ""

    # 6. 筛选有效数据
    merged = merged.dropna(subset=["title"])
    merged = merged[merged["title"].str.strip() != ""]
    print(f"📊 清洗后共 {len(merged)} 条有效记录")

    # 7. 打印统计
    print(f"\n📈 城市分布:")
    city_counts = merged["city"].value_counts().head(15)
    for city, count in city_counts.items():
        print(f"   {city}: {count}")

    print(f"\n📈 岗位分布:")
    title_counts = merged["title"].value_counts().head(15)
    for t, count in title_counts.items():
        print(f"   {t}: {count}")

    # 8. 写入数据库
    print(f"\n💾 写入数据库...")
    build_database(merged)
    print(f"\n✅ 数据迁移完成！")


if __name__ == "__main__":
    run_migration()
