---
name: tide
description: "从 HAR 文件生成 pytest 测试套件，结合源码进行 AI 智能分析。触发方式：/tide <har-path>、'从 HAR 生成测试'、提供 .har 文件路径。"
argument-hint: "<har-file-path> [--quick] [--resume] [--wave N]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, TaskCreate, TaskUpdate, TaskList
---

# Tide：HAR 转 Pytest 测试生成

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
3. 解析 `$ARGUMENTS`：`har_path`（必填）、`--quick`、`--resume`、`--wave N`
4. **环境检查**：`test -f repo-profiles.yaml`，若缺失则打印带修复命令的错误信息并终止
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
   - 若 assertion.style == "code_success" → +30-assert-code-success.md
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
    询问用户是否继续。用户拒绝则终止流程。接受则继续 Wave 1。

12. Task 1 完成。

---

## 第一波次：解析与准备（并行）

Task 2 → in_progress

1. `uv run python3 ${CLAUDE_SKILL_DIR}/../../scripts/state_manager.py init --har "${har_path}"`
2. **并行**启动 har-parser 和 repo-syncer Agent，prompt 分别见 `agents/har-parser.md` 和 `agents/repo-syncer.md`（仅在 `no_source_mode=false` 时启动后者）
3. 读取验证输出（.tide/parsed.json / .tide/repo-status.json）
4. 输出验证摘要，检查点保存

**[Hook]** 若 tide-config.yaml 中有 hook 配置，执行 `uv run python3 scripts/hooks.py run wave1:parse:after`

Task 2 完成。

---

## 第二波次：场景分析

Task 3 → in_progress

1. 读取 `agents/scenario-analyzer.md`，传入上下文：no_source_mode、test_types、industry_mode
2. 启动 scenario-analyzer Agent（opus）
3. 读取 .tide/scenarios.json
4. 若非 `--quick`，展示确认清单供用户确认

**[Hook]** 若配置了 hook，执行 `uv run python3 scripts/hooks.py run wave2:analyze:after`

检查点保存，Task 3 完成。

---

## 第三波次：代码生成（并行扇出）

Task 4 → in_progress

1. 读取 .tide/scenarios.json → generation_plan
2. 对每个模块并行启动一个 case-writer Agent，prompt 见 `agents/case-writer.md`，传入 detected_auth_type
3. 全部完成后，对每个生成文件执行 py_compile + AST 检查

**[偏好]** 写入本次生成的模块数 `uv run python3 scripts/preferences.py write --key last_module_count --value <N>`

检查点保存，Task 4 完成。

---

## 第四波次：评审 + 执行 + 交付

Task 5 → in_progress

1. 启动 case-reviewer Agent，prompt 见 `agents/case-reviewer.md`
2. 检测包管理器并执行测试
3. 生成验收报告

**[Hook]** 执行 `uv run python3 scripts/hooks.py run wave4:review:after` 和 `uv run python3 scripts/hooks.py run output:notify`

Task 5 完成。

## 验收报告与归档

Task 6 → in_progress

1. 显示最终摘要（测试通过数/失败数/断言覆盖率）
2. 打印验收命令（pytest collect-only / pytest run / allure serve）
3. 归档会话

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
