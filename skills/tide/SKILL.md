---
name: tide
description: "从 HAR 文件生成 pytest 测试套件，结合源码进行 AI 智能分析。触发方式：/tide <har-path>、'从 HAR 生成测试'、提供 .har 文件路径。"
argument-hint: "<har-file-path> [--quick] [--yes] [--non-interactive] [--resume] [--wave N]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, TaskCreate, TaskUpdate, TaskList
---

# Tide：HAR 转 Pytest 测试生成

> **重要：除非必要，否则不要改动已有项目中的测试配置或脚本。如需修改，先用 AskUserQuestion 向用户报告改动原因和改动范围，确认后方可执行。**

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
3. **Python 解释器自动检测**：
   ```bash
   # 优先使用项目虚拟环境 (pydantic v1 / jaydebeapi 等)
   if [ -f "$(pwd -P)/.venv/bin/python3" ]; then
       export PYTHON_BIN="$(pwd -P)/.venv/bin/python3"
   elif [ -f "$(pwd -P)/venv/bin/python3" ]; then
       export PYTHON_BIN="$(pwd -P)/venv/bin/python3"
   else
       export PYTHON_BIN="python3"
   fi
   echo "Using Python: $($PYTHON_BIN --version 2>&1) at $PYTHON_BIN"
   ```
4. **固定运行边界**：

   ```bash
   export PROJECT_ROOT="$(pwd -P)"
   export PLUGIN_DIR="$(cd "${CLAUDE_SKILL_DIR}/../.." && pwd -P)"
   mkdir -p "$PROJECT_ROOT/.tide"
   PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 - <<'PY' > "$PROJECT_ROOT/.tide/run-context.json"
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

4. **无头执行策略**：
   - 若 `.tide/run-context.json` 中 `requires_confirmation=false`，不得调用 AskUserQuestion。
   - 所有"是否继续 / 是否进入下一阶段 / 是否确认场景"的问题默认选择继续。
   - 将默认决策写入 `.tide/state.json` 的 metadata，例如 `{"headless_decisions":["continue_after_wave1","continue_after_wave2"]}`。
   - 若 `requires_confirmation=true`，保留现有 AskUserQuestion 交互。

5. 解析 `$ARGUMENTS`：`har_path`（必填）、`--quick`、`--yes`、`--non-interactive`、`--resume`、`--wave N`
6. **环境检查**：`test -f repo-profiles.yaml`，若缺失则打印带修复命令的错误信息并终止
5. **读取配置**：读取 `repo-profiles.yaml` 和 `tide-config.yaml`，提取 repos、test_dir、test_types、industry 等
6. **无源码降级**：repos 为空时设置 `no_source_mode=true`
7. **惯例指纹加载 + 按需 Prompt 组装**：
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
8. **恢复检查**：若 `state.json` 存在且未设置 `--resume`，询问继续/重来/查看摘要
9. **HAR 校验 + 认证头扫描 + 隐私提示**：
   HAR 校验：`uv run python3 -c "from scripts.har_parser import validate_har; from pathlib import Path; r = validate_har(Path('${har_path}')); print(r)"`
   认证头扫描：`uv run python3 -c "from scripts.har_parser import scan_auth_headers; from pathlib import Path; print(scan_auth_headers(Path('${har_path}')))"`
   隐私提示：输出 HAR 数据发送至 AI 模型的提示，请用户确认后继续
10. **参数摘要**：打印 HAR 路径/记录数/认证方式/测试目录/源码模式/模式

11. **成本预估**（fingerprint_mode=true 时展示）：
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

12. **用户意图采集**（新增）：
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

13. Task 1 完成。

---

## 第一波次：解析与准备（并行）

Task 2 → in_progress

1. `uv run python3 ${CLAUDE_SKILL_DIR}/../../scripts/state_manager.py init --har "${har_path}"`
2. **确定性脚本优先**：
   - HAR 快照：
     `uv run python3 -m scripts.har_inputs "$HAR_PATH" --project-root "$PROJECT_ROOT"` 若 CLI 尚未实现，则用 Python snippet 调用 `snapshot_har`。
   - HAR 解析：
     `uv run python3 -m scripts.har_parser "$HAR_SNAPSHOT" --profiles "$PROJECT_ROOT/.tide/repo-profiles.yaml" --output "$PROJECT_ROOT/.tide/parsed.json"`
   - repo 同步：
     `uv run python3 -m scripts.repo_sync --root "$PROJECT_ROOT" --profiles "$PROJECT_ROOT/.tide/repo-profiles.yaml" sync`
   - project-asset-scanner 仍可作为 Agent（如可用），但它只能写 `$PROJECT_ROOT/.tide/project-assets.json`。
   - **确定性回退**：若 Agent 未产生 `project-assets.json`（如无头/print 模式），立即执行确定性扫描：
     ```bash
     PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 - <<'PY'
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

**[Hook]** 若 tide-config.yaml 中有 hook 配置，执行 `uv run python3 scripts/hooks.py run wave1:parse:after`

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
   PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.scenario_validator \
     --parsed "$PROJECT_ROOT/.tide/parsed.json" \
     --scenarios "$PROJECT_ROOT/.tide/scenarios.json" \
     --generation-plan "$PROJECT_ROOT/.tide/generation-plan.json"
   ```

   若校验失败，返回 scenario-analyzer 修复一次；第二次仍失败则停止并写入 `.tide/final-report.md`。
4. 若非 `--quick`，展示确认清单供用户确认

**[Hook]** 若配置了 hook，执行 `uv run python3 scripts/hooks.py run wave2:analyze:after`

检查点保存，Task 3 完成。

---

## 第三波次：代码生成（并行扇出）

Task 4 → in_progress

1. 读取 `.tide/scenarios.json` → `generation_plan`
2. 读取 `.tide/project-assets.json`（若存在）— 项目已有工具类清单
3. 对每个模块并行启动一个 case-writer Agent，prompt 见 `agents/case-writer.md`，传入：
   - `detected_auth_type` — 认证方式
   - **`project_assets`**（新增）— 项目已有工具类方法清单，要求优先复用
   - **`test_granularity`**（新增）— 测试粒度
   - **`business_context`**（新增）— 业务场景描述
   - 按需加载的 code-style-python prompt 模块（来自 fingerprint 组装）
4. 全部完成后，对每个生成文件执行 py_compile + AST 检查
5. **格式检查**（新增）：对所有生成文件执行 format_checker：
   ```bash
   PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 -m scripts.format_checker <generation_plan 中所有 output_file 的父目录>
   ```
   - 对 FC04（硬编码 URL）的 WARNING 级别违规，自动提取并尝试修复
   - 对 FC11（硬编码业务 ID）的 ERROR 级别违规：自动将 `dataSourceId: 1` 等替换为 `self.ds_id` / `self.table_id` 变量引用，若无法修复则阻断流水线
   - 对 FC08（print 语句）的 ERROR 级别违规，自动移除
   - 记录问题到 `.tide/format-report.json`

**[偏好]** 写入本次生成的模块数 `uv run python3 scripts/preferences.py write --key last_module_count --value <N>`

检查点保存，Task 4 完成。

---

## 第四波次：评审 + 执行 + 交付

Task 5 → in_progress

1. 启动 case-reviewer Agent，prompt 见 `agents/case-reviewer.md`
   - case-reviewer 会依次完成：静态审查 → 自动修复 → 测试执行（`${PYTHON_BIN:-python3} -m pytest --collect-only -q` + `${PYTHON_BIN:-python3} -m pytest -x -v --tb=short`）→ **失败语义分析（新增）** → 最多 2 轮修复循环 → 输出 review-report.json 和 execution-report.json
   - **失败语义分析**：当测试失败时，解析 response body 的错误信息，判断失败根因类别：
     - `TEST_BUG` — 测试写错了（参数不对、断言值错）→ 自动修复
     - `ENV_ISSUE` — 环境问题（服务不可用、数据不存在）→ 标记为环境问题，调整预期
     - `BUSINESS_BUG` — 业务 bug（code≠1 但非参数问题）→ 标记为疑似缺陷
   - **等待 case-reviewer 全部完成再继续下一步**
2. 读取 `.tide/execution-report.json`，向用户报告执行结果：

   ```
   测试执行完成
   - 收集：成功
   - 通过：15/18
   - 失败：3
   - 失败归类：测试本身问题 1，环境问题 1，疑似缺陷 1
   - 修复轮数：1
   ```

3. 生成验收报告

**[Hook]** 执行 `uv run python3 scripts/hooks.py run wave4:review:after` 和 `uv run python3 scripts/hooks.py run output:notify`

Task 5 完成。

## 验收报告与归档

Task 6 → in_progress

1. 显示最终摘要（测试通过数/失败数/断言覆盖率/失败归类）
2. 打印验收命令（pytest collect-only / pytest run / allure serve）
3. 归档会话
4. 生成 artifact manifest：

   ```bash
   PYTHONPATH="$PLUGIN_DIR:$PYTHONPATH" uv run python3 - <<'PY'
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
   - 本次 run 的无头/交互模式。
   - HAR 原路径、快照路径、sha256。
   - 解析端点数、匹配 repo 数、未匹配路径列表。
   - 生成文件列表。
   - pytest collect-only 和执行结果。
   - 未完成阶段与失败原因。

**[Hook]** 执行 `uv run python3 scripts/hooks.py run output:notify`

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
