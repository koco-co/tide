# Tide 插件优化 — 最终报告

## 2026-05-12 Iter9 审计附录

Codex 复核 Iter7 结论时发现：原报告的 92.95/100 对生成文件局部质量成立，但不能作为“硬性质量门全过”的最终结论。

- 全量目标项目 `pytest --collect-only` 当前失败：`.venv/bin/python3 -m pytest --collect-only` 命中 75 个既有收集错误，主要是目标项目缺 `cx_Oracle` 和 stream/testdata import 问题；该命令还会在 collect 阶段执行目标项目 API 初始化代码。
- 生成文件局部收集通过：`tests/interface/test_metadata_sync.py` 与 `test_assets_datamap.py` scoped collect 仍为 36/36。
- 原 FC11 漏检字符串数字业务 ID：Iter7 生成的 `test_metadata_sync.py` 仍包含 `dataSourceId: "43"`、`dataSourceId: "99999999"`、`tableId: "99999999"`。Iter9 已修复 `scripts/format_checker.py`，现在会将这些识别为 ERROR。
- Iter9 无法完成 fresh Claude/Tide 生成：运行 Claude Code 会向外部服务发送目标项目数据并改写目标文件，审批因缺少明确用户同意而被拒绝。

**当前审计结论：暂不应宣称硬性质量门全过。** Iter9 本地修复已通过 Tide 自测 `159 passed`，但需要用户明确批准外部 Claude Code 运行后，才能重新生成、重新评分并判断是否恢复 ≥90。

Iter9 分支/PR：`codex/tide-iter-9-audit-quality-gates`，https://github.com/koco-co/tide/pull/1

## 当前结论

**Conditional / Hold.** 用户已授权清理旧 Tide 生成物并运行 Claude Code fresh generation；Iter11 已选中正确 SparkThrift HAR，但硬性质量门仍未通过。`metadata_direct_test.py` 生成了 21 个 `test_*` 方法，但所在类名为 `SyncTaskTest`、`DataSourceTest`、`JobQueryTest`、`TableQueryTest`，pytest 不会收集这些类。

恢复 `>=90` 评估前必须重新运行并确认：每个生成文件 scoped `pytest --collect-only` 的节点数符合预期、format checker 0 ERROR、L1-L5 证据完整、scenario_id 唯一、confidence>=medium 比例达标、风格契合度抽查通过。

## 2026-05-12 Iter10 Fresh Run 附录

用户已明确授权后，Codex 完成了一次 fresh Claude Code + Tide 运行。结论仍为 **Conditional / Hold**：

- 运行完成，但选错 HAR：`evals/tide-optimization/iter_10/session.log:1` 显示生成源为 `batch_orchestration_rules.har`，不是目标 SparkThrift 元数据同步 HAR。
- `.tide/parsed.json:3` 为 `source_har: ".tide/trash/batch_orchestration_rules.har"`；`.tide/scenarios.json:6` 为 `DAGScheduleX_POST_api_rdos_batch_batchTask_e2e_chain`。
- Scoped generated collect 通过 30 tests，但全量 `pytest --collect-only` 仍因既有目标项目问题失败 75 errors。
- Iter10 分数为 **65.0/100**，主要扣分来自“自然语言说 HAR 在 trash 下时，多个 HAR 候选被静默猜错”。
- 已新增修复：`scripts.har_inputs.resolve_har_input()` 和 skill no-guess 规则。未来传目录或自然语言指向 `.tide/trash` 且存在多个 HAR 时，Tide 必须询问或在无头模式失败，不得猜测。

## 2026-05-12 Iter11 Fresh Run 附录

Iter11 在清理旧生成物并只保留目标 HAR 后完成 fresh run，结论仍为 **Conditional / Hold**：

- 正确 HAR 已选中：`.tide/parsed.json` 指向 `20260509_152002_20260509_150847_172.16.122.52.har`，生成 28 endpoints / 49 scenarios。
- 输出文件为 `testcases/scenariotest/assets/assets_datamap_v2_test.py` 与 `testcases/scenariotest/assets/meta_data_sync/metadata_direct_test.py`。
- 场景质量门部分通过：`scenario_id total=49 unique=49`，confidence 为 `high=28`、`medium=21`。
- 收集质量门失败：combined scoped collect 只列出 28 个 datamap tests；metadata-only collect 退出 5，输出 `no tests ran`。
- 已新增修复：`scripts/format_checker.py` 增加 FC14，凡包含 `test_*` 方法但类名不以 `Test` 开头即 ERROR；`agents/case-writer.md` 明确禁止 `SyncTaskTest` 这类 pytest 不收集的类名。
- Iter11 分数为 **78.9/100**；正确 HAR 和场景理解恢复，但 21 个 metadata tests 不可见，不能宣称达成。

## 2026-05-12 Iter12 Fresh Run 附录

安装 Iter11 修复后再次 fresh run，结论提升为 **Near Miss / Hold**：

- 正确 HAR 已选中，`.tide/parsed.json` 指向目标 SparkThrift HAR，去重后 28 endpoints。
- 生成 3 个文件：`test_datamap_browse.py`、`test_table_detail_query.py`、`test_sync_task_management.py`。
- Iter11 的类名收集问题已修复：逐文件 collect 分别为 16、5、6，总计 27 tests。
- 实测执行通过：`.venv/bin/python3 -m pytest <3 generated files> -q` 返回 `27 passed, 1 warning in 71.45s`。
- 仍未达成硬性全绿：`.tide/scenarios.json` 缺失，无法审计 `scenario_id` 和 confidence；`.tide/execution-report.json` 与最终 summary/手工复测结果不一致；format checker 虽 0 errors，但仍有 4 warnings / 107 infos。
- Iter12 分数为 **88.4/100**，接近但仍不应宣称 `>=90`。

## 2026-05-12 Iter13 Fresh Run 阻塞

Iter13 先修复了 Iter12 暴露的两个产物问题：`scripts/scenario_validator.py` 现在阻断缺失/重复/低置信场景产物，`scripts/test_runner.py` 新增 `report` 子命令用最终 pytest 输出重写 `.tide/execution-report.json`。Tide 自测为 `166 passed`，修复已推送。

但安装后 fresh run 触发红线阻塞：

- Claude 直接修改了目标项目 `utils/assets/requests/meta_data_requests.py`，新增 17 个 API helper，违反“只动 `testcases/` 和 `.tide/`”。
- Claude 生成了 `testdata/scenariotest/assets/meta_data/...`，也超出允许写范围。
- `.tide/scenarios.json`、`.tide/generation-plan.json`、`.tide/execution-report.json`、`.tide/review-report.json` 均未产生。
- 已在取证后撤回本轮业务代码和无效测试生成物；证据见 `evals/tide-optimization/iter_13/blockers.md`。

当前状态回落为 **Blocked / Hold**。下一步必须先实现目标写范围硬保护：任何对 `api/`、`dao/`、`utils/`、`config/`、`testdata/` 的目标写入都要阻断或自动回滚，否则不能继续 fresh run。

## 2026-05-12 Iter14 Assisted Run 附录

Iter14 实现并验证了目标写范围硬保护：`scripts/write_scope_guard.py` 对目标项目 `api/`、`dao/`、`utils/`、`config/`、`testdata/`、`resource/` 做快照和哈希校验，Tide 自测已在提交 `b1793c7` 中达到 `170 passed`。安装后外层校验确认本轮没有新增/删除/修改禁止目录文件。

在目标项目上继续生成时发现新的入口阻塞：

- `claude -p '/tide ...'` 返回 `Unknown command: /tide`；同样模式下其他插件命令也不可用。
- 自然语言 Tide workflow prompt 只创建 `.tide/run-context.json` 后挂起；短 prompt 生成了部分 `.tide/scenarios.json` 和 `.tide/generation-plan.json`，但缺测试文件且场景产物无 `endpoint_id`、confidence 比例不合格。
- Codex 随后接手修复产物并补齐测试，所以本轮只能算 assisted recovery，不能算 autonomous Tide pass。

最终 assisted 产物：

- 正确 HAR：`20260509_152002_20260509_150847_172.16.122.52.har`
- `parsed.json`: 31 raw / 28 dedup endpoints
- `scenarios.json`: 28 scenarios，confidence medium/high ratio 100%
- 新增测试：`tide_metadata_sync_test.py`、`tide_assets_datamap_test.py`
- 窄范围执行：`6 passed, 4 skipped, 1 warning in 22.50s`
- 写范围校验：`ok=true`，禁止目录无变更

Iter14 评分为 **84.0/100 — Assisted / Hold**。写范围风险已解决，但 Claude Code 非交互入口仍未可靠激活 Tide workflow，暂不能恢复 `>=90` 推广结论。

## 历史迭代概述 (7 轮)

| 迭代 | 总分 | 关键改进 | 关键时刻 |
|------|------|---------|---------|
| **基线** | 72 | — | v1.3.0 原生能力 |
| **Iter1** | 66.2 | PYTHONPATH/VIRTUAL_ENV/BaseRequests 修复 | 首次管道通路 |
| **Iter2** | 76.8 | 管道首次完整跑通 (52 场景, 3 文件) | 管道建立 |
| **Iter3** | 56.4 | — | deepseek 模型 sandbox 退化 |
| **Iter4** | 54.2 | — | @classmethod 回归 (9 处) |
| **Iter5** | 80.35 | setup_method 0 @classmethod, 16 文件 | 代码质量突破 |
| **Iter6** | 86.55 | 硬编码 ID 23→1 (-96%), PYTHON_BIN 检测, 确定性 project-assets | 质量接近目标 |
| **Iter7** | **92.95 (历史 claim，Iter9 已降级)** | **--yes --non-interactive 无头验证、36/36 scoped collect 通过、0 人工干预** | **不能替代硬门全过** |
| **Iter10** | **65.0** | **暴露多 HAR 静默误选；新增 no-guess resolver** | **fresh run 未达标** |
| **Iter11** | **78.9** | **正确 HAR；新增 FC14 pytest 类名收集门** | **metadata 文件 0 tests collected** |
| **Iter12** | **88.4** | **27 tests collect+execute 通过；FC14 修复生效** | **缺 scenarios.json + 报告不一致** |
| **Iter13** | **Blocked** | **新增场景/执行报告硬化；fresh run 触发写范围红线** | **停止继续生成** |
| **Iter14** | **84.0 assisted** | **新增写范围硬保护；assisted 输出 6 passed / 4 skipped** | **Claude Code `/tide` 入口不可用，非自主达成** |

## 7 轮评分趋势

```
100 ┤
 95 ┤                                    ● Iter7: 92.95 (historical)
 90 ┤                                    ● Iter6: 86.55
 85 ┤
 80 ┤                        ● Iter2: 76.8 ● Iter5: 80.35
 75 ┤  ● 基线: 72
 70 ┤  ● Iter1: 66.2
 65 ┤
 60 ┤
 55 ┤           ● Iter3: 56.4  ● Iter4: 54.2
 50 ┤
    └─────Iter0─────Iter1─────Iter2─────Iter3─────Iter4─────Iter5─────Iter6─────Iter7
```

## 改进归类

### 管道层级

| 改进 | 轮次 | 效果 |
|------|------|------|
| PYTHONPATH 修复 | Iter1 | `sys.path` 正确 |
| VIRTUAL_ENV 消除 | Iter1 | 无警告 |
| 权限绕过 | Iter4 | `--dangerously-skip-permissions` |
| 确定性 project-assets 回退 | Iter6 | 无头/print 模式也能生成项目资产清单 |
| PYTHON_BIN 自动检测 (.venv 优先) | Iter6 | pydantic v1 兼容 → pytest collect-only 通过 |
| **--yes --non-interactive 无头模式** | **Iter7** | **全自动流水线，零人工干预** |

### 代码质量层级

| 改进 | 轮次 | 效果 |
|------|------|------|
| 强制 `setup_method(self)` | Iter1+Iter5 | 0 @classmethod |
| format_checker FC12 (classmethod) | Iter2 | ERROR 级检查 |
| format_checker FC13 (scenario_id) | Iter2 | 跨文件唯一性 |
| FC11 升级为 ERROR (硬编码 ID) | Iter6 | 阻断流水线 |
| case-writer 硬编码 ID 禁令强化 | Iter6 | dataSourceId/tableId/metaId 明令禁止 |
| code-style 硬编码业务 ID 禁令 | Iter6 | 00-core.md + dtstack 模板双保险 |
| **case-reviewer 自动修复** | **Iter7** | **6 处问题自动修复 (辅助函数提取、L1 补充、代码精简)** |

### 场景多样性

| 轮次 | 场景数 | 测试文件 | 类型分布 |
|------|--------|---------|----------|
| Iter2 | 52 | 3 | — |
| Iter4 | 96 | 8 | 每模块一个文件 |
| Iter5 | 109 | 16 | 每端点一个文件 |
| Iter6 | 27 | 6 | 模块级结构 |
| **Iter7** | **29 场景 / 36 测试** | **2** | **1 E2E链 + 28 单接口，含 param/boundary/error** |

## vs 基线提升

| 维度 | 权重 | 基线 | Iter6 | **Iter7** | Δ vs 基线 |
|------|------|------|-------|-----------|-----------|
| 用户体验 | 15% | 72 | 88 | **92** | **+20** |
| 自动化流程度 | 25% | 78 | 75 | **94** | **+16** |
| 人工干预度 | 10% | 65 | 93 | **95** | **+30** |
| 代码生成质量 | 25% | 70 | 93 | **92** | **+22** |
| 历史代码契合度 | 15% | 68 | 93 | **93** | **+25** |
| 场景理解与编排 | 10% | 75 | 81 | **92** | **+17** |
| **总分** | **100%** | **72** | **86.55** | **92.95 (历史 claim，当前审计不采纳为达成)** | **需 fresh run 重评** |

## 残余风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| **SM2 加密库 ARM64 兼容** | 🚨 高 | macOS ARM64 + Python 3.8 下 Segfault，pytest 可 collect 不可执行 |
| **模型依赖** | ⚠️ 中 | Wave 3 (代码生成) 需要强模型，mimo-v2.5-pro 偶有卡住现象 |
| **scenarios.json 无 confidence 字段** | 🔸 低 | 无法直接使用 confidence≥medium 做质量门控 |
| **测试输出路径** | 🔸 低 | 生成到 `tests/interface/`，项目 CLAUDE.md 建议 `testcases/` |
| **convention-fingerprint 未启用** | 🔸 低 | 按需 prompt 组装未激活，代码风格对齐依赖通用模板 |
