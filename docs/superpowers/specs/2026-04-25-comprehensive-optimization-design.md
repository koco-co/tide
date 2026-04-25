# Tide 全面优化设计

## 概述

对本项目进行 4 个子项目的全面优化：SKILL 架构按需加载重构、基础设施接入、代码质量修复、用户体验增强。

## 子项目 A：SKILL 架构重构（按需加载）

### 目标

将 `skills/tide/SKILL.md`（682 行）和 `skills/using-tide/SKILL.md`（866 行）瘦身为纯编排骨架，所有细节外移到 `agents/*.md` 和 `scripts/*.py`。

### 原则

- SKILL.md 只描述"什么阶段做什么"，不描述"怎么做"
- `agents/*.md` 是 agent prompt 的唯一权威来源，消除内联重复
- 内联 `python3 -c "..."` 抽取到 `scripts/*.py` 作为 CLI 子命令
- 条件分支（`no_source_mode` / `industry_mode`）由 SKILL 在 spawn Agent 时以额外 context 注入，而非在 prompt 中硬编码两个版本

### 具体变更

#### 1. SKILL.md 新结构

只保留三部分：
- **任务初始化** — TaskCreate（流程可视化）
- **阶段元信息** — 每个 Wave 的目标、输入/输出文件、成功标准（1-2 句）
- **编排指令** — "启动 scenario-analyzer Agent，prompt 见 agents/scenario-analyzer.md，注入上下文 X/Y/Z"

#### 2. Agent Prompt 去重

agents/*.md 已有完整文件，SKILL.md 中移除所有内联重复。读取方式：
1. Claude Read agents/xxx.md 获取完整 prompt
2. Claude 追加运行时上下文变量（no_source_mode、test_types 等）
3. Claude spawn Agent(prompt=combined)

涉及文件：
- `agents/har-parser.md` — 保持
- `agents/scenario-analyzer.md` — 统一全量/降级两种模式为参数化形式
- `agents/case-writer.md` — 保持
- `agents/case-reviewer.md` — 保持
- `agents/repo-syncer.md` — 保持
- `agents/project-scanner.md` — 保持（仅 using-tide）
- `agents/industry-researcher.md` — 保持（仅 using-tide）

#### 3. 内联 Python 抽取

| 内联代码位置 | 归属 | 操作 |
|---|---|---|
| 预检：HAR 校验 | `scripts/har_parser.py` 新增 `validate_har()` | 新增 |
| 预检：认证头扫描 | `scripts/har_parser.py` 新增 `scan_auth_headers()` | 新增 |
| 预检：包管理器检测 | `scripts/test_runner.py` 新增 `detect_runner()` | 新增 |
| Wave 3: py_compile + AST | 已有 `format_checker.py` → `check_file()` | 已存在 |
| Wave 4: 测试执行 | 已有 `test_runner.py` → `run_tests()` | 已存在 |

#### 4. Hook + 偏好学习接入点

SKILL.md 增加 3 个条件接入位置：
- Wave 边界 → "若配置了 hooks，执行对应 hook"
- Wave 3 后 → "若偏好文件存在，写入本次运行数据"
- 启动时 → "若偏好文件存在，加载作为上下文"

## 子项目 B：基础设施接入

### B1 Hook 系统真实挂载

`hooks.py` 新增 CLI 入口：

```bash
python3 scripts/hooks.py run wave1:parse:before --project-root .
```

SKILL.md 在 9 个位置插入带 `if` 条件的 hook 调用。
`load_hooks_from_config` 的多次 `import sys` 提取到文件顶部。

### B2 偏好学习接入

- Wave 1 完成时：写入 parsed entries 数量、认证类型
- Wave 3 完成时：写入生成的模块数量
- 下次 `/tide` 启动时：读取偏好作为上下文传递给 Agent
- 新增 CLI 入口：`python3 scripts/preferences.py read|write --key ... --value ...`

### B3 格式检查器补全

| 规则 | 检查逻辑 | 实现方式 |
|---|---|---|
| FC03 未使用的 import | 收集所有 import 名，与 AST Name 引用交叉比对 | `ast.walk` 收集 Name/Attribute 节点，排除 __future__ |
| FC04 硬编码测试数据 | 检测断言或 fixture 中的字面量URL(/api/)、长数字ID(>5位) | `ast.walk` 找 Constant 中的 str/int 模式匹配 |
| FC05 断言消息描述性 | 检查 assert 语句是否带描述参数 | `ast.walk` 找 Assert 节点，检查 msg 存在 |
| FC06 Pydantic description | 检查 Field(description=...) 调用中的关键字参数 | `ast.walk` 找 Call → func 是 `Field` |
| FC10 嵌套深度 ≤ 3 | 对 if/for/while/try/with/async for 节点计算嵌套层数 | `ast.walk` 深度统计，报超过 3 层的节点 |

## 子项目 C：代码质量修复

### C1 版本号统一

- `pyproject.toml` → `1.3.0`
- `.claude-plugin/plugin.json` → `1.3.0`
- `README.md` 头图 badge → v1.3
- README Roadmap 合并"v1.2（当前）"和"v1.3（当前）"为 "v1.3（当前）"
- `Makefile` release 命令以 pyproject.toml 为单一来源

### C2 代码质量修复明细

| 位置 | 问题 | 修复 |
|---|---|---|
| `har_parser.py:258` | `match_repo` 参数 `list[dict]` | 改为 `list[RepoProfile]` |
| `har_parser.py:276` | `_extract_service_module` 索引硬编码 | 加路径深度后移回退逻辑 |
| `test_runner.py:31` | `python` → 可能不存在 | 改用 `sys.executable` |
| `notifier.py:103` | `dict[str, object]` 类型不精确 | 改为 `dict[str, Callable]` |
| `scaffold.py:194-203,286-293` | tide-config 渲染重复 | 抽取 `_render_tide_config()` |
| `hooks.py` | 多处重复 `import sys` | 提取到文件顶部 |

### C3 补充集成测试

新增文件：
- `tests/test_integration_har_to_state.py` — HAR → ParsedResult → state 写入 → resume → archive 完整链路
- `tests/test_integration_flow.py` — 模拟 Wave 1-4 编排（mock agent spawn）

### C4 错误路径 UX 改进

- `repo-profiles.yaml` 缺失时输出带修复命令的错误信息
- Agent 调用失败时提供重试/跳过/终止 3 选项（AskUserQuestion）
- `--resume` 模式增加 `--wave N` 参数支持指定波次恢复

### C5 隐私风险提示

预检阶段新增加提示框（AskUserQuestion 确认）：

```
[HAR 内容隐私提示]
HAR 文件中的 URL、请求/响应数据将发送给 AI 模型进行分析。
敏感头（Cookie/Authorization）已在解析时自动剥离。
如包含业务敏感数据（用户 PII、密钥等），建议脱敏后再使用。
确认继续？
```

## 子项目 D：用户体验优化

### D1 预检时间预估

在参数摘要后新增一段：

```
预计耗时：约 3-5 分钟
  Wave 1 (解析): ~30s
  Wave 2 (场景分析): ~1-2min
  Wave 3 (代码生成 ×N): ~1-2min
  Wave 4 (评审): ~1min
```

计算公式：`entries × 系数`，系数基于历史运行数据（偏好学习）。

### D2 执行顺序

```
子项目 A（SKILL 重构）—— 必须先做，子项目 B 依赖此
     │
     ├── 子项目 B（基础设施接入）—— 依赖 A 完成后才有干净接入点
     │
     ├── 子项目 C（代码质量修复）—— 可与 A 并行
     │
     └── 子项目 D（UX 优化）—— 依赖 A，可在 B 之后
```

## 文件变更总清单

```
修改:
  pyproject.toml                       (版本号 1.3.0)
  .claude-plugin/plugin.json           (版本号 1.3.0)
  README.md                            (版本号 + Roadmap 合并)
  Makefile                             (release 命令改进)
  skills/tide/SKILL.md             (重写为极简编排)
  skills/using-tide/SKILL.md       (重写为极简编排)
  agents/scenario-analyzer.md          (参数化，统一全量/降级)
  scripts/har_parser.py                (新增 validate_har / scan_auth_headers / match_repo 类型修复 / _extract_service_module 修复)
  scripts/test_runner.py               (新增 detect_runner / python→sys.executable)
  scripts/hooks.py                     (新增 CLI run 子命令 / import 提顶)
  scripts/preferences.py               (新增 CLI read/write 子命令)
  scripts/format_checker.py            (补全 FC03-FC06/FC10)
  scripts/notifier.py                  (FORMATTERS 类型修复)
  scripts/scaffold.py                  (抽取 _render_tide_config)
  scripts/state_manager.py             (archive 异常处理)
  tests/test_format_checker.py         (新增 FC03-FC06/FC10 测试)
  tests/test_integration_har_to_state.py (新增)
  tests/test_integration_flow.py       (新增)

无新增脚本文件，全部在现有文件上增强。
```
