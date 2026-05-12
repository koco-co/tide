# Tide 泛化性改进实施计划 — no_source_mode 与项目风格自适应

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**目标:** 修复 Tide 在不同 HAR 类型上的泛化能力。当前 metadata sync HAR (92.95) 和编排规则 HAR (54.55) 之间存在 38 分差距，根因在 Agent 提示词的 3 个硬编码规则。

**改动范围:** 仅改 Agent 提示词 markdown 文件（4 个），不改 Python 代码。

---

## Task 1 (P0): scenario-analyzer — no_source_mode 置信度估算

**文件:** `agents/scenario-analyzer.md:66`

**当前:**
```markdown
- 若上下文包含 `no_source_mode = true`：跳过阶段一（源代码追踪），所有场景标记 confidence: 'low'
```

**改为:**
```markdown
- 若上下文包含 `no_source_mode = true`：跳过阶段一（源代码追踪）。基于场景特征估算置信度：
  - **e2e_chain** 类型且 steps ≥ 5 → confidence: 'medium'（多步链路表示业务场景完整）
  - 写操作端点（POST/PUT/DELETE 且有请求体）→ confidence: 'medium'
  - **har_direct** 单接口回放 → confidence: 'low'
  - **param_validation / boundary** → confidence: 'low'
  - 估算依据记录在场景对象的 `confidence_reason` 字段（如 `"e2e chain with 12 steps"`）
```

**验证:** 传入 `no_source_mode=true` 的 HAR 文件运行 Tide，检查 `.tide/scenarios.json` 中 E2E 链路的 confidence 是否为 medium 而非 low。

---

## Task 2 (P0): scenario-analyzer — 无源码时 L4/L5 断言启发式

**文件:** `agents/scenario-analyzer.md:148-155`

**当前:**
```markdown
- **L4**：从源码 DAO/Mapper 层提取 `tables_touched`；若无源码访问，从响应体推断断言
- **L5**：从源码提取副作用证据；若无则将数组置空

仅包含适用的层级。若未找到数据库/副作用证据，则省略 L4/L5。
```

**改为:**
```markdown
- **L4**：从源码 DAO/Mapper 层提取 `tables_touched`；若无源码访问，从响应体推断断言
  - **no_source_mode 下的 L4 启发式**：若端点是写操作（POST/PUT/DELETE），自动规划 L4 断言
  - L4 内容：请求执行后，通过相关查询端点验证写操作生效（如创建后查询详情、更新后对比字段）
- **L5**：从源码提取副作用证据；若无则将数组置空
  - **no_source_mode 下的 L5 启发式**：若场景类型为 e2e_chain 且 steps ≥ 2，对链式端点间的数据传递规划 L5 断言
  - L5 内容：前一步骤的响应字段被后一步骤正确使用（如前一创建的 taskId 在后一查询中出现）

**no_source_mode 下 L4/L5 激活条件：**
- L4：端点 method 为 POST/PUT/DELETE 且 request_body 非空
- L5：场景类型为 e2e_chain 且步骤间有 depends_on 依赖关系
```

**验证:** 传入编排规则 HAR，检查 generated test 中写操作（addOrUpdateTask）是否含 L4 断言，E2E 链路是否含 L5 断言。

---

## Task 3 (P0): case-writer — 类命名规范自适应

**文件:** `agents/case-writer.md:139-141`

**当前:**
```markdown
- 文件：`test_{module}.py`
- 类：`Test{Module}{Feature}` — 大驼峰命名
- 方法：`test_{feature}_{scenario}` — 下划线命名
```

**改为:**
```markdown
- 文件：`test_{module}.py`
- **类命名规范（自适应）**：
  1. 生成代码前，读取项目已有测试文件中与当前输出文件同目录的 1-3 个 `.py` 文件（排除 `conftest.py` 和 `__init__.py`）
  2. 从已有文件中提取所有以 `Test` 开头的类名，检测命名模式：
     - `Test_xxx_xxx` → snake_case（如 `Test_metadata_sync_template`）
     - `TestXxxXxx` → PascalCase（如 `TestMetadataSyncTemplate`）
  3. 以发现的模式为准生成测试类名；若未发现已有文件，回退到 PascalCase 默认
  4. 类名逻辑：`Test{Module}_{Feature}`（snake_case 模式时用下划线分隔）
- 方法：`test_{feature}_{scenario}` — 下划线命名
```

**注意:** 需要确保 project-scanner 运行在 case-writer 之前（已是现有流程），且 case-writer 能在 prompt 中看到 `convention-fingerprint.yaml` 的 `naming_convention` 字段。

**验证:** 对含 snake_case 测试类的项目（如 dtstack），运行 Tide 生成测试，检查类名为 `Test_xxx_xxx` 而非 `TestXxxXxx`。

---

## Task 4 (P1): case-writer — no_source_mode 动态 ID 模板

**文件:** `agents/case-writer.md:189-233`（在"动态 ID 解析"节末尾追加）

**当前:** 动态 ID 解析 3 步优先级（行 230-233）均依赖源码追踪找到现有方法或查询 API。

**追加节（在行 233 后）:**

```markdown
### no_source_mode 下的动态 ID 回退

当 `no_source_mode = true` 时，无法通过源码追踪找到查询方法。改用以下策略：

1. **从 HAR 中识别查询型端点**：扫描 parsed.json 中符合以下任一条件的端点：
   - GET 方法
   - POST 方法且 path 包含 `list`、`query`、`page`、`search`、`get`、`find` 关键词
2. **在 setup_method 中自动生成 `_get_xxx_id()` 辅助方法**：
   ```python
   def _get_project_id(self) -> int:
       """从 HAR 查询端点获取有效的 projectId"""
       resp = self.req.post(BatchApi.list_projects, "查询项目列表", {"page": 1, "size": 20})
       assert resp.get("code") == 1, "查询项目列表失败"
       project_list = resp.get("data", {}).get("data", [])
       assert len(project_list) > 0, "无可用项目"
       return project_list[0].get("id", 0)
   ```
3. **对每个硬编码风险字段**（projectId, taskId, sourceId, tableId 等 `xxxId` 模式），检查 HAR 中是否有对应查询端点；若有则生成辅助方法替换硬编码值
4. **若无任何查询端点可用**（极端情况），维持 HAR 原始值但添加注释 `# no_source_mode: 无查询端点可用，使用 HAR 原始值`

**优先级仍是 1>2>3**，第一步复用 HAR 自身查询端点。
```

**验证:** 对编排规则 HAR（含 listProjects 查询端点），检查生成代码中 projectId 是否通过 `_get_project_id()` 动态获取而非硬编码 101。

---

## Task 5 (P1): project-scanner — 命名规范写入 fingerprint

**文件:** `agents/project-scanner.md:65-77` + `agents/project-scanner.md:176-220`

**改动 1（行 65-77）:** 当前只检查命名模式但输出格式只有 `naming_convention` 字段，需要明确类别。

```markdown
4. **命名规范**：读取 2-3 个测试文件的类定义，检测：
   - 类名是否以 `Test` 开头
   - 采用 snake_case 还是 PascalCase（如 `Test_metadata_sync_template` vs `TestMetadataSync`）
   - 方法名命名模式
```

**输出格式（行 76）不动（已有 `naming_convention`），但补充说明：**
```markdown
  "naming_convention": "Test_{module}_{feature}"  # 或 "Test{Module}{Feature}"
  "naming_convention_type": "snake_case"  # 或 "pascal_case"
```

**改动 2（行 176-220）:** 在 project-profile.json 的 code_style 维度中包含 naming_convention，同时写入 convention-fingerprint.yaml 的 test_style 段。

`project-profile.json` 的 code_style 段增加：
```json
{
  "naming_convention_type": "snake_case",
  "naming_convention": "Test_{module}_{feature}"
}
```

`convention-fingerprint.yaml` 的 test_style 段增加：
```yaml
test_style:
  naming_convention_type: snake_case  # 或 pascal_case
  naming_class_pattern: "Test_{module}_{feature}"  # 类名模板
```

**验证:** 对 dtstack 项目运行 project-profile 扫描，检查 `project-profile.json.dimensions.code_style.naming_convention_type` 值为 `snake_case`。

---

## Task 6 (P2): scenario_validator — 生成后质量校验（可选）

**文件:** `scripts/scenario_validator.py:10-58`

**当前:** `validate_scenario_outputs()` 只校验 `endpoint_id` 完整性和 `scenario_id` 引用。

**改为:** 增加 `validate_generated_code()` 函数：

```python
def validate_generated_code(
    generated_file: Path,
    project_profile: dict | None = None,
) -> dict[str, Any]:
    """校验生成代码的质量问题。"""
    code = generated_file.read_text(encoding="utf-8")
    issues = []

    # 1. 检测硬编码业务 ID（xxxId = 整数）
    hardcoded_id_pattern = re.compile(r'(?:projectId|taskId|sourceId|tableId|metaId|dataSourceId)\s*[:=]\s*(\d{2,})')
    matches = hardcoded_id_pattern.findall(code)
    if matches:
        issues.append({
            "type": "hardcoded_id",
            "count": len(matches),
            "severity": "ERROR",
            "matches": matches[:5],
        })

    # 2. 检测类命名风格（如果 project_profile 提供了命名规范）
    if project_profile:
        expected_type = project_profile.get("dimensions", {}).get("code_style", {}).get("naming_convention_type")
        if expected_type == "snake_case":
            class_pattern = re.compile(r'^class Test[A-Z][a-z]')
            pascal_classes = class_pattern.findall(code)
            if pascal_classes:
                issues.append({
                    "type": "class_naming_mismatch",
                    "count": len(pascal_classes),
                    "severity": "WARNING",
                    "expected": "snake_case (Test_xxx)",
                    "found": "PascalCase (TestXxx)",
                })

    # 3. 检测 L4/L5 断言存在性（写操作应当有 L4，链式场景应当有 L5）
    # ...

    return {"ok": len(issues) == 0, "issues": issues, "total_issues": len(issues)}
```

**验证:** `pytest tests/test_scenario_validator.py` 通过。

---

## 执行顺序

```
Task 1 → Task 2 → Task 5 → Task 3 → Task 4 → Task 6

(project-scanner 先改才能提供 naming_convention → case-writer 使用它)
```

## 验证命令

```bash
# 1. 对每个改动的提示词文件，确认 markdown 解析无语法错误
cd /Users/poco/Projects/tide && python3 -c "
import yaml, re
for f in ['agents/scenario-analyzer.md', 'agents/case-writer.md', 'agents/project-scanner.md']:
    text = open(f).read()
    assert text.count('---') >= 2, f'{f}: 前端元数据格式异常'
    print(f'✅ {f}: {len(text)} chars OK')
"

# 2. 运行现有测试确保无回归
cd /Users/poco/Projects/tide && python3 -m pytest tests/ -v --tb=short -x 2>&1 | tail -20

# 3. 端到端验证
cd /Users/poco/Projects/dtstack-httprunner
# 用编排规则 HAR 重新运行 Tide 并检查输出的三项指标
claude "/tide .tide/trash/batch_orchestration_rules.har --yes --non-interactive"
# 检查生成文件:
#   - 类名是否为 snake_case
#   - 是否有 _get_project_id() 辅助方法
#   - E2E 场景 confidence 是否为 medium
```
