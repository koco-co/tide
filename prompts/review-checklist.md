# 用例审查清单

> 引用方：`agents/case-reviewer.md`
> 用途：`case-reviewer` Agent 的审查标准和自动修正阈值。

---

## 使用说明

1. 阅读指定范围内的每个生成测试文件。
2. 对下方每项检查记录：`通过`、`失败` 或 `不适用`。
3. 统计 `失败` 总数并计算偏差率。
4. 根据偏差阈值（第 6 节）执行对应的修正动作。
5. 审查完成后输出结构化的 `review-report.json`。

---

## 1. 断言完整性

根据断言层与测试类型矩阵，验证每个测试文件是否包含正确的断言层。

```
              L1      L2      L3      L4      L5
interface/    必须    必须    必须    可选    可选
scenariotest/ 必须    必须    必须    必须    必须
unittest/     —       —       必须    必须    可选
```

### 1.1 L1 协议断言 — interface/ 和 scenariotest/ 必须包含

| 检查项 | 验证内容 |
|-------|---------|
| 已调用 `assert_protocol()` | `interface/` 和 `scenariotest/` 中的每个测试方法都从 `core/assertions.py` 调用了 `assert_protocol()` |
| `expected_status` 与 HAR 一致 | `expected_status` 参数与该接口 HAR 中的 `response.status` 一致 |
| `max_time_ms` 合理 | 值为 `max(har_time_ms × 3, 1000)`，而非随意硬编码的值 |
| 包含 Content-Type | `expected_content_type` 已设置且与 HAR 响应 Content-Type 一致 |

### 1.2 L2 结构断言 — interface/ 和 scenariotest/ 必须包含

| 检查项 | 验证内容 |
|-------|---------|
| Pydantic 模型已定义 | 每种响应类型都定义了 `BaseModel` 子类 |
| 已调用 `model_validate()` | 每个测试使用 `model_validate(resp.json())`，而非手动字段检查 |
| 嵌套对象已建模 | 嵌套 JSON 对象不使用 `dict` 类型——应为 `BaseModel` 子类 |
| 可选字段正确 | HAR 中可为 `null` 的字段标注为 `Type \| None = None`，而非必填字段 |

### 1.3 L3 数据断言 — 所有包含 L3 的测试类型必须包含

| 检查项 | 验证内容 |
|-------|---------|
| 枚举校验已存在 | 若源码有枚举/常量，存在 `assert value in (...)` 检查 |
| 已检查业务码 | 成功场景中有 `assert body.code == BUSINESS_SUCCESS_CODE` |
| 范围检查已存在 | `@Min`/`@Max` 字段有对应的范围断言 |
| 分页不变量已检查 | 分页响应有 `totalCount >= 0`、列表长度一致性检查 |
| 使用了命名常量 | 枚举值使用模块级常量，而非内联整数 |

### 1.4 L4 业务断言 — scenariotest/ 必须包含

| 检查项 | 验证内容 |
|-------|---------|
| CRUD 步骤验证数据 | `add` 后重新查询并验证条目存在；`update` 后验证已变更；`delete` 后验证已消失 |
| 状态转换已验证 | 在状态机流程的每个步骤中检查了状态字段 |
| DB 断言已守卫 | 规划的 `if db:` DB 断言块存在且有正确守卫 |
| 无 DB 写入 | `DBHelper` 只调用了 `query_one`、`query_all`、`count`——绝无 `execute` 或 `insert` |

### 1.5 L5 AI 推断断言 — scenariotest/ 必须包含，interface/ 仅允许 HIGH 置信度

| 检查项 | 验证内容 |
|-------|---------|
| 来源注释已存在 | 每条 L5 断言上方有 `# L5[置信度]: 源文件:行号 — 推断依据` |
| 置信度已标注 | 注释中明确写了 `HIGH` 或 `SPECULATIVE` |
| SPECULATIVE 未出现在 interface/ 中 | `tests/interface/` 文件中没有 `SPECULATIVE` 置信度的断言 |
| 推断依据具体 | 注释指明了具体的方法名、条件或代码模式——而非模糊描述 |

---

## 2. 场景完整性

验证生成的场景是否覆盖了 `scenarios.json` 中规定的必需类别。

### 2.1 CRUD 闭环完整性

对 `scenarios.json` 中识别的每个 CRUD 组：

| 检查项 | 验证内容 |
|-------|---------|
| 包含全部 4 种 CRUD 操作 | CRUD 测试中都有 create + read + update + delete 步骤 |
| 包含验证步骤 | 每次写操作后，测试重新查询以验证变更 |
| Fixture 中有清理逻辑 | 通过 `yield` fixture 清理创建的数据，即使测试失败也执行 |
| 测试类型正确 | CRUD 闭环测试位于 `tests/scenariotest/` 而非 `tests/interface/` |

### 2.2 异常路径覆盖

每个接口**至少**必须包含以下异常场景：

| 必须包含的异常场景 | 检查内容 |
|----------------|---------|
| 资源不存在 | 存在使用不存在 ID 的测试（如 `id=999999999`） |
| 权限拒绝（当源码有认证检查时） | 存在使用无效/缺失认证的测试 |

`scenarios.json` 中的其他异常场景也必须存在。

### 2.3 边界值覆盖

对有数值参数的接口：

| 检查项 | 验证内容 |
|-------|---------|
| 零值/负值已测试 | `pageSize=0`、负 ID 等 |
| 最大值已测试 | 大 `pageSize`、大 ID |
| 约束边界值已测试 | 正好等于 `@Min` 和 `@Max` 的值 |

### 2.4 参数校验覆盖

对有 `@Valid`/`@NotNull` 字段的接口：

| 检查项 | 验证内容 |
|-------|---------|
| 缺少必填字段的测试 | 至少有一个测试删除了必填字段 |
| 空字符串测试 | 至少有一个测试为 `@NotBlank` 字段传入 `""` |

---

## 3. 源码交叉验证

审查完生成的测试后，快速扫描源码以发现遗漏的场景。

### 3.1 Controller 方法覆盖率

```bash
# 找到 Controller 中所有 @XxxMapping 方法
grep -n "@PostMapping\|@GetMapping\|@PutMapping\|@DeleteMapping" \
  .repos/group/repo/src/main/java/.../controller/DataMapController.java
```

检查：每个 Controller 方法是否至少有一个测试对应？若某方法没有对应测试，标记为缺口。

### 3.2 异常处理器覆盖率

```bash
# 找到 Service 中所有异常抛出
grep -n "throw new\|return Result.fail\|return R.error" \
  .repos/group/repo/src/main/java/.../service/DataMapService.java
```

检查：Service 中每种不同的异常/错误返回，是否都有测试能触发它？

### 3.3 条件分支覆盖率

```bash
# 找到 Service 中的 if/else 分支
grep -n "if (" .repos/group/repo/src/main/java/.../service/DataMapService.java | head -20
```

检查：是否存在重要业务分支（非简单空值检查）没有对应测试场景？将这些标记为缺口。

---

## 4. 代码质量检查

### 4.1 无硬编码值

| 检查项 | 查找内容 |
|-------|---------|
| 无内联魔法数字 | 断言中无未用命名常量的原始整数（如 `1`、`4`、`5`） |
| 无内联 URL | 测试方法中无硬编码的 base URL——应使用 `client` fixture |
| 无内联凭据 | 测试代码中无 Cookie、令牌或密码 |

例外：用于"不存在"场景的 ID（`999999999`）允许使用，但需加注释。

### 4.2 无可变操作

| 检查项 | 查找内容 |
|-------|---------|
| 无 fixture 修改 | 测试方法不直接修改 fixture 对象 |
| 使用了冻结数据类 | 自定义值对象使用了 `@dataclass(frozen=True)` |
| 无共享可变状态 | 无模块级可变变量在测试间被修改 |

### 4.3 清理正确性

| 检查项 | 查找内容 |
|-------|---------|
| API fixture 使用 `yield` | 每个通过 API 创建数据的 fixture 在 `yield` 后有清理代码 |
| 清理使用 API | 清理通过 `client.delete/post` 完成——而非直接 DB 操作 |
| `scope` 合理 | 只读 fixture 使用 `scope="module"`，写 fixture 使用 `scope="function"` |

### 4.4 规模限制

| 检查项 | 限制 | 验证方式 |
|-------|------|---------|
| 文件长度 | < 400 行 | 对每个生成文件执行 `wc -l` |
| 测试方法长度 | < 50 行 | 统计每个 `def test_` 方法的行数 |
| 嵌套深度 | ≤ 4 层 | 检查是否有深层嵌套的 `for`/`if` 块 |

超过 400 行的文件必须按接口组或场景类别拆分。

### 4.5 类型注解

| 检查项 | 查找内容 |
|-------|---------|
| 所有测试方法已注解 | `def test_xxx(self, client: APIClient) -> None:` |
| 所有 fixture 已注解 | `def fixture_xxx(...) -> Generator[T, None, None]:` |
| 无裸 `dict` 或 `list` | 使用 `dict[str, Any]` 或 `list[SubModel]` |

---

## 5. 可运行性检查

### 5.1 导入完整性

| 检查项 | 验证内容 |
|-------|---------|
| 所有使用的符号已导入 | 不会出现 `NameError`——所有名称都已导入或定义 |
| 无循环导入 | 内部导入不构成循环依赖 |
| 已导入 `allure` | 使用了 allure 装饰器时 `import allure` 存在 |
| 已导入 `pytest` | 使用了 fixture 或标记时 `import pytest` 存在 |

### 5.2 Fixture 可用性

| 检查项 | 验证内容 |
|-------|---------|
| `client` fixture 使用正确 | `client: APIClient` 参数可从 `tests/conftest.py` 获取 |
| `db` fixture 使用正确 | `db: DBHelper \| None` 参数可从 `tests/conftest.py` 获取 |
| 模块本地 fixture 已定义 | 文件中使用的 fixture 要么在本文件中定义，要么在对应的 `conftest.py` 或 `tests/conftest.py` 中定义 |
| 无 fixture 名称冲突 | 没有在多个层级重复定义同名 fixture |

### 5.3 语法与收集

作为可运行性验证的一部分执行以下检查：

```bash
uv run pytest --collect-only tests/
```

期望结果：所有测试文件无错误地被收集。任何 `SyntaxError`、`ImportError` 或 `FixtureLookupError` 都是**阻塞问题**——在标记审查完成前必须修复。

---

## 6. 偏差阈值与修正动作

完成所有检查后计算偏差率：

```
偏差率 = （失败项数量）/（适用检查总数）× 100%
```

| 偏差率 | 处理动作 |
|--------|---------|
| **< 15%** | **静默修复** — 使用 `Edit` 工具直接修正问题，无需通知用户 |
| **15% – 40%** | **修复并标记** — 修正所有问题，然后在 `review-report.json` 中添加 `flag_items` 部分，列出变更内容和原因 |
| **> 40%** | **阻塞并升级** — 不得自动修复，写详细的 `review-report.json` 描述所有问题，通过 AskUserQuestion 通知用户，在继续前请求指导 |

### 何时使用 AskUserQuestion

以下情况使用 `AskUserQuestion`：
- 偏差率 > 40%（始终）
- 对 L4/L5 断言的解读存在歧义的源码
- 缺少源码导致无法为规划中的测试生成场景
- 经过 2 次自动修复后测试仍无法运行

---

## 7. 审查报告输出

审查完成后，写入 `.autoflow/review-report.json`：

```json
{
  "reviewed_at": "<ISO8601>",
  "files_reviewed": ["tests/interface/dassets_datamap/test_datamap.py"],
  "total_checks": 42,
  "passed": 38,
  "failed": 4,
  "deviation_rate": 9.5,
  "action_taken": "silent_fix",
  "issues_found": [
    {
      "file": "tests/interface/dassets_datamap/test_datamap.py",
      "check": "L1 协议断言",
      "line": 45,
      "severity": "MEDIUM",
      "description": "max_time_ms 硬编码为 5000，而非从 HAR 时间计算（45ms × 3 = 135ms，最小 1000ms）",
      "fixed": true
    }
  ],
  "flag_items": [],
  "blocking_issues": []
}
```

问题严重程度级别：
- `CRITICAL`：断言完全缺失（必须的断言层未实现）
- `HIGH`：断言逻辑错误（期望值错误、方法错误）
- `MEDIUM`：断言不够优化（硬编码、缺少常量、未使用不可变模式）
- `LOW`：风格问题（命名、缺少注解）
