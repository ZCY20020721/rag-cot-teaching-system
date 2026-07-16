# 基于 RAG 与 CoT 的智能教学评估系统

> **Intelligent Teaching Assessment System based on RAG & CoT**  
> 毕业设计项目 · BMSTU ИУ5-21М · 周宸宇

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.57+-red.svg)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-green.svg)](https://www.langchain.com/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek--V3-purple.svg)](https://www.deepseek.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 项目简介

本项目构建了一套**基于检索增强生成（RAG）与思维链（CoT）的智能教学评估系统**，面向高等教育场景，为教师和学生提供完整的教学闭环支持：

- **教师端**：上传教材 → AI出题 → 发布习题 → 查看成绩统计 → 在线答疑
- **学生端**：浏览习题 → 提交答案 → 获取CoT分步批改 → 查看错题集 → 在线提问

核心创新点：通过 **RAG 技术将 LLM 输出锚定于教材内容**（防幻觉），通过 **CoT 三步推理链输出结构化可解释评分**（透明批改）。

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────┐
│               Streamlit 前端                   │
│  登录/注册 → 角色路由 → 8个功能页面            │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│              核心引擎层                         │
│  ┌─────────────┐  ┌──────────────────────┐   │
│  │ RAG Engine  │  │   CoT Grader         │   │
│  │ PDF→Chunk   │  │   出题 + 三步批改     │   │
│  │ →Embed→检索 │  │   + JSON容错重试     │   │
│  └──────┬──────┘  └──────────┬───────────┘   │
│         │                    │               │
│  ┌──────▼────────────────────▼───────────┐   │
│  │        LangChain + LCEL               │   │
│  └───────────────────────────────────────┘   │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│              数据持久层                         │
│  ┌──────────────────┐  ┌──────────────────┐  │
│  │   ChromaDB       │  │     SQLite       │  │
│  │   (向量存储)      │  │  (用户/习题/记录) │  │
│  └──────────────────┘  └──────────────────┘  │
│  ┌──────────────────────────────────────┐    │
│  │       DeepSeek-V3 API (云端)          │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- Windows / macOS / Linux

### 2. 克隆仓库

```bash
git clone https://github.com/ZCY20020721/rag-cot-teaching-system.git
cd rag-cot-teaching-system
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 API Key

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 填入你的 DeepSeek API Key
# DEEPSEEK_API_KEY=sk-xxxxxxxx
```

> 💡 注册 DeepSeek API：https://platform.deepseek.com/

### 5. 启动系统

```bash
streamlit run main.py
```

浏览器访问 **http://localhost:8501**

### 6. 快速体验

| 步骤 | 角色 | 操作 |
|------|------|------|
| 1 | 教师 | 注册教师账号 → 登录 |
| 2 | 教师 | 进入「教材管理」→ 上传 PDF 教材 |
| 3 | 教师 | 进入「习题生成」→ 点击「生成考题」→ 发布 |
| 4 | 学生 | 新开浏览器，注册学生账号 → 登录 |
| 5 | 学生 | 进入「习题作答」→ 选择题目 → 输入答案 → 提交批改 |
| 6 | 学生 | 查看 CoT 分步批改结果（要点分+逻辑分+苏格拉底反馈） |
| 7 | 学生 | 进入「错题集」查看个人薄弱知识点 |
| 8 | 教师 | 进入「学生成绩」查看班级错题统计 |

---

## 📁 项目结构

```
НИРС/
├── main.py                    # 应用入口（路由分发 + Session管理）
├── dependencies.py            # RAG/CoT 全局单例工厂
├── db.py                      # 数据库层（6张表 + 20+函数）
├── rag_engine.py              # RAG 检索引擎（PDF→切分→向量化→检索）
├── cot_grader.py              # CoT 批改引擎（出题 + 三步推理批改）
├── prompts.py                 # LLM 提示词模板（出题/批改/薄弱分析）
├── pages/                     # 页面模块（8个独立页面）
│   ├── login.py               #   登录/注册页
│   ├── sidebar.py             #   角色自适应侧边栏
│   ├── teacher_materials.py   #   教师-教材管理
│   ├── teacher_exercises.py   #   教师-习题生成
│   ├── teacher_scores.py      #   教师-学生成绩
│   ├── student_answer.py      #   学生-习题作答
│   ├── student_scores.py      #   学生-我的成绩
│   ├── student_errors.py      #   学生-错题集
│   └── chat.py                #   师生聊天（微信风格）
├── tests/                     # 单元测试
├── data/                      # PDF 教材存放目录
├── chroma_db/                 # ChromaDB 向量持久化（运行时生成）
├── uploads/chat/              # 聊天文件存储（运行时生成）
├── .env.example               # API Key 配置模板
├── .gitignore
└── requirements.txt           # Python 依赖清单
```

---

## 🔧 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | Streamlit 1.57+ | 纯 Python Web 框架，零前端代码 |
| **大模型** | DeepSeek-V3 (API) | 兼容 OpenAI SDK，高性价比 |
| **编排** | LangChain + LCEL | 链式调用，文档→检索→Prompt→解析 |
| **向量库** | ChromaDB | 本地免安装，HNSW 近似最近邻索引 |
| **嵌入模型** | all-MiniLM-L6-v2 | 384维，本地 CPU 运行，完全免费 |
| **数据库** | SQLite | Python 标准库内置，零配置 |
| **密码安全** | SHA-256（计划升级为 bcrypt） | 哈希存储，参数化防SQL注入 |
| **可视化** | Plotly | 交互式柱状图，红色渐变配色 |

---

## 🧪 运行测试

```bash
# 运行全部测试
pytest tests/ -v

# 带覆盖率报告
pytest tests/ -v --cov=. --cov-report=term-missing

# 分模块运行
pytest tests/test_db.py -v
pytest tests/test_rag_engine.py -v
pytest tests/test_cot_grader.py -v
```

---

## 📊 核心功能演示

### 教师端

| 教材管理 | 习题生成 | 学生成绩 |
|----------|----------|----------|
| 上传PDF → 自动向量化 | RAG检索 → AI出题 → 一键发布 | 全局答题记录 + 错误统计图 |

### 学生端

| 习题作答 | 我的成绩 | 错题集 |
|----------|----------|--------|
| 在线答题 → CoT批改 → 逐点评分 | 历次得分记录 | 薄弱知识点柱状图 + 错题回顾 |

### CoT 三步批改流程

```
步骤1: 要点逐条匹配 → 每个得分点 0-5 分 + 评语
步骤2: 整体逻辑评估 → 逻辑连贯性 0-5 分
步骤3: 综合反馈     → 苏格拉底式引导 + 薄弱标签
```

### 师生聊天

- 微信风格消息气泡（发送者绿色靠右，接收者白色靠左）
- 表情选择器（4类 100+ emoji）
- 文件传输（图片/视频/文档/压缩包）
- 2秒自动刷新（准实时）

---

## 📝 论文相关

本项目配套论文《基于 RAG 与 CoT 的智能教学评估系统》（中俄双语），涵盖：

1. 项目背景与目标
2. 系统架构与模块设计
3. RAG 检索流水线与防幻觉策略
4. CoT 思维链批改机制
5. 多角色权限管理
6. 实时聊天系统
7. 系统评估方案（RAGAS + 人评 + 多模型对比）

---

## 🗺️ 开发路线图

- [x] RAG 检索引擎（PDF → 向量化 → 语义检索）
- [x] CoT 批改引擎（出题 + 三步推理 + JSON容错）
- [x] 多角色登录鉴权（教师/学生角色隔离）
- [x] 教材管理 + 习题发布
- [x] 习题作答 + 批改结果可视化
- [x] 成绩统计 + 薄弱知识点柱状图
- [x] 错题集（个人知识薄弱分析）
- [x] 师生实时聊天（文字+表情+文件）
- [x] 代码模块化拆分
- [ ] bcrypt 密码安全升级
- [ ] 混合检索（Dense + BM25）
- [ ] RAGAS 自动化评测
- [ ] 多模型对比实验（DeepSeek / GLM-4 / GPT-4o）
- [ ] WebSocket 实时聊天升级
- [ ] 中/俄/英三语切换
- [ ] BKT 知识追踪模型

---

## 📄 License

MIT © 2026 周宸宇 (Zhou Chengyu)
