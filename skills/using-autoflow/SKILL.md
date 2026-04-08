---
name: using-autoflow
description: "初始化 AutoFlow 环境 — 项目脚手架、仓库配置、技术栈设置。适用场景：首次运行、/using-autoflow、'初始化 autoflow'、'设置 autoflow'。"
argument-hint: "[--force]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# AutoFlow 初始化技能

为新项目或已有项目引导安装 AutoFlow 自动化测试框架。
流程包括：环境校验、技术栈选择、仓库接入、连接配置，
最终生成项目脚手架和 CLAUDE.md。

---

## 第一步：环境检测与依赖预检

检查所有必要工具是否可用，并输出各工具的状态。

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

检测当前是否为已有项目（任意一项命中即判定为已有项目）：

```bash
# 检测已有项目标志
for f in pyproject.toml requirements.txt setup.py setup.cfg conftest.py pytest.ini; do
  test -f "$f" && echo "FOUND: $f"
done
# 检测已有测试目录
for d in testcases tests test; do
  test -d "$d" && echo "TEST_DIR: $d"
done
```

如果检测到任何一项，判断为已有项目。

检测插件依赖：

```bash
python3 -c "import jinja2" 2>/dev/null || echo "MISSING: jinja2"
python3 -c "import pydantic" 2>/dev/null || echo "MISSING: pydantic"
python3 -c "import yaml" 2>/dev/null || echo "MISSING: pyyaml"
```

若有缺失依赖，根据检测到的包管理器自动安装：
- uv: `uv pip install jinja2 pydantic pyyaml`
- pip: `pip install jinja2 pydantic pyyaml`
- 系统 Python (externally managed): `python3 -m pip install --user jinja2 pydantic pyyaml`

输出状态表格：

| 工具      | 要求版本 | 检测版本 | 状态 |
|-----------|----------|----------|------|
| Python    | >= 3.12  | x.y.z    | 正常/失败 |
| uv        | 任意     | x.y.z    | 正常/失败 |
| git       | 任意     | x.y.z    | 正常/失败 |
| jinja2    | 任意     | —        | 正常/已安装 |
| pydantic  | 任意     | —        | 正常/已安装 |
| pyyaml    | 任意     | —        | 正常/已安装 |
| 项目类型  | —        | 已有/新建 | 信息 |

若有必要工具缺失，打印安装说明并终止。

---

## 第二步：项目风格检测与确认

### 已有项目

全面扫描项目已有的风格配置和运行环境：

**风格配置检测：**
- 读取 `pyproject.toml` 中的 `[tool.ruff]`、`[tool.mypy]`、`[tool.pyright]`
- 若存在，读取 `.editorconfig`
- 若存在，读取 `ruff.toml`
- 读取测试目录下测试文件头部，推断编码规范

**运行环境检测：**
- 读取 `pyproject.toml` 中的 `requires-python`，推断 Python 版本要求
- 检测包管理器：`uv.lock` -> uv / `poetry.lock` -> poetry / `requirements.txt` -> pip
- 读取 `pyproject.toml` 中的 `[project.dependencies]`，记录已有依赖
- 检测测试框架配置：`[tool.pytest.ini_options]`、`pytest.ini`、`setup.cfg`
- 若存在 `Makefile`，提取已有 target 列表
- 若存在 `.pre-commit-config.yaml`，记录已有 hooks

**测试目录结构与代码风格深度扫描：**
- 识别测试入口目录（testcases/ vs tests/ vs test/）
- 识别子目录模式（scenariotest/ interface/ unittest/ 等）
- 读取 3-5 个现有测试文件头部，分析代码模式：
  - API 封装方式（Enum? 常量? 直接写URL?）
  - Request 工具类（BaseRequests? requests.Session? httpx?）
  - 断言风格（assert resp['code'] == 1? assert resp.status_code == 200?）
  - allure 使用方式
  - 认证方式（Cookie? Token? 自定义头?）

将检测结果汇总输出：

```
已有项目环境检测报告：
──────────────────────────────────────────
Python 版本要求：  >= 3.11
包管理器：         poetry（检测到 poetry.lock）
代码检查：         ruff（line-length=88）
类型检查：         mypy（strict 模式）
测试框架：         pytest（asyncio_mode=auto）
已有依赖：         httpx, pydantic, sqlalchemy ...
Pre-commit：       已配置（3 个 hooks）
Makefile：         已配置（test, lint, format）
──────────────────────────────────────────

已有测试项目结构检测：
──────────────────────────────────────────
测试入口目录：     testcases/
子目录结构：       scenariotest/, interface/ (未发现 unittest/)
API 封装模式：     Enum (api/xxx/xxx_api.py)
Request 封装：     BaseRequests (utils/common/BaseRequests.py)
断言风格：         resp['code'] == 1 + resp['success'] is True
认证方式：         Cookie (BaseCookies)
Allure 层级：      @allure.epic -> @allure.feature -> @allure.story
──────────────────────────────────────────
```

然后询问：

```
AskUserQuestion(
  "检测到已有项目配置，请选择处理方式：\n"
  "A) 保持旧项目风格和环境（推荐）\n"
  "   — 沿用现有 Python 版本、包管理器、linter、依赖，\n"
  "     仅追加 AutoFlow 必需的依赖（httpx、pydantic、pytest 等），\n"
  "     不改动已有配置文件格式和规则\n"
  "B) 覆盖为 AutoFlow 默认配置\n"
  "   — 使用推荐技术栈，替换现有工具链配置\n"
  "C) 手动自定义\n"
  "   — 逐项确认保留或替换每个配置项"
)
```

各选项行为：

- **A -- 保持旧项目风格和环境：**
  - 保留 `requires-python` 不变
  - 保留现有包管理器（继续使用 poetry/pip/uv）
  - 保留现有 linter/formatter 配置（ruff.toml、pyproject.toml 中的 tool 配置段）
  - 保留现有 `.editorconfig`、`.pre-commit-config.yaml`
  - 保留现有 Makefile target，仅追加缺失的 AutoFlow target
  - 仅追加 AutoFlow 必需但尚未安装的依赖（不升级已有依赖版本）
  - 生成 CLAUDE.md 时记录旧项目的实际技术栈，而非 AutoFlow 默认栈

- **B -- 覆盖为 AutoFlow 默认配置：**
  - 使用推荐技术栈完全替换
  - 备份已有配置到 `.autoflow/backup/` 目录

- **C -- 手动自定义：**
  - 逐项展示检测到的配置 vs AutoFlow 默认配置
  - 用户逐项选择保留或替换

### 新项目

请用户选择技术栈：

```
AskUserQuestion(
  "请为本项目选择技术栈：\n"
  "A) 推荐：Python 3.13 + uv + ruff + pyright + pre-commit + rich + make\n"
  "B) 保守：Python 3.12 + pip + flake8 + mypy + pytest-html\n"
  "C) 自定义：请输入您的偏好"
)
```

若用户选择 C，逐项询问：
- Python 版本
- 包管理器（uv / pip / poetry）
- 代码检查工具（ruff / flake8 / pylint）
- 类型检查工具（pyright / mypy）
- 可选扩展（pre-commit、rich、make）

将确认后的技术栈存储为 `_stack`，供后续步骤使用。

---

## 第二点五步：测试类型选择

根据项目类型，引导用户选择要生成的测试类型。

### 新项目

```
AskUserQuestion(
  multiSelect=true,
  "请选择要生成的测试类型：",
  options=[
    "All — 全部类型",
    "interface — 接口测试（单接口验证）",
    "scenariotest — 场景测试（CRUD 闭环、业务流程）",
    "unittest — 单元测试（需要源码仓库）"
  ]
)
```

注意：unittest 选项仅在用户提供了源码仓库时才显示。若用户选择了 unittest 但尚未配置源码仓库，提示将在第三步配置后生效。

### 已有项目

根据第二步深度扫描结果，动态调整选项：

```
AskUserQuestion(
  multiSelect=true,
  "检测到已有测试类型：interface, scenariotest\n"
  "请选择本次要生成的测试类型：",
  options=[
    "interface — 接口测试",
    "scenariotest — 场景测试",
    // 仅在检测到 unittest 目录或用户提供了源码时显示
    "unittest — 单元测试"
  ]
)
```

将用户选择的测试类型存储为 `_test_types`，供后续步骤使用。

---

## 第三步：源码仓库配置

询问一个或多个待克隆的源码仓库 URL：

```
AskUserQuestion(
  "请输入源码仓库 URL（每行一个，可附加 @branch 后缀）：\n"
  "示例：\n"
  "  https://git.example.com/group1/backend.git\n"
  "  https://git.example.com/group2/api.git@develop\n"
  "输入完毕后留空回车。"
)
```

根据 URL 自动推导本地路径：

```
https://git.example.com/group1/repo1.git  ->  .repos/group1/repo1/
https://git.example.com/group2/repo2.git@develop  ->  .repos/group2/repo2/（分支：develop）
```

克隆并切换每个仓库：

```bash
git clone <url> <local_path>
git -C <local_path> checkout <branch>   # 若指定了分支
```

然后询问 URL 前缀与仓库的映射关系，供 HAR 分析器定位请求所属仓库：

```
AskUserQuestion(
  "请配置 URL 前缀与仓库的映射（每行一条）：\n"
  "格式：<url-prefix> -> <repo-name>\n"
  "示例：\n"
  "  /api/v1 -> backend\n"
  "  /admin  -> admin-portal\n"
  "输入完毕后留空回车。"
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

## 第四步：连接配置

询问被测系统的 Base URL：

```
AskUserQuestion(
  "请输入目标系统的 Base URL（例如：http://172.16.115.247）："
)
```

询问认证方式。根据项目类型动态调整选项：

**已有项目**（检测到认证逻辑时）：

```
AskUserQuestion(
  "请选择认证方式：\n"
  "A) 复用旧项目认证逻辑（推荐，已检测到现有认证方式）\n"
  "B) Cookie（粘贴原始 Cookie 请求头值）\n"
  "C) Token（Bearer token）\n"
  "D) 用户名 + 密码\n"
  "E) 无需认证"
)
```

**新项目**：

```
AskUserQuestion(
  "请选择认证方式：\n"
  "A) Cookie（粘贴原始 Cookie 请求头值）\n"
  "B) Token（Bearer token）\n"
  "C) 用户名 + 密码\n"
  "D) 无需认证"
)
```

根据所选方式逐项收集凭证（每个字段单独一次 AskUserQuestion）。
若选择「复用旧项目认证逻辑」，则跳过凭证收集，记录 auth_method 为 `reuse`。

询问可选集成项：

```
AskUserQuestion(
  "是否配置数据库连接？（y/n）\n"
  "如选是，将依次询问主机、端口、用户名、密码及数据库名。"
)
```

若选是，逐项收集数据库字段。

```
AskUserQuestion(
  "是否配置通知 Webhook？（y/n）\n"
  "支持：钉钉、飞书、Slack"
)
```

若选是，询问 Webhook URL 和平台类型。

### 配置文件写入

**已有项目** -- .env 冲突处理：

检查 `.env` 是否已存在且有内容：
- 若 `.env` 已存在且非空：不修改 `.env`，将 AutoFlow 配置写入 `.autoflow/config.yaml`
- 告知用户：「已有 .env 不受影响，AutoFlow 配置已写入 .autoflow/config.yaml」

`.autoflow/config.yaml` 格式：
```yaml
# .autoflow/config.yaml — AutoFlow 连接配置（不影响已有 .env）
base_url: <value>
auth:
  method: cookie  # cookie | token | password | none | reuse
  cookie: <value>        # 或 token / user + pass
database:                # 若已配置
  host: <value>
  port: <value>
  user: <value>
  password: <value>
  name: <value>
notify:                  # 若已配置
  webhook: <value>
  platform: <value>      # dingtalk | feishu | slack
```

**新项目** -- 正常写入 `.env` 和 `.env.example`：

`.env` -- 包含真实值（已加入 .gitignore）：
```
BASE_URL=<value>
AUTH_COOKIE=<value>        # 或 AUTH_TOKEN / AUTH_USER + AUTH_PASS
DB_HOST=<value>            # 若已配置数据库
NOTIFY_WEBHOOK=<value>     # 若已配置通知
NOTIFY_PLATFORM=<value>    # dingtalk | feishu | slack
```

`.env.example` -- 仅含占位符（提交至版本控制）：
```
BASE_URL=http://your-server
AUTH_COOKIE=your_cookie_here
```

---

## 第五步：脚手架生成 + CLAUDE.md

### 新项目

运行脚手架脚本，生成项目目录结构：

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/scaffold.py \
  --stack "${_stack}" \
  --base-url "${BASE_URL}"
```

脚本将创建以下文件：
```
tests/
  conftest.py
  test_smoke.py
Makefile          （若技术栈包含 make）
pyproject.toml    （已更新）
.pre-commit-config.yaml  （若技术栈包含 pre-commit）
.gitignore        （确保 .env、.repos/、.autoflow/、.trash/ 已被忽略）
```

### 已有项目

不运行 scaffold.py 创建目录结构，仅执行以下操作：

- **追加 .gitignore 条目**：确保以下条目存在（不重复追加）：
  ```
  .repos/
  .autoflow/
  .trash/
  ```
- **创建 .autoflow/ 目录**（若不存在）
- **生成 CLAUDE.md**（见下方）

### CLAUDE.md 生成

在项目根目录自动生成 `CLAUDE.md`，包含以下章节：

```markdown
# CLAUDE.md — AutoFlow 项目

## 技术栈
<第二步确认的技术栈>

## 项目结构
<目录树>

## 测试类型
<第二点五步选择的测试类型列表>

## 源码仓库引用
<repo-profiles.yaml 中的仓库列表及本地路径>

## 规范索引
- 测试目录：<检测到的测试入口目录>
- Fixture：<conftest.py 路径>
- 断言规范：见 prompts/assertion-layers.md
- 代码风格：见 prompts/code-style-python.md

## 环境信息
- Base URL：${BASE_URL}
- 认证方式：<method>
- 数据库：<已配置 / 未配置>
- 通知：<已配置 / 未配置>
```

### autoflow-config.yaml 输出

在初始化结束时，将所有配置写入项目根目录的 `autoflow-config.yaml`：

```yaml
# autoflow-config.yaml — 由 /using-autoflow 自动生成
project:
  type: existing  # existing | new
  test_dir: testcases  # 测试入口目录
  test_types:  # 用户选择的测试类型
    - interface
    - scenariotest
  code_style:
    api_pattern: enum  # enum | constant | inline
    request_class: BaseRequests  # BaseRequests | httpx | requests
    assertion_style: "resp['code'] == 1"
    auth_method: cookie  # cookie | token | password | none | reuse
    allure_enabled: true
  package_manager: pip  # uv | pip | poetry
```

该文件作为后续 `/autoflow` 技能的输入，用于生成符合项目风格的测试代码。

### 初始化摘要

最后打印初始化摘要：

```
AutoFlow 初始化完成
──────────────────────────────────────────
项目类型：    已有项目 / 新项目
技术栈：      Python 3.13 + uv + ruff + pyright
测试类型：    interface, scenariotest
测试目录：    testcases/
已克隆仓库：  2 个
URL 映射：    3 条
认证方式：    Cookie
数据库：      已配置
Webhook：     飞书
配置文件：    autoflow-config.yaml
──────────────────────────────────────────
下一步：执行 /autoflow <path-to.har>
```
