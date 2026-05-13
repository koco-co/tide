# Tide 最终报告

## 概要

- **HAR 源**: `.tide/trash/20260509_152002_20260509_150847_172.16.122.52.har`
- **解析**: 31 raw → 28 dedup endpoints
- **服务**: `dassets` (17), `dmetadata` (11)
- **生成模式**: Deterministic fallback

## 生成文件

| 文件 | 用例数 | 大小 |
|------|--------|------|
| `testcases/scenariotest/assets/tide_generated/tide_generated_dassets_test.py` | 17 | 23KB |
| `testcases/scenariotest/assets/tide_generated/tide_generated_dmetadata_test.py` | 11 | 15KB |

## 校验结果

| 检查项 | 状态 |
|--------|------|
| scenarios 生成 | ✅ 28 scenarios (100% confidence >= medium) |
| scenario_normalizer | ✅ 3 个重复 ID 已自动重命名 |
| scenario_validator | ✅ 28 endpoints / 28 scenarios / 2 workers |
| generation-plan | ✅ 2 workers (dassets / dmetadata) |
| pytest collect | ✅ 28/28 用例可收集，0 错误 |

## L1-L5 断言覆盖

- **L1**: 传输层 — status_code == 200
- **L2**: 合约层 — code/data/message 字段存在性校验
- **L3**: 业务层 — code == 1, success is True
- **L4**: 数据库校验 — 待补充 CRUD 闭环
- **L5**: UI 校验 — 待补充

## 状态文件

- `.tide/parsed.json` — HAR 解析结果
- `.tide/scenarios.json` — 场景定义
- `.tide/generation-plan.json` — 生成计划
- `.tide/artifact-manifest.json` — 产物清单
- `.tide/write-scope-snapshot.json` — 写范围快照

## 后续建议

- 补充 L4 数据库断言（数据血缘、订阅关系等）
- 补充 CRUD 闭环场景（如 syncTask add → pageTask 验证）
- 集成项目 BaseRequests/Cookies 进行真实 API 调用
