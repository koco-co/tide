---
name: using-tide
description: "初始化 Tide 环境 — 智能项目分类、深度扫描/行业调研、方案推荐、脚手架生成。触发方式：首次运行、/using-tide、'初始化 tide'。"
argument-hint: "[--force]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, WebSearch, WebFetch, TaskCreate, TaskUpdate, TaskList
---

# Tide 初始化

为新项目或已有项目引导安装 Tide 测试框架。

---

## 任务初始化

创建 6 个任务（同现有格式）：
1. 环境检测 + 智能分类
2. 项目分析（根据分类更新主题）
3. 确认与选择（根据分类更新主题）
4. 源码仓库配置
5. 连接配置
6. 脚手架生成 + 配置验证

ID 记为 `<task_1_id>` 到 `<task_6_id>`。

---

## 第零步：环境检测 + 智能分类

Task 1 → in_progress

1. **工具检测**：`python3 --version`（>= 3.12）/ `uv --version` / `git --version`
2. **依赖检测**：jinja2 / pydantic / pyyaml（若有缺失自动安装）
3. **重初始化检测**：若 tide-config.yaml 已存在，询问使用/更新/重来
4. **智能分类**：检测测试文件数、conftest、pytest 配置、HTTP 客户端、allure、CI

判定规则：`TEST_FILE_COUNT >= 3 AND (CONFTEST 存在 OR PYTEST_CONFIG 存在) → existing_auto`

Task 1 完成。根据 project_type 更新 Task 2/3 主题。

---

## 分支 A：已有自动项目

### 深度扫描

Task 2 → in_progress

1. 读取 `agents/project-scanner.md` 作为 prompt，启动 project-scanner Agent（opus）
2. 读取 .tide/project-profile.json
3. **规范指纹生成**：运行 convention_scanner.py 生成惯例指纹
   uv run python3 ${CLAUDE_SKILL_DIR}/../../scripts/convention_scanner.py --project-root .
4. **读取指纹**：读取 .tide/convention-scout.json，等待 project-scanner 将其转换为 convention-fingerprint.yaml

Task 2 完成。Task 3 → in_progress

### 7 维度确认

逐项展示 project-profile.json 的 7 个维度（架构/代码风格/鉴权/工具链/Allure/数据管理/行业），每个维度用户确认或修正。修正结果写入 `_confirmed_profile`。

Task 3 完成。跳转至第三步。

---

## 分支 B：新项目

### 行业画像收集

Task 2 → in_progress

5 个问题逐一收集：行业领域 / 系统类型 / 团队规模 / 特殊需求 / 鉴权复杂度。结果存为 `_industry_profile`。

### AI 调研

1. 读取 `agents/industry-researcher.md` 作为 prompt，启动 industry-researcher Agent（sonnet）
2. 读取 .tide/research-report.json

Task 2 完成。Task 3 → in_progress

### 方案推荐与试运行

展示 2-3 个方案 → 用户选择 → 生成最小示例测试文件 → 确认风格 → 存为 `_selected_solution`

Task 3 完成。

---

## 第三步：源码仓库配置（共用）

Task 4 → in_progress

1. 询问仓库 URL（每行一个，可 @branch 后缀）
2. git clone 各仓库到 .repos/ 下
3. 配置 URL 前缀映射关系
4. 写入 repo-profiles.yaml

Task 4 完成。

---

## 第四步：连接配置（共用）

Task 5 → in_progress

1. Base URL → 认证方式（分支 A 可复用旧项目逻辑）→ 数据库（可选）→ Webhook（可选）
2. 写入 .env 或 .tide/config.yaml

Task 5 完成。

---

## 第五步：脚手架生成 + 配置验证

Task 6 → in_progress

1. 渲染 tide-config.yaml（Jinja2）
2. 运行 scaffold.py（--mode new/existing）
3. 生成 CLAUDE.md（包含 7 维度摘要或技术栈 + 行业上下文）
4. smoke test：URL 可达性 + 认证有效性 + 数据库连接（若配置）

打印初始化摘要，Task 6 完成。
