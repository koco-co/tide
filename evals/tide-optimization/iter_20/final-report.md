# Tide 接口测试生成报告

## 概要

- **HAR 文件**: `.tide/trash/20260509_152002_20260509_150847_172.16.122.52.har`
- **解析端点**: 28 个唯一端点（31 个原始条目，去重后 28 个）
- **生成测试**: 28 个 pytest 测试用例
- **pytest 收集**: 全部通过 ✅

## 生成文件

| 文件 | 测试数 | 模块 |
|------|--------|------|
| `testcases/scenariotest/assets/tide_generated/tide_generated_assets_test.py` | 17 | 资产模块（数据地图、数据目录、数据盘点、数据表详情） |
| `testcases/scenariotest/assets/tide_generated/tide_generated_metadata_test.py` | 11 | 元数据模块（同步任务、数据源、数据表生命周期等） |

## 工作流执行

1. ✅ HAR 解析 — 提取 28 个唯一 POST 端点
2. ✅ 场景生成 — `scenario_normalizer` 规范化 28 个场景
3. ✅ 场景校验 — `scenario_validator` 验证通过（所有场景 confidence=high）
4. ✅ 确定性测试生成 — `deterministic_case_writer` 写入 2 个测试文件
5. ✅ pytest 收集校验 — 28/28 测试可被 pytest 正常收集

## Artifacts

- `.tide/parsed.json` — HAR 解析后的端点数据（含请求/响应示例）
- `.tide/scenarios.json` — 28 个测试场景定义（含 L1-L5 断言计划）
- `.tide/generation-plan.json` — 2 个 worker 的分工计划

## 注意事项

- 测试用例引用了 `api/assets/assets_api.py` 中已有的 API 枚举
- 使用 `AssetsBaseRequest` 发送 POST 请求（遵循项目现有模式）
- 请求参数来源于 HAR 录制记录，部分 hardcoded 参数（如 tableId: 0）需要运行前按实际环境调整
- 建议在合适的环境执行实际运行验证：`.venv/bin/python3 -m pytest testcases/scenariotest/assets/tide_generated/ -v`
