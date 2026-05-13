---
name: tide
description: "从 HAR 文件生成 pytest 测试套件，结合源码进行 AI 智能分析。触发方式：/tide <har-path>、/tide:tide <har-path>、'从 HAR 生成测试'、提供 .har 文件路径。"
argument-hint: "<har-file-path> [--quick] [--yes] [--non-interactive] [--resume] [--wave N]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, TaskCreate, TaskUpdate, TaskList
---

# Tide：HAR 转 Pytest 测试生成

> **重要：除非必要，否则不要改动已有项目中的测试配置或脚本。如需修改，先用 AskUserQuestion 向用户报告改动原因和改动范围，确认后方可执行。**
> **HAR 选择不得猜测**：当用户只说 "HAR 在 .tide/trash 下"、"使用 trash 里的 HAR" 或传入目录路径时，不得自行按 mtime、文件大小、名称相似度或模型推断挑选某一个 `.har` 文件。必须先运行 `scripts.har_inputs.resolve_har_input`；如果有多个候选文件，交互模式列出候选并询问用户选择，无头/非交互模式直接失败并给出精确命令示例。
> **Claude Code 插件命令名**：在插件 CLI/非交互上下文中，可靠入口是 `/tide:tide <har-file> --yes --non-interactive`；若 `/tide` 返回 Unknown command，必须改用 `/tide:tide`，不得自由生成测试。

## 第零步：自更新

在开始之前检查 Tide 插件是否有更新。

```bash
# 检查并自动更新插件（无网络时静默跳过）
bash "${CLAUDE_SKILL_DIR}/../../scripts/self-update.sh"
```

## 任务初始化

在流程开始时创建 6 个任务：
- 预检与参数校验
- [1/4] 解析与准备
- [2/4] 场景分析
- [3/4] 代码生成
- [4/4] 评审与交付
- 验收报告与归档

格式同现有 TaskCreate，ID 依次记为 `<task_1_id>` 到 `<task_6_id>`。

---

## 预检阶段

1. 标记 task 1 为 in_progress
2. 设置 `PLUGIN_DIR="${CLAUDE_SKILL_DIR}/../.."`
3. **Python 解释器自动检测与职责分离**：
   ```bash
   # PYTHON_BIN 只用于运行目标项目 pytest（项目 .venv 可能是 pydantic v1 / Python 3.8）
   if [ -f "$(pwd -P)/.venv/bin/python3" ]; then
       export PYTHON_BIN="$(pwd -P)/.venv/bin/python3"
   elif [ -f "$(pwd -P)/venv/bin/python3" ]; then
       export PYTHON_BIN="$(pwd -P)/venv/bin/python3"
   else
       export PYTHON_BIN="python3"
   fi
   echo "Using Python: $($PYTHON_BIN --version 2>&1) at $PYTHON_BIN"
   ```
   Tide 自身脚本不得使用项目 .venv；所有 `scripts.*` 必须用插件环境运行：
   ```bash
   export TIDE_PY='(cd "$PLUGIN_DIR" && PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3'
   tide_py() {
     (cd "$PLUGIN_DIR" && PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 "$@")
   }
   ```
4. **固定运行边界**：

   ```bash
   export PROJECT_ROOT="$(pwd -P)"
   export PLUGIN_DIR="$(cd "${CLAUDE_SKILL_DIR}/../.." && pwd -P)"
   mkdir -p "$PROJECT_ROOT/.tide"
   tide_py - <<'PY' > "$PROJECT_ROOT/.tide/run-context.json"
   import json
   import os
   from pathlib import Path
   from scripts.run_context import resolve_run_context

   ctx = resolve_run_context(
       argument_text=os.environ.get("ARGUMENTS", ""),
       project_root=Path(os.environ["PROJECT_ROOT"]),
       plugin_dir=Path(os.environ["PLUGIN_DIR"]),
   )
   print(json.dumps({
       "project_root": str(ctx.project_root),
       "plugin_dir": str(ctx.plugin_dir),
       "tide_dir": str(ctx.tide_dir),
       "har_path": str(ctx.har_path),
       "requires_confirmation": ctx.args.requires_confirmation,
       "quick": ctx.args.quick,
       "yes": ctx.args.yes,
       "non_interactive": ctx.args.non_interactive,
       "resume": ctx.args.resume,
       "wave": ctx.args.wave,
   }, ensure_ascii=False, indent=2))
   PY
   ```

4a. **repo profile 配置选择**：
   ```bash
   if [ -f "$PROJECT_ROOT/.tide/repo-profiles.yaml" ]; then
       export REPO_PROFILES="$PROJECT_ROOT/.tide/repo-profiles.yaml"
   elif [ -f "$PROJECT_ROOT/repo-profiles.yaml" ]; then
       export REPO_PROFILES="$PROJECT_ROOT/repo-profiles.yaml"
   elif [ -f "$PROJECT_ROOT/tide-config.yaml" ]; then
       export REPO_PROFILES="$PROJECT_ROOT/tide-config.yaml"
   else
       export REPO_PROFILES=""
   fi
   ```
   `tide-config.yaml` 支持 `repos.profiles` schema；不得把 `$PROJECT_ROOT/.tide/repos` 目录当作 profiles 文件传入。

4b. **运行环境边界**：
   - HAR base_url 只作为来源元数据，用于说明录制来源。
   - 不得把 HAR base_url 写入生成测试，不得用 HAR base_url 覆盖项目运行环境。
   - 生成测试和最终 pytest 必须使用项目已有配置的 active environment（例如 `tide-config.yaml` 的 `environments.active`、项目 env 文件、fixture、runner）。

4c. **INTERACTIVE HARD GATE**：
   - 若 `.tide/run-context.json` 中 `requires_confirmation=true`，优先用 AskUserQuestion 等用户确认，确认前不得进入下一阶段。
   - 隐私/成本摘要后至少记录 `continue_after_precheck`。
   - `.tide/parsed.json` 解析完成并展示端点/环境摘要后必须询问，确认后记录 `continue_after_parse`。
   - `.tide/scenarios.json` 与 `.tide/generation-plan.json` 生成并展示写入计划后必须询问，确认后记录 `continue_after_scenarios`。
   - 涉及真实环境的最终 pytest，如用户未显式要求自动执行，也必须在交互模式下确认。
   - **Codex exec 模式降级**：若 AskUserQuestion / request_user_input 不可用（返回 error 或 tool 不存在），自动降级到无头策略。

5. **无头执行策略**：
   - 若 `.tide/run-context.json` 中 `requires_confirmation=false`，不得调用 AskUserQuestion。
   - 所有"是否继续 / 是否进入下一阶段 / 是否确认场景"的问题默认选择继续。
   - 将默认决策写入 `.tide/state.json` 的 metadata，例如 `{"headless_decisions":["continue_after_precheck","continue_after_parse","continue_after_scenarios"]}`。
   - 若 `requires_confirmation=true`，优先尝试 AskUserQuestion。如果调用失败（tool 不存在、返回错误、或在 exec 模式中），**自动降级为无头模式**：
     - 所有交互点默认选择继续
     - 测试粒度默认 `hybrid`（混合模式）
     - 业务场景根据 HAR 文件名自动推断
     - 所有决策写入 `.tide/state.json` 的 `headless_fallback` 字段
     - 继续下一阶段，不中断流程
   - 降级后不得再次尝试 AskUserQuestion。

6. 解析 `$ARGUMENTS`：`har_path`（必填）、`--quick`、`--yes`、`--non-interactive`、`--resume`、`--wave N`
6a. **HAR 路径确定性解析（禁止猜测）**：
   ```bash
   export HAR_PATH="$(tide_py - <<'PY'
   import json
   import os
   from pathlib import Path
   from scripts.har_inputs import resolve_har_input

   run_context = Path(os.environ["PROJECT_ROOT"]) / ".tide" / "run-context.json"
   ctx = json.loads(run_context.read_text())
   print(resolve_har_input(ctx["har_path"], Path(os.environ["PROJECT_ROOT"])))
   PY
   )"
   echo "Resolved HAR: $HAR_PATH"
   ```
   - 若命令报 `Multiple HAR files found; Do not guess`：
     - 交互模式：用 AskUserQuestion 列出候选 `.har` 文件，请用户选择精确路径后重新解析。
     - 无头/非交互模式：立即终止，输出候选清单和示例：`/tide .tide/trash/<exact-file>.har --yes --non-interactive`。
   - 不得在多个候选中自动选择"最新"、"最大"或"看起来最相关"的 HAR。
7. **环境检查**：检查 `$REPO_PROFILES`；若为空则进入无源码模式，不得因缺少 `repo-profiles.yaml` 直接终止。
8. **读取配置**：读取 `$REPO_PROFILES` 和 `tide-config.yaml`，提取 repos、test_dir、test_types、industry、active environment 等。
9. **无源码降级**：repos 为空时设置 `no_source_mode=true`
10. **惯例指纹加载 + 按需 Prompt 组装**：
   test -f .tide/convention-fingerprint.yaml && echo "FINGERPRINT_EXISTS" || echo "NO_FINGERPRINT"
   若 fingerprint 存在：
   - 读取 .tide/convention-fingerprint.yaml
   - 将 fingerprint 内容注入后续 wave 的 case-writer prompt 的"项目规范"约束段
   - 设置 fingerprint_mode=true
   若不存在：
   - 设置 fingerprint_mode=false，使用通用默认模板

   按需 Prompt 组装（fingerprint_mode=true 时）：
   根据 convention-fingerprint.yaml 的内容，从 prompts/code-style-python/ 中选择要加载的模块：
   - 始终加载：00-core.md
   - 若 api.type == "enum" → +10-api-enum.md
   - 若 api.type == "class" → +10-api-class.md
   - 若 api.type 为 inline 或不存在 → +10-api-inline.md
   - 若 http_client.client_pattern == "custom_class" → +20-client-custom.md
   - 若 http_client.library == "httpx" → +20-client-httpx.md
   - 若 http_client.library == "requests" → +20-client-requests.md
   - 若 assertion.has_code_success == true → +30-assert-code-success.md
   - 若 assertion.style 为 status_only 或不存在 → +30-assert-status-only.md
   - 若 test_style.file_suffix == "*_test.py" → +40-test-structure-dtstack.md
   - 以上都不匹配 → +40-test-structure-standard.md
   读取 selected 模块内容作为"项目规范"约束注入 Agent 上下文。
   设置 prompt_loaded_modules=[模块名列表] 供调试。
11. **恢复检查**：若 `state.json` 存在且未设置 `--resume`，询问继续/重来/查看摘要
12. **HAR 校验 + 认证头扫描 + 隐私提示**：
   HAR 校验：`tide_py -c "from scripts.har_parser import validate_har; from pathlib import Path; r = validate_har(Path('${HAR_PATH}')); print(r)"`
   认证头扫描：`tide_py -c "from scripts.har_parser import scan_auth_headers; from pathlib import Path; print(scan_auth_headers(Path('${HAR_PATH}')))"`
   隐私提示：输出 HAR 数据发送至 AI 模型的提示，请用户确认后继续
13. **参数摘要**：打印 HAR 路径/记录数/认证方式/测试目录/源码模式/模式/active environment

14. **成本预估**（fingerprint_mode=true 时展示）：
    端点数：har-parser 输出中 endpoint 的数量
    复杂度分级：
    - 端点数 ≤ 10 → 复杂度"低"，系数 3000
    - 端点数 11-30 → 复杂度"中"，系数 8000
    - 端点数 > 30 → 复杂度"高"，系数 15000
    公式：预估 tokens = 端点数 × 系数 × 2（wave2+wave4 共用 opus）
    展示格式：
    ```
    ╔══════════════════════════════════════╗
    ║ Tide 成本预估                        ║
    ║──────────────────────────────────────║
    ║ 端点数: <N>                          ║
    ║ 场景复杂度: <低/中/高>                 ║
    ║ 预估 tokens: ~<X>                    ║
    ║ 预估成本: ~$<Y>                      ║
    ╚══════════════════════════════════════╝
    ```
    询问用户是否继续。用户拒绝则终止流程。接受则继续。

15. **用户意图采集**（新增）：
    在进入 Wave 1 之前，用 AskUserQuestion 询问以下问题，明确用户期望的测试粒度：

    ```
    请选择测试粒度：
    
    A. 单接口回放 — 每个 HAR 端点对应一个独立测试，验证 HTTP 状态码和基本响应
    B. CRUD 闭环 — 按资源维度组织增删改查生命周期测试
    C. 端到端链路 — 按业务场景串联多个接口（如：建表→同步→查询→清理），含 setup/teardown
    D. 混合模式 — 核心链路做端到端，其余做单接口回放
    ```

    同时询问用户业务场景描述（可选）：
    ```
    这批 HAR 对应的业务场景是什么？（例如："资产模块的元数据同步全链路测试"）
    这有助于 AI 理解接口之间的业务关联，生成更有意义的测试。
    ```

    根据回答设置 `test_granularity`（single_api / crud / e2e_chain / hybrid）和 `business_context` 变量，用于后续 wave。

    > 若未选择，默认 hybrid 模式：检测到同一 module 中有 POST 请求依赖关系则做 e2e，其余单接口。

16. Task 1 完成。

---

## 第一波次：解析与准备（并行）

Task 2 → in_progress

1. `tide_py -m scripts.state_manager init --har "$HAR_PATH"`
2. **确定性脚本优先**：
   - HAR 快照：
     `tide_py -m scripts.har_inputs "$HAR_PATH" --project-root "$PROJECT_ROOT"` 若 CLI 尚未实现，则用 Python snippet 调用 `snapshot_har`。
   - HAR 解析：
     `tide_py -m scripts.har_parser "$HAR_SNAPSHOT" --profiles "$REPO_PROFILES" --output "$PROJECT_ROOT/.tide/parsed.json"`
   - repo 同步：
     若 `$REPO_PROFILES` 非空，执行 `tide_py -m scripts.repo_sync --root "$PROJECT_ROOT" --profiles "$REPO_PROFILES" sync`；若为空，写入 no_source 状态并跳过同步。
   - project-asset-scanner 仍可作为 Agent（如可用），但它只能写 `$PROJECT_ROOT/.tide/project-assets.json`。
   - **确定性回退**：若 Agent 未产生 `project-assets.json`（如无头/print 模式），立即执行确定性扫描：
     ```bash
     tide_py - <<'PY'
     import os, json, importlib.util, inspect
     from pathlib import Path
     root = Path(os.environ["PROJECT_ROOT"])
     utils_dir = root / "utils"
     if utils_dir.exists():
         modules = {"modules": {}}
         for svc_dir in sorted(utils_dir.rglob("*")):
             if svc_dir.is_dir() and (svc_dir / "__init__.py").exists():
                 rel = svc_dir.relative_to(root)
                 for py_file in sorted(svc_dir.glob("*.py")):
                     if py_file.name == "__init__.py":
                         continue
                     try:
                         mod_name = str(py_file.relative_to(root)).replace("/", ".").replace(".py", "")
                         spec = importlib.util.spec_from_file_location(mod_name, py_file)
                         if spec and spec.loader:
                             mod = importlib.util.module_from_spec(spec)
                             spec.loader.exec_module(mod)
                             for name, cls in inspect.getmembers(mod, inspect.isclass):
                                 if hasattr(cls, "__module__") and cls.__module__ == mod_name:
                                     methods = [m for m in dir(cls) if not m.startswith("_") and callable(getattr(cls, m))]
                                     modules["modules"].setdefault(str(svc_dir.relative_to(root)), {"services": []})
                                     modules["modules"][str(svc_dir.relative_to(root))]["services"].append({
                                         "class": name, "module": mod_name, "file": str(py_file.relative_to(root)),
                                         "methods": [{"name": m} for m in methods[:20]]
                                     })
                     except Exception:
                         pass
         with open(root / ".tide" / "project-assets.json", "w") as f:
             json.dump(modules, f, indent=2, ensure_ascii=False)
         print(f"project-assets.json generated ({len(modules.get('modules', {}))} modules)")
     else:
         print("No utils/ directory found, skipping project-assets generation")
     PY
     ```
3. 读取验证输出：
   - `.tide/parsed.json` — 解析后的端点列表
   - `.tide/repo-status.json` — 仓库同步状态
   - `.tide/project-assets.json`（新增）— 项目工具类资产清单
4. **向用户报告解析结果**：读取 .tide/parsed.json，按模块和方法归类端点，同时说明测试粒度设定。用 AskUserQuestion 展示以下信息，询问是否确认进入下一阶段：

   ```
   HAR 解析完成：
   - 原始请求数：42
   - 去重后端点数：18
   - 测试粒度：端到端链路 / 单接口回放

   测试场景分布：
   batch 模块
     场景 1：查询批量任务列表
       · GET /api/batch/list
       · GET /api/batch/search
     ...

   项目可复用资产（基于 convention-fingerprint）：
   - DatasourceService.get_datasource_id_by_name(name) — 按名称查数据源ID
   - DataMapService.get_asset_metadata_sync_result(schema, type) — 全链路同步结果
   - MetaDataRequest.page_table_column(tableId) — 查表字段
   代码生成时将优先使用这些已有封装而非从零实现。

   仓库同步状态：
   - dt-insight-web/dt-center-assets ✓（main@2a3b4c5）

   是否进入场景分析阶段？
   ```

5. 输出验证摘要，检查点保存

**[Hook]** 若 tide-config.yaml 中有 hook 配置，执行 `tide_py -m scripts.hooks run wave1:parse:after`

Task 2 完成。

---

## 第二波次：场景分析

Task 3 → in_progress

1. 读取 `agents/scenario-analyzer.md`，传入上下文：
   - `no_source_mode` — 是否无源码模式
   - `test_types` — 配置中指定的测试类型
   - `industry_mode` — 是否启用行业规则
   - **`test_granularity`**（新增）— 用户选择的测试粒度
   - **`business_context`**（新增）— 用户描述的业务场景
   - **`async_mode`**（新增）— 自动检测：若端点中有异步接口（返回 taskId 后轮询），标记为 async
2. 启动 scenario-analyzer Agent（opus）
3. 读取 .tide/scenarios.json

   读取 `.tide/scenarios.json` 与 `.tide/generation-plan.json` 后，必须执行：

   ```bash
   tide_py -m scripts.scenario_normalizer \
     --parsed "$PROJECT_ROOT/.tide/parsed.json" \
     --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
     --generation-plan "$PROJECT_ROOT/.tide/generation-plan.json"

   tide_py -m scripts.scenario_validator \
     --parsed "$PROJECT_ROOT/.tide/parsed.json" \
     --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
     --generation-plan "$PROJECT_ROOT/.tide/generation-plan.json"
   ```

   若 normalizer 仍无法消除重复 `scenario_id` 或补齐 generation-plan 引用，返回 scenario-analyzer 修复一次；第二次仍失败则停止并写入 `.tide/final-report.md`。
   **不得跳过此校验**：缺失 `.tide/scenarios.json`、重复 `scenario_id`、或 `confidence>=medium` 比例低于 60% 都是阻断错误，不能继续生成代码。
4. 若非 `--quick`，展示确认清单供用户确认

**[Hook]** 若配置了 hook，执行 `tide_py -m scripts.hooks run wave2:analyze:after`

检查点保存，Task 3 完成。

---

## 第三波次：代码生成（并行扇出）

Task 4 → in_progress

1. 读取 `.tide/scenarios.json` → `generation_plan`
2. 读取 `.tide/project-assets.json`（若存在）— 项目已有工具类清单
3. 在任何 case-writer 写文件之前创建目标写范围快照：
   ```bash
   tide_py -m scripts.write_scope_guard snapshot \
     --project-root "$PROJECT_ROOT" \
     --snapshot "$PROJECT_ROOT/.tide/write-scope-snapshot.json"
   ```
   只允许写 `.tide/` 和 `testcases/`。禁止新增或修改 `api/`、`dao/`、`utils/`、`config/`、`testdata/`、`resource/`。
4. 仅当用户确认需要 AI 精修时，才对每个模块并行启动一个 case-writer Agent，prompt 见 `agents/case-writer.md`，传入：
   - `detected_auth_type` — 认证方式
   - **`project_assets`**（新增）— 项目已有工具类方法清单，要求优先复用
   - **`test_granularity`**（新增）— 测试粒度
   - **`business_context`**（新增）— 业务场景描述
   - 按需加载的 code-style-python prompt 模块（来自 fingerprint 组装）
5. **确定性 fallback（必跑）**：
   在 case-writer 运行前或并行执行：
   ```bash
   tide_py -m scripts.deterministic_case_writer \
     --project-root "$PROJECT_ROOT" \
     --parsed "$PROJECT_ROOT/.tide/parsed.json" \
     --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
     --generation-plan "$PROJECT_ROOT/.tide/generation-plan.json"
   ```
   fallback 只允许写 `testcases/` 和 `.tide/artifact-manifest.json`，不得改 `api/`、`dao/`、`utils/`、`config/`、`testdata/`、`resource/`。

5b. **确定性升级约束（新增）**：
   deterministic case writer 生成的测试**仅供骨架参考**，不得作为最终输出。无论 deterministic case writer 是否产出可 collect 的测试文件，都必须继续启动 `case-writer` Agent 对每个生成文件进行**实时 HTTP 化改造**：
   - 使用项目已有 HTTP client 类（`DataValidRequest`/`MetaDataRequest`等），进行方法与端点匹配
   - **如果没有匹配的 client 方法，直接使用 `AssetsBaseRequest` 或 `BaseRequests`（`self.req.post/post(url, json=payload)`），不得使用 mock 数据（`response = {'body': {...}}`）
   - 从 HAR 提取每个端点的真实请求体 payload
   - 保留 deterministic case writer 生成的断言结构和 L1-L5 注释，但替换 response 数据来源为真实 HTTP 调用
   - 禁止生成 `response = {'body': ...}` 或 `response = {'status_code': ...}` 形式的 mock 数据
   - 禁止使用 `CONTRACTS` 常量字典作为断言依据（实时测试必须从真实 API 响应中获取数据）
   - 完成改造后验证文件是否包含 `self.req`、`requests.`、`session.` 或 `httpx.`；如不包含，改造失败
6. 全部完成后立刻校验目标写范围：
   ```bash
   tide_py -m scripts.write_scope_guard verify \
     --project-root "$PROJECT_ROOT" \
     --snapshot "$PROJECT_ROOT/.tide/write-scope-snapshot.json"
   ```
   若失败，立即停止，报告 forbidden path；不得继续 pytest、不得输出成功总结。
7. 对每个生成文件执行 py_compile + AST 检查
8. **格式检查**（新增）：对所有生成文件执行 format_checker：
   ```bash
   tide_py -m scripts.format_checker <generation_plan 中所有 output_file 的父目录>
   ```
   - 对 FC04（硬编码 URL）的 WARNING 级别违规，自动提取并尝试修复
   - 对 FC11（硬编码业务 ID）的 ERROR 级别违规：自动将 `dataSourceId: 1` 等替换为 `self.ds_id` / `self.table_id` 变量引用，若无法修复则阻断流水线
   - 对 FC08（print 语句）的 ERROR 级别违规，自动移除
   - 记录问题到 `.tide/format-report.json`
9. **断言硬门检查**（新增）：对 `.tide/scenarios.json` 和所有生成测试执行 generated_assertion_gate：
   ```bash
   tide_py -m scripts.generated_assertion_gate \
     --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
     <生成的 pytest 文件列表>
   ```
   - 若输出 `empty L4`、`empty L5`、`missing L4` 或 `missing L5`，本轮质量门必须 FAIL。
   - 不得把 `pytest passed`、`format passed` 或空的 `db_verify: []` / `ui_verify: []` 当作 L4/L5 通过。
   - 将输出保存为 `.tide/assertion-gate-report.json` 或在 `.tide/final-report.md` 中逐项列出失败原因。

**[偏好]** 写入本次生成的模块数 `tide_py -m scripts.preferences write --key last_module_count --value <N>`

检查点保存，Task 4 完成。

---

## 第三波次结尾 — Live Execution Gate（硬阻断）

**在进入第四波次前必须执行此门禁，不得跳过。**

Task 4 完成后，在 Task 5 开始前，立即运行以下命令：

```bash
# --- Live Execution Gate ---
# 脚本检查所有 tide_generated_*.py 是否包含真实 HTTP 调用
# 如果 DETERMINISTIC，写入 .tide/skip-wave4.txt，阻断第四波次
tide_py -m scripts.live_gate check --project-root "$PROJECT_ROOT"

# 读取门禁结果
LIVE_GATE=$(cat "$PROJECT_ROOT/.tide/live-gate-result.json" | python3 -c "import sys,json; print(json.load(sys.stdin)['test_mode'])")
echo "LIVE GATE: $LIVE_GATE"
```

### LIVE 分支

`TEST_MODE=LIVE` → 允许进入第四波次。正常进行。

### DETERMINISTIC 分支

`TEST_MODE=DETERMINISTIC` → 门禁失败，**跳过第四波次**。

**立即执行确定性骨架升级**（必须按顺序执行以下命令）：

```bash
# 1. 查找项目已有 HTTP client
echo "=== 项目 HTTP Client 扫描 ==="
for client_py in utils/assets/requests/*.py; do
  if grep -q 'class.*Request' "$client_py" 2>/dev/null; then
    echo "Found: $client_py"
    head -80 "$client_py"
    break
  fi
done

# 2. 读取 auth 配置
echo "=== Auth 配置 ==="
grep -A5 'auth:' tide-config.yaml 2>/dev/null || true

# 3. 读取一个现有测试作为参考
echo "=== 参考测试文件 ==="
sample_test=$(find testcases/scenariotest/assets -name '*_test.py' -not -name 'tide_generated_*' 2>/dev/null | head -1)
if [ -n "$sample_test" ]; then head -80 "$sample_test"; fi
```

升级要求：
- 保留原始 mock 测试作为降级备份
- 为每个 mock 测试生成真实 HTTP 版本，使用项目已有 HTTP client
- 从 HAR 提取真实请求 payload
- 若没有匹配的 HTTP client 类，创建继承 `BaseRequests` 的最小 client

升级完成后**再次运行门禁**：

```bash
tide_py -m scripts.live_gate check --project-root "$PROJECT_ROOT"
```

**最终判定**：
- `TEST_MODE=LIVE` → 允许进入第四波次
- `TEST_MODE=DETERMINISTIC` → **跳过整个第四波次，直接进入验收报告阶段。最终报告状态写 `DETERMINISTIC_SKELETON`（不得写 PASS 或 Success），并说明升级失败原因**

---

## 第四波次：评审 + 执行 + 交付

**开始第四波次前必须检查门禁文件：**

```bash
if [ -f "$PROJECT_ROOT/.tide/skip-wave4.txt" ]; then
  echo "Live Execution Gate BLOCKED: tests are DETERMINISTIC (no real HTTP calls)"
  echo "Skipping entire Wave 4. Proceed directly to 验收报告与归档."
  exit 0
fi
```

**只有门禁通过 (LIVE) 才执行以下步骤。**

Task 5 → in_progress

1. 启动 case-reviewer Agent，prompt 见 `agents/case-reviewer.md`
   - case-reviewer 会依次完成：静态审查 → 自动修复 → 测试执行（`${PYTHON_BIN:-python3} -m pytest --collect-only -q` + `${PYTHON_BIN:-python3} -m pytest -x -v --tb=short`）→ **失败语义分析（新增）** → 最多 2 轮修复循环 → 输出 review-report.json 和 execution-report.json
   - **失败语义分析**：当测试失败时，解析 response body 的错误信息，判断失败根因类别：
     - `TEST_BUG` — 测试写错了（参数不对、断言值错）→ 自动修复
     - `ENV_ISSUE` — 环境问题（服务不可用、数据不存在）→ 标记为环境问题，调整预期
     - `BUSINESS_BUG` — 业务 bug（code≠1 但非参数问题）→ 标记为疑似缺陷
   - **等待 case-reviewer 全部完成再继续下一步**
2. case-reviewer 结束后再次校验目标写范围：
   ```bash
   tide_py -m scripts.write_scope_guard verify \
     --project-root "$PROJECT_ROOT" \
     --snapshot "$PROJECT_ROOT/.tide/write-scope-snapshot.json"
   ```
   若失败，立即停止，报告 forbidden path；不得继续 pytest、不得输出成功总结。

3. 用最终 pytest 输出重写 `.tide/execution-report.json`，确保报告与最后一次实际执行一致：

   ```bash
   set +e
   "${PYTHON_BIN:-python3}" -m pytest <生成文件列表> -q > "$PROJECT_ROOT/.tide/final-pytest-output.txt" 2>&1
   PYTEST_RC=$?
   set -e
   tide_py -m scripts.test_runner report \
     --report "$PROJECT_ROOT/.tide/execution-report.json" \
     --output-file "$PROJECT_ROOT/.tide/final-pytest-output.txt" \
     --return-code "$PYTEST_RC" \
     --total-tests <collect-only 收集到的生成测试数> \
     --command "${PYTHON_BIN:-python3}" -m pytest <生成文件列表> -q
   ```

   若 `.tide/execution-report.json` 中的 `passed/failed/errors/total_tests` 与最终 pytest 输出不一致，必须以此命令重写后的 JSON 为准。
4. 读取 `.tide/execution-report.json`，向用户报告执行结果：

   ```
   测试执行完成
   - 收集：成功
   - 通过：15/18
   - 失败：3
   - 失败归类：测试本身问题 1，环境问题 1，疑似缺陷 1
   - 修复轮数：1
   ```

5. 生成验收报告

**[Hook]** 执行 `tide_py -m scripts.hooks run wave4:review:after` 和 `tide_py -m scripts.hooks run output:notify`

Task 5 完成。

## 验收报告与归档

Task 6 → in_progress

1. 显示最终摘要（测试通过数/失败数/断言覆盖率/失败归类）
2. 打印验收命令（pytest collect-only / pytest run / allure serve）
3. 归档会话

2b. **报告超时保护**：
   假设代码生成和 pytest 执行已完成（py 文件和 pytest 输出已存在），如果总运行时间接近平台限制（例如 Codex exec 600s），报告生成本身不应导致整个运行失败：
   ```bash
   # 核心产物已到位，快速写入简洁报告
   # 使用 echo/cat 而非复杂 Python 脚本
   # 至少写入状态和文件列表
   ```
   报告生成应在 30s 内完成。如果超过 60s 未响应，使用极简报告模板（只包含状态、文件列表、pytest 输出）尽快结束。

4. 生成 artifact manifest：

   ```bash
   tide_py - <<'PY'
   from pathlib import Path
   from scripts.artifact_manifest import collect_artifact, write_manifest

   project = Path("$PROJECT_ROOT")
   artifacts = []
   for rel, kind in [
       (".tide/run-context.json", "run_context"),
       (".tide/parsed.json", "parsed"),
       (".tide/repo-status.json", "repo_status"),
       (".tide/project-assets.json", "project_assets"),
       (".tide/scenarios.json", "scenarios"),
       (".tide/generation-plan.json", "generation_plan"),
       (".tide/review-report.json", "review"),
       (".tide/execution-report.json", "execution"),
   ]:
       path = project / rel
       if path.exists():
           artifacts.append(collect_artifact(project, path, kind))
   write_manifest(project, artifacts)
   PY
   ```

5. 生成 `.tide/final-report.md`，必须包含：
   - **测试模式** (`test_mode`: `LIVE` / `DETERMINISTIC_SKELETON` / `LIVE_WITH_DETERMINISTIC_FALLBACK`)。
   - 本次 run 的无头/交互模式。
   - HAR 原路径、快照路径、sha256。
   - 解析端点数、匹配 repo 数、未匹配路径列表。
   - 生成文件列表。
   - pytest collect-only 和执行结果（仅限 `test_mode=LIVE` 时）。
   - **最终状态规则**：
     - `test_mode=LIVE` 且 pytest all pass → `PASS`（仅此情况可写 PASS）
     - `test_mode=LIVE` 且 pytest 有失败 → `FAIL`，附失败归类
     - `test_mode=DETERMINISTIC_SKELETON` → 最终状态写 **`DETERMINISTIC_SKELETON`**，不得写 PASS
     - `test_mode=LIVE_WITH_DETERMINISTIC_FALLBACK` → 根据 LIVE 部分结果写 PASS/FAIL
   - `scripts.generated_assertion_gate` 结果；若存在 `empty L4`、`empty L5`、`missing L4` 或 `missing L5`，最终状态必须写为 FAIL（覆盖 test_mode 规则）。
   - 确定性骨架升级尝试：成功/失败数量、原因。
   - 未完成阶段与失败原因。
   - 没有 final-pytest-output.txt 且 `test_mode=LIVE` 时，不得输出成功总结。

**[Hook]** 执行 `tide_py -m scripts.hooks run output:notify`

Task 6 完成。

---

## 隐私提示模板

在预检 HAR 校验完成后输出以下内容，等用户确认再进入 Wave 1：

```
[HAR 内容隐私提示]
HAR 文件中的 URL、请求/响应数据将发送给 AI 模型进行分析。
敏感头（Cookie/Authorization）已在解析时自动剥离。
如包含业务敏感数据（用户 PII、密钥等），建议脱敏后再使用。
确认继续？
```
