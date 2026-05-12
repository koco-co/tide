<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/Tide-1.3-7C3AED?style=for-the-badge&logoColor=white">
  <img alt="Tide" src="https://img.shields.io/badge/Tide-1.3-7C3AED?style=for-the-badge&logoColor=white">
</picture>

# <img src="https://em-content.zobj.net/source/apple/391/test-tube_1f9ea.png" width="32" /> Tide

### HAR-Driven, Source-Aware API Test Generation

<br />

**一句话说清**：丢入浏览器 HAR 抓包，自动出生产级 pytest 测试套件。

基于 **Claude Code Plugin** 构建，并提供 **Codex / Cursor** 适配入口的 AI 接口自动化测试生成引擎，5 个 Agent 协同、4 波编排。

<br />

📡 HAR 解析 &nbsp;·&nbsp; 🔍 源码追踪 &nbsp;·&nbsp; 🧪 L1-L5 断言 &nbsp;·&nbsp; ⚡ 并行生成 &nbsp;·&nbsp; 📊 Allure 报告

<br />

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org/)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-7C3AED?style=flat-square&logo=anthropic&logoColor=white)](https://claude.ai/code)
[![pytest](https://img.shields.io/badge/pytest-Framework-0A9EDC?style=flat-square&logo=pytest&logoColor=white)](https://pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](./LICENSE)
[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg?style=flat-square)](./pyproject.toml)

<br />

```
📡 HAR ─── /tide ──→ 🔍 源码分析 ──→ 🧪 pytest 测试套件 ──→ 📊 Allure 报告
```

</div>

<br />

---

## 目录

- [核心特性](#核心特性)
- [工作流总览](#工作流总览)
- [断言层级](#断言层级)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [融入已有项目](#融入已有项目)
- [配置参考](#配置参考)
- [项目结构](#项目结构)
- [开发](#开发)
- [Roadmap](#roadmap)
- [License](#license)

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **HAR → pytest** | 浏览器录制的 HAR 文件自动转化为生产级 pytest 测试套件，零样板代码 |
| **源码感知** | 读取后端源码（Controller → Service → DAO），深度理解业务逻辑 |
| **L1-L5 断言** | 从 HTTP 状态码（L1）到 AI 推断的隐式业务规则（L5），5 层断言递进覆盖 |
| **5 Agent 协同** | har-parser · repo-syncer · scenario-analyzer · case-writer · case-reviewer |
| **4 波并行编排** | 解析 → 分析 → 生成 → 评审，波次内并行、波次间串行，充分利用 AI 能力 |
| **安全校验** | HAR 输入 Pydantic 校验、repo-profiles YAML schema 验证、分支容错 |
| **Hook 系统** | 9 个 Hook 点（wave1-4 before/after + output:notify），YAML 配置注入自定义处理 |
| **偏好学习** | 跨会话偏好持久化（断言风格、fixture 作用域等），自动修正生成风格 |
| **格式检查** | AST 级 Python 代码检查（FC01-FC10），CLI 集成，覆盖 docstring/print/行长等 |
| **智能项目分类** | 自动检测已有自动化项目 vs 新项目，阈值保守、不误判覆盖 |
| **行业感知** | 收集行业画像 → AI 调研 → 2-3 方案推荐，行业断言全流程贯穿 |
| **方案推荐** | 基于行业/团队/鉴权复杂度，推荐完整技术方案（框架+CI+报告+Mock+数据管理） |
| **旧项目无侵入** | 自动检测已有项目的测试目录、API 封装、断言风格，沿用原有规范 |
| **交互式确认** | 每个关键节点提供确认清单，支持 `--quick` 跳过和断点恢复 |
| **验证透明** | 每波次结束明确输出验证摘要（py_compile / import 检查 / 断言覆盖率） |
| **任务可视化** | 全流程进度实时可见，spinner 显示当前阶段，子步骤逐项追踪 |

---

## 工作流总览

![Tide Pipeline](assets/workflow.png)

<details>
<summary><b>4 波次详解</b></summary>

### Wave 1：解析与准备（并行）

| Agent | 模型 | 输入 | 输出 |
|-------|------|------|------|
| **har-parser** | haiku | HAR 文件 | `.tide/parsed.json` |
| **repo-syncer** | haiku | `repo-profiles.yaml` | `.tide/repo-status.json` |

两个 Agent 并行执行。无源码仓库时自动跳过 repo-syncer。

### Wave 2：场景分析（交互式）

| Agent | 模型 | 职责 |
|-------|------|------|
| **scenario-analyzer** | opus | 源码追踪 + 场景推断 + 断言计划 |

- 追踪 Controller → Service → DAO 调用链
- 推断正常路径、异常路径、边界值、CRUD 闭环等 8 种场景类别
- 规划每个场景的 L1-L5 断言层级
- 生成确认清单，用户确认后继续

### Wave 3：代码生成（并行扇出）

| Agent | 模型 | 职责 |
|-------|------|------|
| **case-writer ×N** | sonnet | 按模块并行生成 pytest 测试文件 |

- 每个服务模块独立一个 Agent
- 遵循项目已有的代码风格（API 封装、Request 工具类、allure 标注等）
- 生成后自动进行 py_compile 验证

### Wave 4：评审与交付（交互式）

| Agent | 模型 | 职责 |
|-------|------|------|
| **case-reviewer** | opus | 5 维评审 + 自动修复 + 执行 |

5 个评审维度：
1. **断言完整性** — L1-L5 逐层验证
2. **场景完整性** — CRUD 闭环、异常路径、边界值
3. **源码交叉核验** — 断言值与源码实际逻辑一致
4. **代码质量** — 无硬编码、不可变模式、规模限制
5. **可运行性** — 导入完整、语法正确、fixture 可用

偏差率处理：`< 15%` 静默修复 · `15-40%` 修复并警告 · `> 40%` 阻断

</details>

<details>
<summary><b>任务可视化</b></summary>

Tide 在流程开始时创建任务清单，实时展示当前进度：

**`/tide` 执行时的任务面板：**

| 状态 | 任务 |
|------|------|
| ✅ | 预检与参数校验 |
| ✅ | [1/4] 解析与准备 |
| ▶ 分析测试场景... | [2/4] 场景分析 |
| ○ | [3/4] 代码生成 |
| ○ | [4/4] 评审与交付 |
| ○ | 验收报告与归档 |

**`/using-tide` 执行时的任务面板：**

| 状态 | 任务 |
|------|------|
| ✅ | 环境检测 + 智能分类 |
| ▶ 扫描项目代码... | 深度扫描（已有项目） |
| ○ | 7 维度确认 |
| ○ | 源码仓库配置 |
| ○ | 连接配置 |
| ○ | 脚手架生成 + 配置验证 |

每个任务包含子步骤描述，完成后自动标记。分支确定后任务名称自动更新。

</details>

---

## 断言层级

![Assertion Layers](assets/assertion_layers.svg)

| 层级 | 名称 | 覆盖内容 | 生成条件 |
|------|------|----------|----------|
| **L1** | 协议层 | HTTP 状态码 · 响应时间 · Content-Type | 所有接口（100%） |
| **L2** | 结构层 | Schema 验证 · 字段类型 · 存在性检查 | 有响应体的接口 |
| **L3** | 数据层 | 值范围 · 枚举合法性 · 分页不变量 | 有源码参考时 |
| **L4** | 业务层 | 状态机 · CRUD 一致性 · 数据库验证 | 配置了数据库连接 |
| **L5** | AI 推断层 | 隐式规则 · 安全边界 · 异常路径 | 源码追踪 + 高置信度 |

每层断言代码示例参见 [references/assertion-examples.md](references/assertion-examples.md)。

---

## 快速开始

### 前置条件

- Claude Code、Codex 或 Cursor（任选其一作为 AI 编排入口）
- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器（推荐）或 pip
- Git

### Claude Code 安装

```bash
# 方式一：从 marketplace 安装（推荐）
claude plugins marketplace add koco-co/tide
claude plugins install tide

# 方式二：或直接克隆（适用于全局安装）
git clone https://github.com/koco-co/tide.git ~/.claude/plugins/tide
cd ~/.claude/plugins/tide && uv sync

# 验证安装
claude plugins list
```

安装后，进入你的测试项目目录启动 Claude Code：

```bash
cd /path/to/your-test-project
claude
```

### Codex / Cursor 适配

Tide 同仓库提供 Codex 与 Cursor 的项目级适配文件：

| 入口 | 文件 | 使用方式 |
|------|------|----------|
| Codex 插件 | `.codex-plugin/plugin.json`、`codex-skills/`、`commands/` | 安装为本地 Codex 插件后使用 `$using-tide` / `$tide`，或 `/using-tide` / `/tide` 命令 |
| Cursor 项目规则 | `.cursor/rules/*.mdc`、`.cursor/commands/*.md` | 在 Cursor 中打开 Tide 仓库或拷贝 `.cursor/` 到项目后使用 `using-tide` / `tide` 命令 |

Codex 和 Cursor 适配层复用同一套 `scripts/`、`agents/`、`prompts/` 资产，不改变 Claude Code 入口。

---

## 使用指南

### 第一步：初始化项目（仅首次）

在 Claude Code、Codex 或 Cursor 中运行初始化入口：

```
/using-tide
```

这是一个交互式向导，会根据项目类型自动选择路径：

**已有自动化项目**（如 dtstack-httprunner）→ 自动检测为 existing：

| 步骤 | 说明 |
|------|------|
| 项目扫描 | 自动通读代码，检测 API 封装方式、HTTP 客户端、断言风格等 |
| 交互确认 | 逐项确认扫描结果，可手动调整 |
| 仓库配置 | 输入后端仓库 URL（可选，用于源码分析增强断言） |
| 连接配置 | Base URL · 认证方式 |
| 生成配置 | 写入 `tide-config.yaml` |

**全新项目** → 自动检测为 new：

| 步骤 | 说明 |
|------|------|
| 行业画像 | 选择行业、系统类型、团队规模 |
| AI 调研 | 自动搜索行业最佳实践，推荐技术方案 |
| 方案确认 | 选择技术栈（框架/客户端/报告/CI 等） |
| 脚手架 | 生成完整的项目结构 + 示例测试 |

生成文件：`tide-config.yaml` · `repo-profiles.yaml`

### 第二步：录制 HAR 文件

在浏览器开发者工具 Network 面板中操作目标系统，导出 `.har` 文件。

### 第三步：生成测试

```bash
# 标准模式（全流程 + 交互确认）
/tide ./recordings/api.har

# 快速模式（跳过确认清单，适合 CI）
/tide ./recordings/api.har --quick

# 恢复中断的会话
/tide --resume
```

在 Codex 中也可以使用 `$tide <har-file>`；在 Cursor 中可以使用 `.cursor/commands/tide.md` 对应的 `tide <har-file>` 命令。

#### 约定适配（自动）

Tide 在生成测试代码时会自动适配目标项目的编码规范——无需手动配置：

| 检测维度 | 自动适配行为 |
|---------|------------|
| API 定义 | Enum 类如 `BatchApi.create_project.value`、Class 常量、或内联 URL |
| HTTP 客户端 | 自定义 `BaseRequests`、`httpx`、或 `requests` |
| 断言风格 | `resp["code"] == 1`、`resp.status_code == 200`、或 `resp.get("key")` |
| 测试结构 | `*_test.py` 后缀或 `test_*.py`、`setup_class` 或 conftest fixture |
| Allure 标注 | 自动生成 `@allure.feature` / `@allure.story`，或不使用 |
| pytest markers | 自动应用项目已有的 markers（如 `@pytest.mark.smoke`）|

适配信息来自 `scripts/convention_scanner.py` 的 AST 检测，存储在 `.tide/convention-scout.json` 中。

### 第四步：验收

生成完成后输出验收命令：

```bash
# 收集测试用例（验证语法）
pytest --collect-only

# 执行测试 + Allure 报告
pytest -v --alluredir=.tide/allure-results

# 查看 Allure 报告
allure serve .tide/allure-results
```

> 实际命令会根据项目的配置自动适配。

---

## 常见场景

### 场景 A：全新项目从零开始

```bash
mkdir my-api-tests && cd my-api-tests && git init
# 启动 Claude Code → /using-tide
```

生成脚手架：`tests/` · `conftest.py` · `pyproject.toml` · `Makefile`

### 场景 B：已有自动化项目（如 dtstack-httprunner）

```bash
cd /path/to/existing-test-project
# 启动 Claude Code → /using-tide（初始化配置）
# → /tide ./recordings/api.har（生成测试）
```

Tide 会自动检测：
- API 封装模式（Enum / Class / 内联）
- 自定义 HTTP 客户端和调用签名
- 断言风格和辅助方法
- 测试文件命名规范
- pytest markers
- Allure 使用模式

生成的测试代码自动遵循已有项目的编码规范，无侵入。

### 场景 C：纯脚本模式（不使用 Claude Code）

```bash
git clone https://github.com/koco-co/tide.git
cd tide && uv sync

# 执行项目扫描（输出 convention-scout.json）
uv run python3 scripts/convention_scanner.py --project-root /path/to/project

# HAR 解析
uv run python -c "
from scripts.har_parser import parse_har
from pathlib import Path
result = parse_har(Path('your.har'), Path('repo-profiles.yaml'))
print(f'解析到 {len(result.endpoints)} 个接口')
"
```

> 纯脚本模式仅提供 HAR 解析、脚手架、通知等基础工具，不含 AI 场景分析和用例生成。

---

## 配置参考

### repo-profiles.yaml

```yaml
repos:
  - name: backend-service
    local_path: .repos/group/backend/
    remote: https://git.example.com/group/backend.git
    branch: release_1.0
    url_prefixes:
      - /api/v1
```

### tide-config.yaml

```yaml
project:
  type: existing          # existing | new
  test_dir: testcases     # 测试入口目录
  test_types:             # 要生成的测试类型
    - interface
    - scenariotest
  code_style:
    api_pattern: enum     # enum | constant | inline
    request_class: BaseRequests
    assertion_style: "resp['code'] == 1"
    auth_method: reuse    # cookie | token | password | none | reuse
    allure_enabled: true
  package_manager: pip    # uv | pip | poetry

# 行业信息（由 /using-tide 自动生成）
industry:
  domain: "金融/银行"
  system_type: "微服务架构"
  team_size: "3-5人"
  auth_complexity: complex
  special_needs: ["multi_env"]
  compliance: ["等保三级", "数据脱敏"]

solution:
  name: "金融级 API 自动化方案"
  fit_score: 92
  stack:
    framework: pytest
    http_client: httpx
    report: allure
    mock: wiremock
    ci: github_actions
    data_management: factory_boy
  industry_specific:
    - "金融交易幂等性断言"
    - "敏感数据字段脱敏验证"
```

### 环境变量（.env）

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `BASE_URL` | 是 | 被测服务基础 URL |
| `AUTH_COOKIE` | 否 | 认证 Cookie（或 `AUTH_TOKEN`） |
| `DB_PASSWORD` | 否 | 数据库密码（L4 断言需要） |
| `DINGTALK_WEBHOOK` | 否 | 钉钉 Webhook |
| `FEISHU_WEBHOOK` | 否 | 飞书 Webhook |
| `SLACK_WEBHOOK` | 否 | Slack Webhook |

---

## 项目结构

```text
tide/
├── .codex-plugin/                   # Codex 插件元数据
├── .cursor/                         # Cursor 项目规则与命令
│   ├── commands/                    #   tide / using-tide 命令
│   └── rules/                       #   Tide 工作流项目规则
├── skills/                          # Claude Code 技能定义
│   ├── tide/SKILL.md            #   /tide — 主流程（4 波编排）
│   └── using-tide/SKILL.md      #   /using-tide — 初始化向导
├── codex-skills/                    # Codex 技能定义
│   ├── tide/SKILL.md                #   $tide — HAR 生成 pytest
│   └── using-tide/SKILL.md          #   $using-tide — 初始化向导
├── commands/                        # Codex slash command 文档
│   ├── tide.md
│   └── using-tide.md
├── agents/                          # 5 个 Agent 定义
│   ├── har-parser.md                #   HAR 解析（haiku）
│   ├── repo-syncer.md               #   仓库同步（haiku）
│   ├── scenario-analyzer.md         #   场景分析（opus）
│   ├── case-writer.md               #   代码生成（sonnet）
│   ├── case-reviewer.md             #   评审修复（opus）
│   ├── project-scanner.md           #   项目深度扫描（opus）
│   └── industry-researcher.md       #   行业调研（sonnet）             #   评审修复（opus）
├── prompts/                         # Agent 规范文档（按需加载）
│   ├── code-style-python/           # Python 代码风格模块
│   │   ├── 00-core.md               #   通用核心规范
│   │   ├── 10-api-enum.md           #   Enum 风格 API
│   │   ├── 20-client-custom.md      #   自定义 HTTP 客户端
│   │   ├── 30-assert-code-success.md #   resp['code']==1 断言
│   │   └── ...                      #   更多条件模块
│   ├── assertion-layers.md          #   L1-L5 断言规范
│   ├── har-parse-rules.md           #   HAR 解析过滤规则
│   ├── review-checklist.md          #   评审清单与质量标准
│   ├── scenario-enrich.md           #   8 种场景类别生成策略
│   └── industry-assertions.md       #   行业特定断言规范
├── scripts/                         # Python 工具库
│   ├── common.py                    #   共享常量、JSON/日志工具
│   ├── har_parser.py                #   HAR 解析与去重（Pydantic 校验）
│   ├── scaffold.py                  #   脚手架生成（new/existing 模式）
│   ├── state_manager.py             #   波次检查点管理
│   ├── test_runner.py               #   pytest 执行包装（uv/pip/poetry）
│   ├── repo_sync.py                 #   Git 同步（含分支容错）
│   ├── notifier.py                  #   钉钉/飞书/Slack 通知
│   ├── hooks.py                     #   Hook 注册表与 YAML 加载
│   ├── preferences.py               #   偏好学习（跨会话持久化）
│   └── format_checker.py            #   AST 格式检查（FC01-FC10）
├── templates/                       # Jinja2 模板
├── references/                      # 参考文档
├── assets/                          # 流程图资源
├── .claude-plugin/                  # Claude Code 插件元数据
├── pyproject.toml                   # 项目配置
├── Makefile                         # 开发命令
└── LICENSE
```

---

## 开发

```bash
git clone https://github.com/koco-co/tide.git
cd tide
uv sync --dev

make test       # 运行测试
make lint       # ruff 代码检查
make typecheck  # pyright 类型检查
make ci         # lint + typecheck + test
make fmt        # 代码格式化
```

---

## Roadmap

| 版本 | 主要特性 |
|------|---------|
| **v1.0** | HAR 解析 · 4 波编排 · L1-L5 断言 · DB 验证 · 检查点恢复 · 外部通知 |
| **v1.1** | 旧项目适配 · 验证透明度 · 验收命令优化 · 路径修复 · 测试类型选择 |
| **v1.3**（当前） | 跨项目优化 · Hook 系统 · 偏好学习 · 格式检查器 · Codex/Cursor 适配 · no-source mode 泛化 |
| **v1.4**（进行中） | Convention 指纹驱动适配 · Prompt 按需加载（省 ~50% tokens）· 成本预估 · 多项目风格扩展框架 |
| v1.4 | OpenAPI / Swagger spec 作为补充输入源 |
| v2.0 | UI 自动化集成（Playwright）· 性能测试 |

---

## Contributing

欢迎提交 Issue 和 Pull Request。提交前请确保：

```bash
make ci   # 所有检查通过
```

---

## License

[MIT](./LICENSE) &copy; 2026 Tide contributors
