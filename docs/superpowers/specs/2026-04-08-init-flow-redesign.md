# /using-tide 初始化流程重构设计

> 日期：2026-04-08
> 状态：已确认，待实施

---

## 背景

当前 `/using-tide` 初始化流程采用固定的技术栈选项（推荐/保守/自定义），对已有项目只做配置文件级别的扫描（ruff/mypy 等），存在以下不足：

1. **已有项目**：只检测代码风格配置，未深度理解代码逻辑、架构模式、鉴权方式
2. **新项目**：提供固定框架选项，未考虑用户行业、平台、团队等因素
3. **行业上下文**：完全缺失，后续 /tide 生成测试时无法参考行业特性

## 设计目标

- 已有自动化项目：Agent 深度通读 → 交互式逐项确认 → 写入配置
- 新项目：收集行业画像 → Agent 网络调研 → 2-3 个完整技术方案 → 用户选择
- 行业信息全流程影响（初始化 + 后续 /tide 生成）
- 多环境/多版本：初始化时收集信息并记录，实际功能留后续版本

---

## 总体流程架构

```
┌─────────────────────────────────────────────────┐
│ 第零步：环境检测 + 智能分类                        │
│   检测工具 → 扫描项目标志 → 判定项目类型              │
│   输出：project_type = existing_auto | new          │
│   特殊：检测到 tide-config.yaml → 快速重初始化    │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌───────────────┐  ┌────────────────────┐
│ 分支 A：      │  │ 分支 B：            │
│ 已有自动化项目 │  │ 新项目 / 非自动化    │
└───────┬───────┘  └────────┬───────────┘
        │                   │
        ▼                   ▼
┌───────────────┐  ┌────────────────────┐
│ 第一步：      │  │ 第一步：            │
│ 深度扫描 Agent│  │ 行业画像收集         │
│ 通读项目代码  │  │ 5 个问题             │
│ 逐项确认(7维) │  │ 一次一个             │
└───────┬───────┘  └────────┬───────────┘
        │                   │
        │                   ▼
        │          ┌────────────────────┐
        │          │ 第二步：            │
        │          │ 调研 Agent          │
        │          │ WebSearch 行业方案   │
        │          │ 输出 2-3 方案        │
        │          │ 用户选择             │
        │          │ 方案试运行(1个示例)   │
        │          └────────┬───────────┘
        │                   │
        ├───────────────────┘
        ▼
┌─────────────────────────────────────────────────┐
│ 第三步：源码仓库配置（共用）                        │
│ 第四步：连接配置（按行业/分支定制深度）              │
│ 第五步：脚手架生成 + CLAUDE.md + 配置验证            │
└─────────────────────────────────────────────────┘
```

---

## 第零步：环境检测 + 智能分类

### 环境检测（同现有）

```bash
python3 --version   # >= 3.12
uv --version
git --version
```

检测插件依赖（jinja2, pydantic, pyyaml），缺失则自动安装。

### 快速重初始化检测

检查 `tide-config.yaml` 是否已存在：

```
若已存在：
AskUserQuestion(
  "检测到已有 Tide 配置（上次初始化：<日期>）。",
  options=[
    "使用现有配置直接进入 /tide（推荐）",
    "更新配置（只修改变更项）",
    "完全重新初始化"
  ]
)
```

- 选择「使用现有配置」→ 直接终止，提示用户运行 /tide
- 选择「更新配置」→ 读取现有配置，只询问用户想修改的部分
- 选择「完全重新初始化」→ 备份现有配置到 `.tide/backup/`，继续完整流程

### 智能分类

**分类信号矩阵：**

| 信号 | 权重 | 检测方式 |
|------|------|----------|
| 测试文件数量 (test_*.py / *_test.py) | 高 | find 测试目录 |
| conftest.py 存在且非空 | 高 | `test -s conftest.py` |
| pytest/unittest 配置存在 | 中 | pyproject.toml / pytest.ini / setup.cfg |
| HTTP 客户端导入 | 中 | grep requests/httpx/BaseRequests |
| allure 使用 | 低 | grep `import allure` |
| CI 配置存在 | 低 | .github/workflows / .gitlab-ci.yml |

**判定规则：**

```
if 测试文件数 >= 3 AND (conftest存在 OR pytest配置存在):
    project_type = "existing_auto"
else:
    project_type = "new"
```

阈值设低（3 个文件），宁可走保守路径也不误判覆盖。

**边界情况：**

- 1-2 个零散脚本 → 判为 `new`，但提示"检测到少量测试文件，如需保留请告知"
- tests/ 目录存在但全空 → 判为 `new`
- 检测到非 Python 测试框架（Java/JS）→ 提示"检测到非 Python 测试代码，Tide 目前仅支持 Python"

---

## 分支 A：已有自动化项目

### Agent 设计：project-scanner

- **模型：** opus
- **工具：** Read, Grep, Glob, Bash
- **输入：** 项目根目录
- **输出：** `.tide/project-profile.json`

### 增量检测

若 `project-profile.json` 已存在且项目在 Git 管理下：

```bash
git diff --name-only <上次扫描commit>..HEAD
```

变更文件 < 20 个 → 只分析变更部分（增量模式）
变更文件 >= 20 个或无上次记录 → 全量扫描

增量模式输出：
```
上次扫描后检测到 <N> 个文件变更。增量扫描结果：
  API 封装模式：    无变化
  鉴权逻辑：        检测到 OAuth2 相关代码（新增）
  ...
```

### 7 维度交互式确认

Agent 扫描完成后，按以下 7 个维度逐项展示并确认：

**维度 1：项目架构**
- 测试入口目录（testcases/ vs tests/ vs test/）
- 子目录结构及各目录文件数
- conftest 层级分布
- 工具类/辅助目录

**维度 2：代码风格**
- API 封装模式（Enum / 常量 / inline）
- Request 封装（BaseRequests / httpx / requests.Session）
- 断言风格（resp['code'] == 1 / assert resp.status_code == 200）
- 命名规范

**维度 3：鉴权方式**
- 认证类位置和实现方式
- 认证方式（Cookie / Token / OAuth2）
- 多环境 Token 支持

**维度 4：依赖与工具链**
- Python 版本要求
- 包管理器（pip / uv / poetry）
- HTTP 客户端及版本
- 测试框架配置
- Linter / Formatter

**维度 5：Allure 使用模式**
- 装饰器层级（epic → feature → story）
- 步骤模式（allure.step 使用比例）
- 严重等级标注比例

**维度 6：数据管理模式**
- 测试数据来源（JSON / DB / API）
- 数据驱动方式（parametrize 使用情况）
- 数据库操作类
- 清理策略

**维度 7：行业与业务上下文**
- Agent 从代码推断的行业/领域
- 核心业务概念
- 合规要求检测

每个维度以表格形式展示检测结果，用户确认或在 Other 中纠正。

### 输出

确认后生成/更新：
- `.tide/project-profile.json` — 完整扫描结果（机器可读）
- `tide-config.yaml` — 合并 7 个维度的确认结果
- `CLAUDE.md` — 包含项目理解的上下文说明

---

## 分支 B：新项目 / 非自动化项目

### 阶段 1：行业画像收集

5 个问题，一次一个 AskUserQuestion：

**Q1 — 行业领域**
选项：互联网/SaaS、金融/银行/保险、医疗/健康、电商/零售（+ Other）

**Q2 — 被测系统类型**
选项：Web 后端 API (REST/GraphQL)、微服务架构、移动端 BFF、开放平台/第三方 API 集成

**Q3 — 团队规模与自动化经验**
选项：1-2 人刚开始、3-5 人有基础、5+ 人成熟体系

**Q4 — 特殊需求**（多选）
选项：多环境切换、多版本 API 共存、国际化/多语言、性能测试/压力测试

**Q5 — 鉴权复杂度**
选项：简单（单一 Cookie/Token）、中等（多角色 RBAC）、复杂（OAuth2/SSO/多租户）、不确定

### 阶段 2：调研 Agent

**Agent 设计：industry-researcher**

- **模型：** sonnet
- **工具：** WebSearch, WebFetch, Read, Write
- **输入：** 行业画像（5 个问题的答案）
- **输出：** `.tide/research-report.json`

Agent 调研内容：
1. 该行业的 API 自动化测试最佳实践
2. 适合团队规模的测试框架和工具链
3. 行业特定的合规/安全测试需求
4. CI/CD 集成方案、报告系统、Mock 服务
5. 数据工厂和测试数据管理方案

输出格式：

```json
{
  "industry_context": {
    "domain": "金融/银行",
    "key_concerns": ["数据安全", "幂等性", "审计日志"],
    "compliance": ["等保三级", "数据脱敏"],
    "references": ["<调研来源URL>"]
  },
  "recommended_solutions": [
    {
      "name": "方案名称",
      "summary": "一句话总结",
      "stack": {
        "framework": "pytest",
        "http_client": "httpx",
        "report": "allure",
        "mock": "wiremock",
        "ci": "github_actions",
        "data_management": "factory_boy"
      },
      "pros": ["..."],
      "cons": ["..."],
      "fit_score": 85,
      "industry_specific": [
        "金融交易幂等性断言",
        "敏感数据字段脱敏验证"
      ]
    }
  ]
}
```

### 阶段 3：方案呈现与选择

以对比表格形式展示 2-3 个方案：
- 每个方案包含：名称、适合度评分、技术栈、优劣势、行业特性
- 用户通过 AskUserQuestion 选择

### 阶段 4：方案试运行

用户选择方案后，不直接全量生成脚手架，而是：

1. 从调研方案的 `industry_specific` 中选取最具代表性的接口类型（如金融行业选"转账"，电商选"下单"），生成一个 GET + POST 的最小示例测试文件
2. 展示给用户，确认代码风格和结构
3. 用户确认后再全量生成

```
AskUserQuestion(
  "以下是基于所选方案生成的示例测试文件（test_example.py）。
   请确认代码风格是否符合预期：\n\n"
  "<示例代码摘要>\n\n"
  "A) 风格正确，继续全量生成
   B) 需要调整，我在 Other 中说明"
)
```

### 行业信息持久化

```yaml
# tide-config.yaml
industry:
  domain: "金融/银行"
  system_type: "微服务架构"
  team_size: "3-5人"
  auth_complexity: "complex"
  special_needs: ["multi_env", "multi_version"]
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
    data: factory_boy
  industry_specific:
    - "金融交易幂等性断言"
    - "敏感数据字段脱敏验证"
```

---

## 后续共用步骤适配

### 第三步：源码仓库配置

- 基本同现有流程
- 新增：分支 B 若方案包含 Mock 服务，额外询问"是否配置 Mock 服务仓库？"

### 第四步：连接配置

按 `auth_complexity` 调整询问深度：

| 鉴权复杂度 | 询问内容 |
|-----------|---------|
| 简单 | Cookie 或 Token |
| 中等 | + 角色列表、RBAC 配置 |
| 复杂 | + OAuth2 client_id/secret、SSO 端点、多租户 ID |

分支 A 保留「复用旧项目认证逻辑」选项。

### 第五步：脚手架生成 + CLAUDE.md + 配置验证

**分支 A：**
- 调用 `scaffold.py --mode existing`，只追加 .tide/ 相关文件
- CLAUDE.md 包含 Agent 扫描的 7 维度项目理解

**分支 B：**
- 根据选定方案生成完整脚手架
- CLAUDE.md 包含行业上下文和方案信息

**配置验证（两个分支共用）：**

在脚手架生成后，自动执行 smoke test 验证配置：

```bash
# 1. Base URL 可达性
python3 -c "import httpx; r = httpx.get('${BASE_URL}'); print(f'HTTP {r.status_code}')"

# 2. 认证有效性
python3 -c "import httpx; r = httpx.get('${BASE_URL}', headers={...}); print(f'Auth: {r.status_code}')"

# 3. 数据库连接（若配置）
python3 -c "import pymysql; conn = pymysql.connect(...); print('DB OK'); conn.close()"
```

失败时立即反馈并协助修复：
```
配置验证结果：
  Base URL 可达性：  通过 (HTTP 200)
  认证有效性：        失败 (HTTP 401 — Cookie 可能已过期)
  数据库连接：        通过
  
认证失败，是否立即更新 Cookie？
```

---

## 全流程行业影响

`tide-config.yaml` 中的 `industry` 段将在后续 `/tide` 流程中被以下 Agent 读取：

| Agent | 影响 |
|-------|------|
| scenario-analyzer | 增加行业特定场景类别（如金融幂等性测试、医疗脱敏验证） |
| case-writer | 在 L3/L5 断言中加入行业合规检查 |
| case-reviewer | 评审时检查行业特定测试是否覆盖 |

示例：金融行业自动增加的断言：
```python
# L3: 幂等性检查（行业：金融）
resp1 = client.post("/api/v1/transfer", json=payload)
resp2 = client.post("/api/v1/transfer", json=payload)  # 相同请求
assert resp2.json()["code"] == "DUPLICATE_REQUEST"
```

---

## 新增 Agent 清单

| Agent | 模型 | 用途 | 分支 |
|-------|------|------|------|
| project-scanner | opus | 深度通读已有项目代码，输出 7 维度分析 | A |
| industry-researcher | sonnet | 网络调研行业自动化最佳实践，输出 2-3 方案 | B |

---

## 文档与资产更新

### 流程图更新

使用 `cli-anything-drawio` 工具（路径：`/Users/poco/Projects/CLI-Anything/drawio`）重新绘制工作流总览图。

**需要生成的流程图：**

1. **`assets/workflow.drawio`** — 初始化 + 主流程全景图（替换现有 `assets/workflow.png`）

流程图需体现：
- 第零步的智能分类（existing_auto / new 两条分支）
- 分支 A 的 project-scanner Agent → 7 维度确认
- 分支 B 的行业画像 → industry-researcher Agent → 方案选择 → 试运行
- 合流后的共用步骤（仓库配置 → 连接配置 → 脚手架 + 验证）
- /tide 4 波次流程（行业信息贯穿）

**绘制方式：**

```bash
DRAWIO="cli-anything-drawio"

# 1. 创建项目
$DRAWIO project new --preset 16:9 -o assets/workflow.drawio

# 2. 添加形状和连接器
$DRAWIO --project assets/workflow.drawio shape add ...
$DRAWIO --project assets/workflow.drawio connect add ...

# 3. 导出为 PNG（用于 README 引用）
$DRAWIO --project assets/workflow.drawio export render assets/workflow.png -f png
```

**注意：** 断言层级图（`assets/assertion_layers.svg`）保持不变，不需要重绘。

### README 更新要点

更新 `README.md` 中以下章节以反映新初始化流程：

| 章节 | 变更 |
|------|------|
| 核心特性 | 新增「智能项目分类」「行业感知」「方案推荐」特性 |
| 工作流总览 | 替换流程图引用，新增初始化流程说明 |
| 快速开始 | 更新初始化步骤描述 |
| 使用指南 > 步骤 1 | 重写，体现分支 A/B 的不同路径 |
| 融入已有项目 | 重写场景 A（深度扫描）和场景 B（行业调研）的说明 |
| 配置参考 > tide-config.yaml | 新增 `industry` 和 `solution` 段的文档 |
| 项目结构 | 新增 project-scanner 和 industry-researcher Agent |
| Roadmap | 更新 v1.2 特性列表 |

---

## 实施影响

### 需修改的文件

| 文件 | 变更 |
|------|------|
| `skills/using-tide/SKILL.md` | 重写整个初始化流程 |
| `skills/tide/SKILL.md` | 预检阶段读取 industry 配置 |
| `agents/case-writer.md` | 增加行业感知断言生成规则 |
| `agents/scenario-analyzer.md` | 增加行业特定场景类别 |
| `agents/case-reviewer.md` | 增加行业合规评审维度 |
| `scripts/scaffold.py` | 支持方案驱动的脚手架生成 |
| `prompts/code-style-python.md` | 增加行业特定代码风格规则 |
| `README.md` | 更新使用指南、配置参考、流程图 |
| `assets/workflow.drawio` | 使用 cli-anything-drawio 重绘初始化 + 主流程全景图 |
| `assets/workflow.png` | 从 .drawio 导出的 PNG 版本 |

### 需新增的文件

| 文件 | 用途 |
|------|------|
| `agents/project-scanner.md` | 项目深度扫描 Agent 定义 |
| `agents/industry-researcher.md` | 行业调研 Agent 定义 |
| `templates/tide-config.yaml.j2` | 配置文件模板 |
| `prompts/industry-assertions.md` | 行业特定断言规范 |

---

## 版本规划

此重构对应 **v1.2** 版本，主要特性标签：

- 智能项目分类
- 深度项目扫描（7 维度）
- 行业画像与调研
- 方案推荐系统
- 配置验证
- 全流程行业感知
- 流程图重绘（cli-anything-drawio）
- README 全面更新
