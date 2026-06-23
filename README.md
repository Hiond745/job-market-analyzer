# 🎯 招聘市场智能分析工具

> 输入专业 + 地区，AI 自动推荐最适合你的岗位方向 + 市场数据看板 + 简历匹配度分析

## 功能亮点

- **智能推荐**：输入你的专业（如"数据科学与大数据技术"），系统自动匹配推荐适合的岗位方向
- **市场看板**：岗位数量、薪资分布、学历/经验要求、技能排行、词云
- **公司画像**：招聘公司 Top 10、行业分布
- **简历匹配**：输入你的技能，自动计算匹配度并给出学习建议

## 技术栈

Python · Pandas · SQLite · Plotly · WordCloud · Streamlit

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/你的用户名/job-market-analyzer.git
cd job-market-analyzer

# 安装依赖
pip install -r requirements.txt

# 生成数据（首次运行，已预置5000条模拟数据可跳过）
python -c "from src.etl import run_etl; run_etl(use_sample=True, sample_size=5000)"

# 启动应用
streamlit run app/main.py
```

## 项目结构

```
job-market-analyzer/
├── data/          # 数据文件（SQLite 数据库）
├── src/           # 核心逻辑（ETL、匹配、分析）
├── app/           # Streamlit 前端
│   ├── main.py          # 首页
│   ├── pages/           # 多页面
│   └── components/      # Tab 组件
├── assets/        # 静态资源
└── README.md
```

## 部署

一键部署到 Streamlit Cloud：
1. 将代码推送到 GitHub
2. 登录 [share.streamlit.io](https://share.streamlit.io)
3. 连接仓库，设置入口为 `app/main.py`
4. 部署完成 🚀

## 数据说明

本项目使用模拟招聘数据集（5000 条），覆盖主流城市和互联网/科技行业岗位。
数据仅供求职参考，不代表真实市场情况。

## 适用人群

- 数据科学/大数据/计算机相关专业在校生
- 正在找实习/工作的应届毕业生
- 想了解目标城市就业市场的求职者
