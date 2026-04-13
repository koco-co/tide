---
name: autoflow
description: "从 HAR 文件生成 pytest 测试套件，结合源码进行 AI 智能分析。触发方式：/autoflow <har-path>、'从 HAR 生成测试'、提供 .har 文件路径。"
argument-hint: "<har-file-path> [--quick] [--resume]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, TaskCreate, TaskUpdate, TaskList
---

# AutoFlow：HAR 转 Pytest 测试生成技能

将浏览器 HAR 抓包文件转换为完整的 pytest 测试套件，
采用四波次编排流水线：解析、分析、生成、评审。

---

## 任务初始化

在流程开始时，批量创建 6 个任务以可视化全流程进度：

```
TaskCreate(subject="预检与参数校验", activeForm="校验 HAR 文件与项目配置",
  description="子步骤：环境检查 → HAR 校验 → 认证头扫描 → 参数摘要输出")

TaskCreate(subject="[1/4] 解析与准备", activeForm="解析 HAR 文件",
  description="子步骤：启动 har-parser Agent → 启动 repo-syncer Agent（若有源码）→ 验证 parsed.json 完整性 → 输出验证摘要 → 检查点保存")

TaskCreate(subject="[2/4] 场景分析", activeForm="分析测试场景",
  description="子步骤：启动 scenario-analyzer Agent → 生成 scenarios.json → 展示确认清单（--quick 跳过）→ 验证摘要 → 检查点保存")

TaskCreate(subject="[3/4] 代码生成", activeForm="生成测试代码",
  description="子步骤：按模块并行启动 case-writer Agent ×N → py_compile 验证 → AST 检查 → 失败文件自动修复 → 验证摘要 → 检查点保存")

TaskCreate(subject="[4/4] 评审与交付", activeForm="评审测试代码",
  description="子步骤：启动 case-reviewer Agent → 5 维评审 → 自动修复 → 执行测试 → 生成执行报告")

TaskCreate(subject="验收报告与归档", activeForm="生成验收报告",
  description="子步骤：汇总评审+执行报告 → 展示验收清单 → 发送通知（若配置）→ 归档会话")
```

将每个 TaskCreate 返回的 ID 依次记为 `<task_1_id>` 到 `<task_6_id>`，后续阶段引用这些 ID 进行状态更新。

---

## 预检阶段

设置路径变量：

```
PLUGIN_DIR="${CLAUDE_SKILL_DIR}/../.."
```

解析 `$ARGUMENTS`，提取以下参数：
- `har_path` — 第一个位置参数（必填）
- `--quick` — 跳过第二波次的用户确认
- `--resume` — 从上次保存的检查点恢复

**1. 环境检查**

```bash
test -f repo-profiles.yaml || echo "MISSING"
```

若 `repo-profiles.yaml` 不存在：

```
AutoFlow 需要已初始化的项目。
请先运行 /using-autoflow，再重试。
```

立即终止。

**2. 项目配置读取**

读取 `repo-profiles.yaml`，提取以下配置：
- `repos` 列表 — 源码仓库清单
- `test_dir` — 测试目录路径（如 `testcases/` 或 `tests/`），默认为 `tests/`

读取 `autoflow-config.yaml`（若存在），提取以下配置：
- `test_types` — 用户选择的测试类型列表（如 `["interface", "scenario"]`），默认为全部类型
- `industry` — 行业画像（若存在），提取 `domain`、`compliance`、`special_needs`
- `solution.industry_specific` — 行业特定测试策略列表
- `project.code_style` — 已有项目的代码风格配置（若 `project.type == "existing"`）

若 `industry` 段存在，设置 `industry_mode = true`，后续波次传递行业上下文给下游 Agent。

**3. 无源码降级检测**

检查 `repos` 列表是否为空。若为空：

```
注意：未配置源码仓库。
  - 将跳过 repo-syncer 同步步骤
  - 场景分析将降级为「仅 HAR 分析」模式
  - L3-L5 断言标记为「低置信度」
```

设置 `no_source_mode = true`，后续波次据此分支处理。

**4. 恢复检查**

```bash
test -f .autoflow/state.json && cat .autoflow/state.json
```

若 `state.json` 存在且未设置 `--resume`：

```
AskUserQuestion(
  "发现中断的会话（波次 <N>，HAR：<har>）。\n"
  "请选择处理方式：\n"
  "A) 从波次 <N> 继续\n"
  "B) 重新开始\n"
  "C) 仅查看会话摘要"
)
```

处理完各选项后再继续。

**5. HAR 校验**

```bash
python3 -c "
import json, sys
data = json.load(open('${har_path}'))
assert 'log' in data and 'entries' in data['log'], '无效的 HAR 文件'
print(f'entries: {len(data[\"log\"][\"entries\"])}')
"
```

若校验失败，打印明确的错误信息并终止。

**6. HAR 认证头扫描**

```bash
python3 -c "
import json, collections
data = json.load(open('${har_path}'))
auth_stats = collections.Counter()
for entry in data['log']['entries']:
    headers = {h['name'].lower(): h['value'] for h in entry['request']['headers']}
    if 'cookie' in headers:
        auth_stats['cookie'] += 1
    elif 'authorization' in headers:
        auth_type_value = headers['authorization'].split()[0] if headers['authorization'] else 'unknown'
        auth_stats[f'token({auth_type_value})'] += 1
    else:
        auth_stats['none'] += 1
for k, v in auth_stats.most_common():
    print(f'  {k}: {v} 条请求')
dominant = auth_stats.most_common(1)[0][0] if auth_stats else 'none'
print(f'推断认证方式: {dominant}')
"
```

将检测到的认证方式（cookie / token / none）记录为 `detected_auth_type`，供后续代码生成使用。

**7. 参数摘要**

打印已确认的输入信息：

```
HAR 文件：      <path>  （<N> 条记录）
认证方式：      <detected_auth_type>
测试目录：      <test_dir>
测试类型：      <test_types>
源码模式：      <完整 / 仅 HAR>
模式：          quick=<是/否>  resume=<是/否>
```

---

## 第一波次：解析与准备（并行）

```
[1/4] 解析与准备 ▶ 开始...
```

初始化会话状态文件：

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/state_manager.py init --har "${har_path}"
```

**并行**启动 Agent（单条消息，根据 `no_source_mode` 决定启动数量）：

```
Agent(
  name="har-parser",
  description="将 HAR 文件解析为结构化的请求/响应数据",
  model="haiku",
  prompt="
    读取 HAR 文件：${har_path}
    同时读取：${CLAUDE_SKILL_DIR}/../../prompts/har-parse-rules.md
    将所有条目解析写入 .autoflow/parsed.json：
      - method、url、status、请求头/请求体、响应体
      - 按服务分组（使用 repo-profiles.yaml 中的 url_prefixes 进行映射）
    写入 .autoflow/parsed.json 后退出。
  "
)
```

仅在 `no_source_mode = false` 时启动：

```
Agent(
  name="repo-syncer",
  description="同步源码仓库并构建代码索引",
  model="haiku",
  prompt="
    读取 repo-profiles.yaml。
    对列表中的每个仓库：
      - 运行：git -C <local_path> pull --ff-only
      - 收集：模块名、类名、路由装饰器
    写入 .autoflow/repo-status.json：
      { repo: string, branch: string, synced: bool, modules: string[] }
    完成后退出。
  "
)
```

等待所有 Agent 均完成。读取 `.autoflow/parsed.json`（及 `.autoflow/repo-status.json`，若有），验证输出正确后再继续。

**验证摘要**

```
[1/4] 解析与准备 — 验证摘要：
  - parsed.json 结构完整性：<通过/失败>
  - 解析条目数：<N> 条
  - 服务匹配数：<N> 个服务（<列出服务名>）
  - repo-status.json：<已生成/跳过（无源码模式）>
```

检查点：

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/state_manager.py advance_wave --wave 1
```

```
[1/4] 解析与准备 ✓ 完成 (<N> 条记录解析完毕，匹配 <M> 个服务)
```

---

## 第二波次：场景分析（顺序执行，交互式）

```
[2/4] 场景分析 ▶ 开始...
```

启动场景分析器（`--quick` 模式下跳过用户确认，但仍执行分析）：

若 `no_source_mode = true`，使用降级 prompt：

```
Agent(
  name="scenario-analyzer",
  description="仅基于 HAR 流量分析生成测试场景（无源码模式）",
  model="opus",
  prompt="
    读取：.autoflow/parsed.json
    读取：${CLAUDE_SKILL_DIR}/../../prompts/scenario-enrich.md
    读取：${CLAUDE_SKILL_DIR}/../../prompts/assertion-layers.md

    注意：当前为无源码模式，无法读取后端源码。
    - L1（状态码）和 L2（Schema）断言正常生成
    - L3-L5 断言标记为「低置信度」，在 scenarios.json 中设置 confidence: 'low'

    仅生成以下测试类型：<test_types>

    生成 .autoflow/scenarios.json：
    {
      services: [
        {
          name: string,
          repo: null,
          endpoints: [
            {
              method, path, source_file: null, source_fn: null,
              scenarios: [
                { id, name, type, priority, confidence, assertions: AssertionLevel[] }
              ]
            }
          ]
        }
      ],
      generation_plan: [
        { module: string, file: string, endpoint_ids: string[] }
      ]
    }

    AssertionLevel：L1=状态码, L2=Schema, L3=业务逻辑, L4=数据库, L5=副作用
  "
)
```

若 `no_source_mode = false`，使用完整 prompt：

```
Agent(
  name="scenario-analyzer",
  description="对照源码分析 HAR 流量，生成测试场景",
  model="opus",
  prompt="
    读取：.autoflow/parsed.json
    读取：repo-profiles.yaml（用于定位源码仓库）
    从 .repos/ 读取相关源码文件，理解业务逻辑。
    读取：${CLAUDE_SKILL_DIR}/../../prompts/scenario-enrich.md
    读取：${CLAUDE_SKILL_DIR}/../../prompts/assertion-layers.md

    仅生成以下测试类型：<test_types>

    若 industry_mode = true：
    同时读取：${CLAUDE_SKILL_DIR}/../../prompts/industry-assertions.md
    行业：<industry.domain>
    合规要求：<industry.compliance>
    行业特定策略：<solution.industry_specific>
    在生成场景时，为写入类接口追加行业特定场景类别。

    生成 .autoflow/scenarios.json：
    {
      services: [
        {
          name: string,
          repo: string,
          endpoints: [
            {
              method, path, source_file, source_fn,
              scenarios: [
                { id, name, type, priority, assertions: AssertionLevel[] }
              ]
            }
          ]
        }
      ],
      generation_plan: [
        { module: string, file: string, endpoint_ids: string[] }
      ]
    }

    AssertionLevel：L1=状态码, L2=Schema, L3=业务逻辑, L4=数据库, L5=副作用
  "
)
```

读取 `.autoflow/scenarios.json`。若设置了 `--quick`，直接跳到验证摘要和检查点。

否则展示确认清单：

```
AskUserQuestion(
  "=== 第二波次：场景分析完成 ===\n\n"
  "源码仓库：    <列表及分支名 / 无（仅 HAR 模式）>\n"
  "HAR 覆盖率：  <N> 个服务，<M> 个接口\n\n"
  "AI 推断场景：\n"
  "  正常路径：  <N> 个\n"
  "  异常用例：  <N> 个\n"
  "  边界用例：  <N> 个\n\n"
  "AI 补充场景（增删改查 / 边界值）：\n"
  "  新增：      <N> 个\n\n"
  "断言层级：\n"
  "  L1（状态码）：  所有接口\n"
  "  L2（Schema）：  <N> 个接口\n"
  "  L3（业务逻辑）：<N> 个接口 <若无源码：（低置信度）>\n"
  "  L4（数据库）：  <N> 个接口（需配置数据库）<若无源码：（低置信度）>\n"
  "  L5（副作用）：  <N> 个接口 <若无源码：（低置信度）>\n\n"
  "测试类型过滤：<test_types>\n\n"
  "输出文件：\n"
  "  <generation_plan 中的文件列表>\n\n"
  "确认并继续？（yes / modify / cancel）"
)
```

若用户需要修改：询问具体变更内容，更新 `scenarios.json`，
并重新展示确认清单。

**验证摘要**

```
[2/4] 场景分析 — 验证摘要：
  - scenarios.json schema 校验：<通过/失败>
  - generation_plan 中所有 endpoint_ids 非空：<通过/失败>
  - 场景总数：<N> 个（正常 <X> / 异常 <Y> / 边界 <Z>）
  - 测试类型过滤：<test_types>
```

检查点：

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/state_manager.py advance_wave --wave 2
```

```
[2/4] 场景分析 ✓ 完成 (<N> 个场景，覆盖 <M> 个接口)
```

---

## 第三波次：代码生成（并行扇出）

```
[3/4] 代码生成 ▶ 开始...
```

读取 `.autoflow/scenarios.json` → `generation_plan` 数组。
根据 `test_types` 配置过滤，仅生成用户选择的测试类型对应的模块。

对计划中的每个模块，并行启动一个 Agent：

```
Agent(
  name="case-writer",
  description="为分配的接口生成 pytest 测试模块",
  model="sonnet",
  prompt="
    你负责的模块：<module_name>
    分配的接口：<endpoint_ids>

    读取：
      - .autoflow/scenarios.json  （获取场景详情）
      - .autoflow/parsed.json     （获取真实的请求/响应示例）
      - ${CLAUDE_SKILL_DIR}/../../prompts/code-style-python.md
      - ${CLAUDE_SKILL_DIR}/../../prompts/assertion-layers.md
      - scenarios.json 中各接口对应的源码文件（若有）

    认证方式：<detected_auth_type>

    写入：<test_dir>/<module_name>.py
      - 每个场景对应一个测试函数
      - 基于 Fixture 的认证与客户端初始化（使用检测到的认证方式）
      - 按 scenarios.json 中指定的层级编写断言
      - 低置信度断言添加 @pytest.mark.low_confidence 标记

    若 industry_mode = true：
    同时读取：${CLAUDE_SKILL_DIR}/../../prompts/industry-assertions.md
    行业：<industry.domain>
    在生成测试代码时，在标准 L1-L5 断言之后追加行业特定断言。
    行业断言标注格式：# Industry[<行业>]: <说明>

      - 添加类型注解和文档字符串，不硬编码凭证
  "
)
```

所有代码生成器并行运行（单条消息，每个模块一次 Agent 调用）。
等待全部完成。

**验证摘要**

对每个生成的测试文件执行验证：

```bash
# 语法检查
python3 -m py_compile <test_dir>/<module_name>.py

# import 可用性检查
python3 -c "import ast; ast.parse(open('<test_dir>/<module_name>.py').read()); print('AST OK')"
```

```
[3/4] 代码生成 — 验证摘要：
  - 生成文件数：<N> 个
  - py_compile 通过：<N>/<总数>
  - import/AST 检查通过：<N>/<总数>
  - 失败文件：<列表，若有>
```

若存在 py_compile 失败的文件，尝试自动修复后重新验证。

检查点：

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/state_manager.py advance_wave --wave 3
```

```
[3/4] 代码生成 ✓ 完成 (<N> 个文件，<M> 个测试函数)
```

---

## 第四波次：评审 + 执行 + 交付（顺序执行，交互式）

```
[4/4] 评审与交付 ▶ 开始...
```

**评审**

```
Agent(
  name="case-reviewer",
  description="评审所有生成的测试文件，检查质量与正确性",
  model="opus",
  prompt="
    读取所有匹配 <test_dir>/test_*.py 的文件
    读取：${CLAUDE_SKILL_DIR}/../../prompts/review-checklist.md
    读取：${CLAUDE_SKILL_DIR}/../../prompts/assertion-layers.md

    生成 .autoflow/review-report.json：
    {
      files_reviewed: number,
      issues: [{ file, line, severity, message, suggestion }],
      assertion_coverage: { L1: %, L2: %, L3: %, L4: %, L5: % },
      auto_fixes: [{ file, description }]
    }

    将可自动修复的问题直接应用到测试文件中。
  "
)
```

**执行**

检测项目包管理器并执行测试：

```bash
# 检测包管理器
if command -v uv &>/dev/null && test -f pyproject.toml; then
  RUNNER="uv run pytest"
elif command -v poetry &>/dev/null && test -f poetry.lock; then
  RUNNER="poetry run pytest"
else
  RUNNER="python3 -m pytest"
fi

# 收集本次生成的文件路径
GENERATED_FILES="<从 generation_plan 动态获取的文件路径列表>"

$RUNNER $GENERATED_FILES --alluredir=.autoflow/allure-results -v --tb=short -q \
  | tee .autoflow/execution-output.txt
```

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/test_runner.py --output .autoflow/execution-report.json
```

**验收报告**

读取 `.autoflow/review-report.json` 和 `.autoflow/execution-report.json`。

```
AskUserQuestion(
  "=== 第四波次：验收报告 ===\n\n"
  "生成结果：\n"
  "  测试文件：    <N> 个\n"
  "  测试函数：    <N> 个\n"
  "  评审问题：    <critical> 个严重，<high> 个高危，<low> 个低危\n\n"
  "断言覆盖率：\n"
  "  L1（状态码）：         <N>%\n"
  "  L2（Schema）：         <N>%\n"
  "  L3（业务逻辑）：       <N>%\n"
  "  L4（数据库）：         <N>%\n"
  "  L5（副作用）：         <N>%\n\n"
  "执行结果：\n"
  "  通过：<N>  失败：<N>  跳过：<N>\n\n"
  "已执行的验证步骤：\n"
  "  [x] 波次 1：parsed.json 结构完整性、条目数、服务匹配数\n"
  "  [x] 波次 2：scenarios.json schema 校验、endpoint_ids 非空检查\n"
  "  [x] 波次 3：所有生成文件 py_compile 和 AST 检查\n"
  "  [x] 波次 4：代码评审、测试执行、覆盖率统计\n\n"
  "生成文件：\n"
  "  <test_dir 下的文件列表>\n\n"
  "验收命令：\n"
  "  # 预检（仅收集，不执行）\n"
  "  <RUNNER> <生成的文件路径列表> --collect-only\n\n"
  "  # 执行本次生成的测试\n"
  "  <RUNNER> <生成的文件路径列表> -v --alluredir=.autoflow/allure-results\n\n"
  "  # 查看 Allure 报告\n"
  "  allure serve .autoflow/allure-results\n\n"
  "确认并归档？（yes / review-failures / cancel）"
)
```

**通知与归档**

若 `.env` 中配置了 Webhook：

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/notifier.py \
  --report .autoflow/execution-report.json \
  --review .autoflow/review-report.json
```

归档本次会话：

```bash
python3 ${CLAUDE_SKILL_DIR}/../../scripts/state_manager.py archive
```

```
[4/4] 评审与交付 ✓ 完成 (<N> 个测试通过，<M> 个失败)
```

打印最终摘要：

```
AutoFlow 完成
─────────────────────────────────────────────
已生成测试：  <N> 个函数，分布在 <M> 个文件中
通过：        <N>  失败：<N>  跳过：<N>
会话已归档：  .autoflow/archive/<timestamp>/
─────────────────────────────────────────────

验收命令：
  # 预检（仅收集，不执行）
  <RUNNER> <生成的文件路径列表> --collect-only

  # 执行本次生成的测试
  <RUNNER> <生成的文件路径列表> -v --alluredir=.autoflow/allure-results

  # 查看 Allure 报告
  allure serve .autoflow/allure-results
```
