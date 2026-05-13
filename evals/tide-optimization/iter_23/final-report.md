# Tide 接口测试生成报告

**生成时间**: 2026-05-13
**HAR 源文件**: `20260509_152002_20260509_150847_172.16.122.52.har`
**模块**: 数据资产 (assets)
**环境**: 172.16.122.52

---

## 执行摘要

从 1 个 HAR 文件解析出 **28 个端点**，生成 **5 个 pytest 测试文件**，包含 **28 个唯一测试用例**（含 L1-L5 分层断言）。所有校验均通过。

## HAR 解析结果

| 指标 | 数量 |
|------|------|
| 原始请求 | 31 |
| 去重后端点 | 28 |
| dassets 端点 | 17 |
| dmetadata 端点 | 11 |

## 生成的测试文件

| 文件 | 场景数 | 类数 | 测试数 |
|------|--------|------|--------|
| `data_map/tide_generated_datamap_test.py` | 8 | 8 | 8 |
| `data_table/tide_generated_datatable_test.py` | 7 | 7 | 7 |
| `meta_data_sync/tide_generated_metadata_sync_test.py` | 4 | 4 | 4 |
| `platform_manage/tide_generated_platform_manage_test.py` | 4 | 4 | 4 |
| `meta_data/tide_generated_metadata_test.py` | 5 | 5 | 5 |

## 测试结构（L1-L5 断言）

每个测试用例包含完整的 5 层断言：
- **L1**: HTTP 状态码校验 (200)
- **L2**: 响应字段完整性 (code, success 等)
- **L3**: 业务状态码校验 (code=1, success=True)
- **L4**: 响应数据结构校验 (schema fields)
- **L5**: 业务响应一致性校验 (data字段、响应结构)

## 校验结果

| 检查项 | 结果 |
|--------|------|
| scenario_normalizer | ✅ 通过 |
| deterministic_case_writer | ✅ 5 文件生成，28 个 scenario_id 全局去重 |
| generated_assertion_gate | ✅ 28/28 场景无违规 |
| format_checker | ✅ 格式检查通过 |
| Python 语法检查 | ✅ 5/5 文件编译正常 |
| pytest 收集 | ✅ 28 个测试可收集 |
| pytest 执行 | ✅ 28 passed |
