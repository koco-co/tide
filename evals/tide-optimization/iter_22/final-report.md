# Tide 最终报告

**日期**: 2026-05-13  
**HAR 文件**: `.tide/trash/20260509_152002_20260509_150847_172.16.122.52.har`  
**运行状态**: ⚠️ 部分通过（Assertion Gate 失败）

---

## 解析结果

| 指标 | 值 |
|------|------|
| 原始条目 | 31 |
| 去重后 | 28 |
| 服务模块 | `dassets`（资产）, `dmetadata`（元数据） |
| 匹配仓库 | `dt-center-assets`, `dt-center-metadata` |

## 生成文件

| 文件 | 场景数 | 状态 |
|------|--------|------|
| `testcases/scenariotest/assets/meta_data/tide_generated_assets_test.py` | 17 | ✅ 生成 |
| `testcases/scenariotest/assets/meta_data/tide_generated_metadata_test.py` | 11 | ✅ 生成 |

## 验证结果

| 检查项 | 结果 |
|--------|------|
| 格式检查 | ✅ 通过 |
| pytest 收集 | ✅ 28/28 测试可收集 |
| 场景验证 | ✅ 通过（28/28 confidence≥medium） |

## ❌ Assertion Gate 失败

所有 **28 个场景** 缺少 L4（数据模式验证）和 L5（业务逻辑验证）断言。

**已实现的断言层级**: L1（状态码）✅ · L2（响应结构）✅ · L3（业务成功码）✅  
**缺失的断言层级**: L4（数据模式深度检查）❌ · L5（业务逻辑验证）❌

## 端点清单

### daassets（17 个端点）
- `POST /dassets/v1/user/pageUsers`
- `POST /dassets/v1/datamap/recentQuery`
- `POST /dassets/v1/datamap/assetStatistics`
- `POST /dassets/v1/dataInventory/countDataSource`
- `POST /dassets/v1/datamap/hotword/list`
- `POST /dassets/v1/datamap/hotLabel/list`
- `POST /dassets/v1/datamap/listUsers`
- `POST /dassets/v1/datamap/label/list`
- `POST /dassets/v1/resourceCatalog/listCatalogByQuery`
- `POST /dassets/v1/datamap/queryDetail`
- `POST /dassets/v1/dataTableColumn/pageTableColumn`
- `POST /dassets/v1/dataTable/queryDetail`
- `POST /dassets/v1/label/listAllBindLabelByCondition`
- `POST /dassets/v1/datamap/resource/bindResourceRel`
- `POST /dassets/v1/dataTable/judgeIsMetaByTableId`
- `POST /dassets/v1/dataTable/hasParition`
- `POST /dassets/v1/dataTable/queryCreateTableSql`

### dmetadata（11 个端点）
- `POST /dmetadata/v1/syncTask/pageTask`
- `POST /dmetadata/v1/dataSource/listMetadataDataSource`
- `POST /dmetadata/v1/dataDb/realTimeDbList`
- `POST /dmetadata/v1/syncTask/realTimeTableList`
- `POST /dmetadata/v1/syncTask/add`
- `POST /dmetadata/v1/syncJob/pageQuery`
- `POST /dmetadata/v1/metadataApply/isSuperUser`
- `POST /dmetadata/v1/dataTable/getTableLifeCycle`
- `POST /dmetadata/v1/metadataApply/getApplyStatus`
- `POST /dmetadata/v1/dataSubscribe/getSubscribeByTableId`
- `POST /dmetadata/v1/dataTable/queryTablePermission`

## 建议后续步骤

1. **补充 L4 断言**: 为每个端点的 data 字段添加深度模式验证（结构、类型、嵌套约束）
2. **补充 L5 断言**: 根据业务语义添加跨字段/跨接口的业务规则验证
3. **集成认证和 fixture**: 接入项目的 BaseRequests/BaseCookies 进行真实 API 调用
4. **运行完整测试**: 在目标环境上执行 `uv run pytest testcases/scenariotest/assets/meta_data/tide_generated_assets_test.py`
