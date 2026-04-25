---
name: using-tide
description: "初始化 Tide 环境 — 智能项目分类、深度扫描/行业调研、方案推荐、脚手架生成。触发方式：首次运行、/using-tide、'初始化 tide'。"
argument-hint: "[--force]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, WebSearch, WebFetch, TaskCreate, TaskUpdate, TaskList
---

# Tide 初始化

> **重要：除非必要，否则不要改动已有项目中的测试配置或脚本。如需修改，先用 AskUserQuestion 向用户报告改动原因和改动范围，确认后方可执行。**

为新项目或已有项目引导安装 Tide 测试框架。

---

## 第零步：自更新

在开始之前检查 Tide 插件是否有更新。

```bash
# 检查并自动更新插件（无网络时静默跳过）
bash "${CLAUDE_SKILL_DIR}/../../scripts/self-update.sh"
```

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

1. **Tide 运行环境检查**：`python3 --version`（>= 3.12，Tide 自身需要）/ `uv --version` / `git --version`
2. **项目 Python 版本检测**：依次检查 `.python-version` / `pyproject.toml` → `requires-python` / `setup.py`或`setup.cfg` → `python_requires` / `Pipfile` → `python_version`，输出项目要求的 Python 版本（此版本仅作为上下文记录，不影响 Tide 运行）
3. **依赖检测**：jinja2 / pydantic / pyyaml（若有缺失自动安装）
4. **重初始化检测**：若 tide-config.yaml 已存在，询问使用/更新/重来
5. **智能分类**：检测测试文件数、conftest、pytest 配置、HTTP 客户端、allure、CI

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
5. **复杂度评估**：
   - 读取 .tide/convention-scout.json 输出，评估：
     - 模块数 > 3 → complexity = complex
     - 有 config/env/*.ini → complexity = complex
     - 有 run_demo.py → complexity = moderate
     - 否则 → complexity = simple
   - 将 complexity 存入上下文（供后续步骤使用）

Task 2 完成。Task 3 → in_progress

### 7 维度确认

逐项展示 project-profile.json 的 7 个维度（架构/代码风格/鉴权/工具链/Allure/数据管理/行业），每个维度用户确认或修正。修正结果写入 `_confirmed_profile`。

### 新维度确认

8. **多环境检测确认**（仅 complexity=moderate/complex）：
   - 展示检测到的环境列表
   - 询问：是否配置多环境？当前默认环境是哪个？
   - 若确认，写入 environments 节到 tide-config.yaml

9. **测试运行器检测**（仅 complexity=complex）：
   - 若检测到 run_demo.py 等自定义 runner：
     - 展示检测到的运行参数（并行数、重试次数）
     - 展示模块级运行入口
     - 确认写入 tide-config.yaml

10. **认证流程确认**（如有认证类）：
    - 展示检测到的认证方式 + 认证类 + 步骤链
    - 确认凭证来源

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

> 注意：当前项目已在工作目录中，无需再配置。此步骤仅管理**额外源码仓库**（被测服务等），存储在 `.tide/repos/` 下。

1. **检查已有仓库**：`ls -d .tide/repos/*/*/ 2>/dev/null`，仅检测 `.tide/repos/` 下的仓库，**不要读取当前项目的 git 信息**。
   - 若已有仓库：读取每个仓库的 `git remote get-url origin` 和当前分支
   - 展示给用户确认（使用 AskUserQuestion）
   - 用户确认或修正后写入 repo-profiles.yaml
2. **首次配置**（无 .tide/repos 时）：
   - 让用户提供需要关联的源码仓库 Git 地址
   - 使用 `uv run python3 scripts/repo_sync.py clone <url> -b <branch>` 进行克隆，自动按组名路径保存到 `.tide/repos/<group>/<repo>`
3. 配置 URL 前缀映射关系
4. 写入 repo-profiles.yaml

切换迭代分支时，可使用 `uv run python3 scripts/repo_sync.py checkout <branch>` 批量切换所有仓库。
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
3. smoke test：
   - URL 可达性 + 认证有效性 + 数据库连接（若配置）
   - 若 tide-config.yaml 中存在 test_runner.type == custom：
     - 展示：`python {{ test_runner.entry }}` 运行全部测试
     - 展示：`python {{ test_runner.entry }} --module <name>` 运行特定模块
   - 若没有自定义 runner：
     - 现有 pytest 命令逻辑

打印初始化摘要，Task 6 完成。
