---
name: using-autoflow
description: "初始化 AutoFlow 环境 — 智能项目分类、深度扫描/行业调研、方案推荐、脚手架生成。适用场景：首次运行、/using-autoflow、'初始化 autoflow'、'设置 autoflow'。"
argument-hint: "[--force]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, WebSearch, WebFetch, TaskCreate, TaskUpdate, TaskList
---

# AutoFlow 初始化技能

为新项目或已有项目引导安装 AutoFlow 自动化测试框架。
流程包括：环境校验、智能分类、深度扫描/行业调研、仓库接入、连接配置，
最终生成项目脚手架和 CLAUDE.md。

---

## 第零步：环境检测 + 智能分类

### 环境检测

检查所有必要工具是否可用：

```bash
python3 --version   # 要求 >= 3.12
uv --version        # 要求 uv 包管理器
git --version       # 要求 git
```

检测包管理器类型：

```bash
test -f uv.lock && echo "PKG_MGR: uv"
test -f poetry.lock && echo "PKG_MGR: poetry"
test -f requirements.txt && echo "PKG_MGR: pip"
```

检测插件依赖：

```bash
python3 -c "import jinja2" 2>/dev/null || echo "MISSING: jinja2"
python3 -c "import pydantic" 2>/dev/null || echo "MISSING: pydantic"
python3 -c "import yaml" 2>/dev/null || echo "MISSING: pyyaml"
```

若有缺失依赖，根据检测到的包管理器自动安装。

输出状态表格：

| 工具      | 要求版本 | 检测版本 | 状态 |
|-----------|----------|----------|------|
| Python    | >= 3.12  | x.y.z    | 正常/失败 |
| uv        | 任意     | x.y.z    | 正常/失败 |
| git       | 任意     | x.y.z    | 正常/失败 |
| jinja2    | 任意     | —        | 正常/已安装 |
| pydantic  | 任意     | —        | 正常/已安装 |
| pyyaml    | 任意     | —        | 正常/已安装 |

若有必要工具缺失，打印安装说明并终止。

### 快速重初始化检测

```bash
test -f autoflow-config.yaml && echo "CONFIG_EXISTS"
```

若 `autoflow-config.yaml` 已存在：

```
AskUserQuestion(
  "检测到已有 AutoFlow 配置。请选择处理方式：",
  options=[
    "使用现有配置直接进入 /autoflow（推荐）",
    "更新配置（只修改变更项）",
    "完全重新初始化"
  ]
)
```

- 选择「使用现有配置」→ 打印"配置无变更，请运行 /autoflow <har-path>"并终止
- 选择「更新配置」→ 读取现有配置，后续步骤中只询问用户想修改的部分
- 选择「完全重新初始化」→ 备份现有配置到 `.autoflow/backup/`，继续完整流程

### 智能分类

扫描项目标志，判定项目类型：

```bash
# 计算测试文件数
TEST_COUNT=0
for d in testcases tests test; do
  if [ -d "$d" ]; then
    count=$(find "$d" -name "test_*.py" -o -name "*_test.py" 2>/dev/null | wc -l)
    TEST_COUNT=$((TEST_COUNT + count))
  fi
done
echo "TEST_FILE_COUNT: $TEST_COUNT"

# 检测 conftest.py
for f in conftest.py tests/conftest.py testcases/conftest.py test/conftest.py; do
  test -s "$f" && echo "CONFTEST: $f"
done

# 检测 pytest 配置
grep -q "\[tool\.pytest" pyproject.toml 2>/dev/null && echo "PYTEST_CONFIG: pyproject.toml"
test -f pytest.ini && echo "PYTEST_CONFIG: pytest.ini"
grep -q "\[tool:pytest\]" setup.cfg 2>/dev/null && echo "PYTEST_CONFIG: setup.cfg"

# 检测 HTTP 客户端
grep -rl "import requests\|import httpx\|BaseRequests" testcases/ tests/ test/ 2>/dev/null | head -3

# 检测 allure
grep -rl "import allure" testcases/ tests/ test/ 2>/dev/null | head -3

# 检测 CI 配置
test -d .github/workflows && echo "CI: github_actions"
test -f .gitlab-ci.yml && echo "CI: gitlab_ci"
test -f Jenkinsfile && echo "CI: jenkins"
```

**判定规则：**

```
if TEST_FILE_COUNT >= 3 AND (CONFTEST存在 OR PYTEST_CONFIG存在):
    project_type = "existing_auto"
else:
    project_type = "new"
```

输出分类结果：

```
项目类型判定：<existing_auto | new>
  测试文件数：<N>
  conftest：  <路径 | 未检测到>
  pytest 配置：<路径 | 未检测到>
```

**边界情况处理：**

- 若 `project_type = "new"` 但 `TEST_FILE_COUNT > 0`（1-2 个文件）：提示"注意：检测到少量测试文件，如需保留请告知。"
- 若检测到非 Python 测试代码（.java/.js/.ts 测试文件）：提示"注意：检测到非 Python 测试代码，AutoFlow 目前仅支持 Python。"

根据 `project_type` 进入对应分支。

---

## 分支 A：已有自动化项目（project_type = "existing_auto"）

### 第一步：深度扫描 Agent

启动 project-scanner Agent 深度分析项目：

```
Agent(
  name="project-scanner",
  description="深度扫描已有自动化项目，输出 7 维度分析",
  model="opus",
  prompt="
    读取 agents/project-scanner.md 中的完整指令。
    project_root: <当前目录>
    incremental: <true | false>
    last_commit: <.autoflow/project-profile.json 中的 scan_commit，若存在>
    执行全部 7 个维度的扫描，写入 .autoflow/project-profile.json。
  "
)
```

等待 Agent 完成，读取 `.autoflow/project-profile.json`。

### 第一步续：交互式逐项确认

读取 project-profile.json，按 7 个维度逐项向用户展示并确认。

**维度 1：项目架构**

```
AskUserQuestion(
  "【1/7 项目架构】检测结果：\n"
  "  测试入口目录：  <test_entry_dir>\n"
  "  子目录结构：    <subdirs 列表>\n"
  "  conftest 层级：  <conftest_levels>\n"
  "  工具类目录：    <utility_dirs>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

若用户选择"需要修正"，在 Other 中获取修正内容，更新 profile。

**维度 2：代码风格**

```
AskUserQuestion(
  "【2/7 代码风格】检测结果：\n"
  "  API 封装：      <api_pattern> (<api_pattern_path>)\n"
  "  Request 封装：  <request_class> (<request_class_path>)\n"
  "  断言风格：      <assertion_style>\n"
  "  命名规范：      <naming_convention>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

**维度 3：鉴权方式**

```
AskUserQuestion(
  "【3/7 鉴权方式】检测结果：\n"
  "  认证方式：      <auth_method>\n"
  "  认证类：        <auth_class> (<auth_class_path>)\n"
  "  多环境 Token：  <multi_env_token>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

**维度 4：依赖与工具链**

```
AskUserQuestion(
  "【4/7 依赖与工具链】检测结果：\n"
  "  Python 版本：   <python_version>\n"
  "  包管理器：      <package_manager>\n"
  "  HTTP 客户端：   <http_client> <http_client_version>\n"
  "  测试框架：      <test_framework>\n"
  "  Linter：        <linter>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

**维度 5：Allure 使用模式**

```
AskUserQuestion(
  "【5/7 Allure 标注】检测结果：\n"
  "  装饰器层级：    <decorator_hierarchy>\n"
  "  步骤模式使用率：<step_usage_ratio>\n"
  "  严重等级标注率：<severity_usage_ratio>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

**维度 6：数据管理模式**

```
AskUserQuestion(
  "【6/7 数据管理】检测结果：\n"
  "  测试数据来源：  <data_sources>\n"
  "  数据驱动：      <parametrize_count> 处 parametrize\n"
  "  数据库操作：    <db_helper_class> (<db_helper_path>)\n"
  "  清理策略：      <cleanup_strategy>\n"
  "\n检测是否正确？",
  options=["正确", "需要修正"]
)
```

**维度 7：行业与业务上下文**

```
AskUserQuestion(
  "【7/7 行业上下文】以下是 AI 从代码推断的信息：\n"
  "  推断行业：      <inferred_industry>\n"
  "  核心业务领域：  <business_domains>\n"
  "  合规要求：      <compliance_detected>\n"
  "\n是否正确？如有补充请在 Other 中说明。",
  options=["正确", "需要补充"]
)
```

将所有确认/修正后的结果作为 `_confirmed_profile` 存储，供后续步骤使用。

分支 A 完成后，跳转到第三步。

---

## 分支 B：新项目 / 非自动化项目（project_type = "new"）

### 第一步：行业画像收集

通过 5 个问题逐一收集用户行业画像：

**Q1 — 行业领域**

```
AskUserQuestion(
  "你所在的行业/领域是什么？",
  options=[
    "互联网/SaaS",
    "金融/银行/保险",
    "医疗/健康",
    "电商/零售"
  ]
)
```

**Q2 — 被测系统类型**

```
AskUserQuestion(
  "你要测试的系统属于什么类型？",
  options=[
    "Web 后端 API (REST/GraphQL)",
    "微服务架构（多服务间通信）",
    "移动端 BFF (Backend for Frontend)",
    "开放平台/第三方 API 集成"
  ]
)
```

**Q3 — 团队规模与自动化经验**

```
AskUserQuestion(
  "测试团队规模和自动化经验如何？",
  options=[
    "1-2 人，刚开始做自动化",
    "3-5 人，有一定自动化基础",
    "5+ 人，成熟的自动化体系"
  ]
)
```

**Q4 — 特殊需求**（多选）

```
AskUserQuestion(
  multiSelect=true,
  "项目有以下哪些特殊需求？",
  options=[
    "多环境切换 (dev/staging/prod)",
    "多版本 API 共存 (v1/v2/v3)",
    "国际化/多语言",
    "性能测试/压力测试"
  ]
)
```

**Q5 — 鉴权复杂度**

```
AskUserQuestion(
  "系统的鉴权方式有多复杂？",
  options=[
    "简单 — 单一 Cookie/Token",
    "中等 — 多角色权限 + RBAC",
    "复杂 — OAuth2/SSO/多租户",
    "不确定 — 需要调研"
  ]
)
```

将 5 个答案组装为 `_industry_profile`。

### 第二步：调研 Agent

派出 industry-researcher Agent：

```
Agent(
  name="industry-researcher",
  description="调研行业自动化测试最佳实践",
  model="sonnet",
  prompt="
    读取 agents/industry-researcher.md 中的完整指令。
    用户行业画像：
      industry: <Q1 答案>
      system_type: <Q2 答案>
      team_size: <Q3 答案>
      special_needs: <Q4 答案列表>
      auth_complexity: <Q5 答案>
    执行完整调研流程，写入 .autoflow/research-report.json。
  "
)
```

等待 Agent 完成，读取 `.autoflow/research-report.json`。

### 第二步续：方案呈现与选择

读取 research-report.json，向用户展示方案：

```
AskUserQuestion(
  "基于你的行业画像，以下是 AI 调研推荐的方案：\n\n"
  "━━━ 方案 1：<name>（推荐，适合度 <fit_score>/100）━━━\n"
  "  测试框架：<framework>\n"
  "  HTTP 客户端：<http_client>\n"
  "  报告：<report>\n"
  "  Mock：<mock>\n"
  "  CI/CD：<ci>\n"
  "  数据管理：<data_management>\n"
  "  行业特性：<industry_specific 列表>\n"
  "  优势：<pros>\n"
  "  劣势：<cons>\n\n"
  "━━━ 方案 2：<name>（适合度 <fit_score>/100）━━━\n"
  "  ...\n\n"
  "请选择一个方案：",
  options=["方案 1（推荐）", "方案 2", "方案 3"]
)
```

将选择的方案存为 `_selected_solution`。

### 第二步续：方案试运行

基于选定方案，生成一个最小示例测试文件：

1. 根据 `industry_specific` 选取最具代表性的接口类型
2. 生成包含 1 个 GET + 1 个 POST 测试的文件
3. 展示给用户确认

```
AskUserQuestion(
  "以下是基于所选方案生成的示例测试文件。\n"
  "请确认代码风格是否符合预期：\n\n"
  "<示例代码内容>\n\n",
  options=[
    "风格正确，继续全量生成（推荐）",
    "需要调整"
  ]
)
```

若需调整，在 Other 中获取反馈后修改方案参数。

分支 B 完成后，继续第三步。

---

## 第三步：源码仓库配置（两个分支共用）

询问一个或多个待克隆的源码仓库 URL：

```
AskUserQuestion(
  "请输入源码仓库 URL（每行一个，可附加 @branch 后缀）：\n"
  "示例：\n"
  "  https://git.example.com/group1/backend.git\n"
  "  https://git.example.com/group2/api.git@develop\n"
  "输入完毕后留空回车。如不需要源码分析，请直接跳过。"
)
```

根据 URL 自动推导本地路径：

```
https://git.example.com/group1/repo1.git  →  .repos/group1/repo1/
```

克隆并切换每个仓库：

```bash
git clone <url> <local_path>
git -C <local_path> checkout <branch>   # 若指定了分支
```

询问 URL 前缀与仓库的映射关系：

```
AskUserQuestion(
  "请配置 URL 前缀与仓库的映射（每行一条）：\n"
  "格式：<url-prefix> → <repo-name>\n"
  "示例：\n"
  "  /api/v1 → backend\n"
  "  /admin  → admin-portal\n"
  "输入完毕后留空回车。"
)
```

若分支 B 的方案包含 Mock 服务：

```
AskUserQuestion(
  "所选方案包含 Mock 服务（<mock 名称>）。是否需要配置 Mock 服务仓库？",
  options=["是，输入 Mock 仓库 URL", "否，暂不配置"]
)
```

在项目根目录生成 `repo-profiles.yaml`：

```yaml
# repo-profiles.yaml — 由 /using-autoflow 自动生成
repos:
  - name: <repo-name>
    local_path: .repos/<group>/<repo>/
    remote: <url>
    branch: <branch>
    url_prefixes:
      - <prefix1>
      - <prefix2>
```

---

## 第四步：连接配置（两个分支共用，深度按鉴权复杂度分级）

询问被测系统的 Base URL：

```
AskUserQuestion(
  "请输入目标系统的 Base URL（例如：http://172.16.115.247）："
)
```

询问认证方式。根据分支和鉴权复杂度动态调整选项：

**分支 A（检测到认证逻辑时）：**

```
AskUserQuestion(
  "请选择认证方式：",
  options=[
    "复用旧项目认证逻辑（推荐，检测到：<auth_class>）",
    "Cookie（粘贴原始 Cookie 请求头值）",
    "Token（Bearer token）",
    "用户名 + 密码",
    "无需认证"
  ]
)
```

**分支 B（简单鉴权）：**

```
AskUserQuestion(
  "请选择认证方式：",
  options=[
    "Cookie（粘贴原始 Cookie 请求头值）",
    "Token（Bearer token）",
    "用户名 + 密码",
    "无需认证"
  ]
)
```

**分支 B（中等鉴权 — RBAC）：** 上述选项 + 额外追问：

```
AskUserQuestion(
  "请输入需要测试的角色列表（每行一个）：\n"
  "示例：admin, editor, viewer"
)
```

**分支 B（复杂鉴权 — OAuth2/SSO）：** 上述选项 + 额外追问：

```
AskUserQuestion("请输入 OAuth2 Client ID：")
AskUserQuestion("请输入 OAuth2 Client Secret：")
AskUserQuestion("请输入 SSO/Token 端点 URL：")
```

根据所选方式逐项收集凭证。若选择「复用旧项目认证逻辑」，记录 `auth_method: reuse`。

询问可选集成项：

```
AskUserQuestion("是否配置数据库连接？（y/n）")
```

若选是，逐项收集数据库字段。

```
AskUserQuestion("是否配置通知 Webhook？（y/n）\n支持：钉钉、飞书、Slack")
```

若选是，询问 Webhook URL 和平台类型。

### 配置文件写入

**分支 A（已有 .env）：** 不修改 .env，AutoFlow 配置写入 `.autoflow/config.yaml`。

**分支 B（新项目）：** 正常写入 `.env` 和 `.env.example`。

---

## 第五步：脚手架生成 + CLAUDE.md + 配置验证

### 生成 autoflow-config.yaml

使用 Jinja2 模板 `templates/autoflow-config.yaml.j2` 渲染 `autoflow-config.yaml`：
- 分支 A：包含 `project.code_style` 段（从确认后的 profile 提取）
- 分支 B：包含 `industry` 段和 `solution` 段

### 脚手架生成

**分支 A：**

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/scaffold.py \
  --mode existing \
  --project-root "."
```

仅追加 `.autoflow/`、`.repos/`、`.trash/` 目录和 `.gitignore` 条目。

**分支 B：**

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/scaffold.py \
  --mode new \
  --stack "${_selected_solution.stack}" \
  --base-url "${BASE_URL}" \
  --project-root "."
```

生成完整目录结构：tests/、core/、conftest.py、pyproject.toml、Makefile 等。

### 生成 CLAUDE.md

在项目根目录生成 `CLAUDE.md`：

**分支 A 的 CLAUDE.md 包含：**
```markdown
# CLAUDE.md — AutoFlow 项目（已有项目适配）

## 项目理解
<7 维度扫描确认后的摘要>

## 代码风格约束
- API 封装：<api_pattern>
- Request 封装：<request_class>
- 断言风格：<assertion_style>
- 认证方式：<auth_method>
以上风格优先于 AutoFlow 默认规范。

## 行业上下文
<维度 7 确认结果>
```

**分支 B 的 CLAUDE.md 包含：**
```markdown
# CLAUDE.md — AutoFlow 项目

## 技术栈
<选定方案的完整技术栈>

## 行业上下文
<行业画像 + 合规要求>

## 项目结构
<目录树>

## 环境信息
- Base URL：${BASE_URL}
- 认证方式：<method>
- 数据库：<已配置 / 未配置>
```

### 配置验证

在脚手架生成后，自动执行 smoke test：

```bash
# 1. Base URL 可达性
python3 -c "
import httpx
try:
    r = httpx.get('${BASE_URL}', timeout=10)
    print(f'BASE_URL: OK (HTTP {r.status_code})')
except Exception as e:
    print(f'BASE_URL: FAIL ({e})')
"
```

```bash
# 2. 认证有效性（若非 reuse 模式）
python3 -c "
import httpx
headers = {<根据认证方式构建>}
try:
    r = httpx.get('${BASE_URL}', headers=headers, timeout=10)
    print(f'AUTH: {\"OK\" if r.status_code < 400 else \"FAIL\"} (HTTP {r.status_code})')
except Exception as e:
    print(f'AUTH: FAIL ({e})')
"
```

```bash
# 3. 数据库连接（若配置了数据库）
python3 -c "
import pymysql
try:
    conn = pymysql.connect(host='${DB_HOST}', port=${DB_PORT}, user='${DB_USER}', password='${DB_PASS}', database='${DB_NAME}')
    print('DB: OK')
    conn.close()
except Exception as e:
    print(f'DB: FAIL ({e})')
"
```

展示验证结果：

```
配置验证结果：
  Base URL 可达性：  <通过/失败 + 详情>
  认证有效性：        <通过/失败 + 详情>
  数据库连接：        <通过/失败/未配置>
```

若有失败项：

```
AskUserQuestion(
  "<失败项> 验证失败：<错误详情>\n是否立即修正？",
  options=["是，重新输入", "跳过，稍后修正"]
)
```

若选择修正，回到第四步对应的配置项重新收集。

### 打印初始化摘要

```
AutoFlow 初始化完成
──────────────────────────────────────────
项目类型：      <existing_auto / new>
技术栈：        <方案名称 / 旧项目原有栈>
行业：          <domain>
已克隆仓库：    <N> 个
URL 映射：      <N> 条
认证方式：      <method>
数据库：        <已配置 / 未配置>
配置验证：      <全部通过 / N 项失败>
──────────────────────────────────────────
下一步：执行 /autoflow <path-to.har>
```
