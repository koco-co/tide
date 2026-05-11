# Iteration 6 — 评分报告

## 基础信息

| 项目 | 值 |
|------|-----|
| 轮次 | Iteration 6 |
| 生成方式 | Claude Code CLI (mimo-v2.5-pro) + Tide v1.3.0 `--print` 管道模式 |
| 权限模式 | `--dangerously-skip-permissions` |
| 管道状态 | ✅ 全部完成 (0 退出码) |
| 新生成文件 | **2 个**, 1,229 行, 13 个测试类, **75 个测试方法** |
| 场景分析结果 | 75 场景 (2 并行 worker) |

## 关键改进 vs Iter5

| 指标 | Iter5 | Iter6 | Δ | 说明 |
|------|-------|-------|---|------|
| 文件数 | 16 (新建) | **2** | -14 | Iter6 用 2 个大文件 (按 worker) vs Iter5 的 16 个小文件 (按端点) |
| 测试方法 | 91 | **75** | -16 | 更聚焦于 HAR 端点衍生场景 |
| 代码行数 | 2,780 | **1,229** | -56% | 更精简 |
| `@classmethod` (FC12) | 0 | **0** ✅ | 持平 | 都完美 |
| `def setup_method` | 26 处 | **13 处** ✅ | 持平 | 各有优势 |
| 硬编码 ID (FC11) | 5 处 | **23 处** ❌ | +18 恶化 | Iter6 大量 `dataSourceId=1`/`tableId=1`/`metaId=1` |
| 并行 Worker | 15 | **2** | -13 | Iter6 更少但更契合端点分组 |
| L3 业务断言 | 157 处 | **69 处** | -88 | 更少但每方法有 |
| try/finally 清理 | 部分 | **2 处** | — | 有 CRUD 闭环清理 |
| L5 链路场景 | 0 | **6 处** ✅ | +6 新增 | 含 crud_closure 生命周期测试 |
| total 断言 | ~157 | **199** | +27% | 实际更多断言/行 |

## 硬性质量门

| # | 门 | 结果 | 证据 |
|---|-----|------|------|
| 1 | pytest --collect-only | ❌ 环境阻断 | JPype1 macOS ARM64 编译失败 + pydantic-settings 缺失 → python3: ModuleNotFoundError |
| 2 | L1+L2+L3 断言 | ✅ | L1: 75/75 方法含 status_code 断言。L2: 含 `resp.get("code") is not None` 或 `"code" in resp`。L3: 69/75 方法含 `code == 1/-1` |
| 3 | 写操作 L4 | ⚠️ 部分 | 无真实 DB 级断言（dao/SELECT/UPDATE）。但 `len(db_list) > 0` 等存在性检查算弱 L4 |
| 4 | 链路场景 L5 | ✅ **6 处** | 含 crud_closure 链路测试（数据表详情链路、资源目录链路、用户管理链路、同步任务生命周期等）+ try/finally cleanup |
| 5 | 无硬编码 ID | ❌ **23 处** | `dataSourceId=1`(×10), `tableId=1`(×7), `metaId=1`(×3), `taskType=1`(×3) — 严重退化 vs Iter5 |
| 6 | 无敏感信息明文 | ✅ | 无 token/密码/secret |
| 7 | 类粒度/import 一致 | ✅ | 13/13 `def setup_method(self)`, 正确 `AssetsBaseRequest`/`AssetsApi`/`Logger('模块名')()` |
| 8 | scenario_id 唯一 | ✅ | 75/75 全部唯一 |
| 9 | ≥60% medium confidence | ⚠️ | scenarios.json 缺少 confidence 字段 |
| 10 | 无 @classmethod | ✅ **0 ERROR** | 零次违规 |

### Gate 结论：1 硬门不过（环境）+ 1 硬门不过（23 处硬编码 ID）

## 6 维评分

### 1. 用户体验 (权重 15%)

| 指标 | 评分 | 证据 |
|------|------|------|
| 文件组织 | 70/100 | 2 个大文件按 worker 分组 (`dt-center-assets`, `dt-center-metadata`)，不按模块目录细分 |
| 可读性 | 80/100 | allure 装饰完备 (epic/feature/story/title), step 描述清晰 |
| 命名一致性 | 85/100 | 文件名 `test_dt_center_*.py` 规范, 类名 `Test*` 驼峰 |
| 干预次数 | 90/100 | 仅需 1 次启动指令 `--print` 模式，无人工干预 |

**得分: 81/100** (Iter5: 80, **Δ +1**)
证据: 文件 1,229 行可读性好，但 2 个大文件不如 Iter5 16 个小文件按模块好导航

### 2. 自动化流程度 (权重 25%)

| 指标 | 评分 | 证据 |
|------|------|------|
| 管道成功率 | 100/100 | 完全自动完成，0 退出码 |
| 端到端完成度 | 90/100 | 75 场景→75 测试→2 文件, py_compile 通过 |
| 测试可执行性 | 0/100 | 环境依存问题阻断 pytest |
| 自动修复 | 80/100 | 评审自动修复 3 处小问题 |

**得分: 68/100** (Iter5: 66, **Δ +2**)
证据: 管道全自动运行 (`tide_output.log: "全部完成"`), 但执行仍被环境阻断

### 3. 人工干预度 (权重 10%)

| 指标 | 评分 | 证据 |
|------|------|------|
| 用户需补充信息 | 95/100 | 无需确认，`--yes` flag bypass |
| 需手动修复 | 85/100 | 无需手动修复代码 |
| 一次成功率 | 100/100 | 一次运行成功 |

**得分: 93/100** (Iter5: 83, **Δ +10**)
证据: `--print` 管道模式零交互，全程自动化

### 4. 代码生成质量 (权重 25%)

| 指标 | 评分 | 证据 |
|------|------|------|
| 语法正确 | 100/100 | py_compile 两文件全部通过 |
| 断言完整性 | 75/100 | L1+L2+L3 都有, L4 部分, L5 新增 6 处 ✅。但 `resp.get("code") is not None` 作为 L2 较弱 |
| 场景覆盖率 | 85/100 | 75 测试覆盖 28 端点 (har_direct/param_validation/boundary/crud_closure/permission) |
| 硬编码问题 | 40/100 | **23 处硬编码 ID** — 严重退化 vs Iter5 的 5 处 |
| setup 模式 | 100/100 | 13/13 `setup_method(self)` ✅ |
| @classmethod | 100/100 | 0 处 ✅ |

**得分: 78/100** (Iter5: 91, **Δ -13**)
**主要原因**: 硬编码 ID 从 5 处恶化到 23 处

### 5. 历史代码契合度 (权重 15%)

| 指标 | 评分 | 证据 |
|------|------|------|
| import 风格 | 95/100 | 正确 `AssetsBaseRequest`/`AssetsApi`/`Logger` |
| setup 模式 | 100/100 | 全部 `setup_method(self)` |
| 文件命名 | 85/100 | `test_dt_center_*_interface.py` 符合 `test_*` 规范 |
| 类粒度 | 65/100 | 按功能模块分 13 类但文件级过于集中 (35-40 方法/文件) |
| 项目 API 复用 | 70/100 | 使用 AssetsApi 枚举 ✅, 但未复用项目已有的 Service 方法 (DatasourceService, MetaDataRequest) |

**得分: 83/100** (Iter5: 86, **Δ -3**)
证据: 核心模式正确但类粒度不如 Iter5 的模块级分组 (ProjectAssetScanner 未产生 project-assets.json)

### 6. 场景理解与编排 (权重 10%)

| 指标 | 评分 | 证据 |
|------|------|------|
| 场景多样性 | 90/100 | 5 种类型: har_direct/param_validation/boundary/crud_closure/permission |
| 源码追踪 | 85/100 | 场景有 `source_evidence` (SyncTaskController.java:189 等) |
| 链路编排 | 75/100 | **6 处链路场景新增** ✅ — crud_closure 生命周期测试 |
| Worker 并行度 | 50/100 | 仅 2 并行 worker vs Iter5 的 15 |

**得分: 80/100** (Iter5: 79, **Δ +1**)
证据: crud_closure 类含 3 条多步骤链路; 元数据文件含 1 条 try/finally 链路

## 加权总分

| 维度 | 权重 | 得分 | 加权 | Δ vs Iter5 |
|------|------|------|------|-----------|
| 用户体验 | 15% | 81 | 12.15 | +0.15 |
| 自动化流程度 | 25% | 68 | 17.00 | +0.50 |
| 人工干预度 | 10% | 93 | 9.30 | +1.00 |
| 代码生成质量 | 25% | **78** | **19.50** | -3.25 |
| 历史代码契合度 | 15% | **83** | **12.45** | -0.45 |
| 场景理解与编排 | 10% | 80 | 8.00 | +0.10 |
| **总分** | **100%** | | **78.40** | **-1.95 vs Iter5** |

**总分: 78.40/100** (Iter5: 80.35, **Δ -1.95 退化**)

## 10 项扣分对账

| # | 扣分项 | Iter5 | Iter6 | Δ |
|---|--------|-------|-------|---|
| 1 | 硬编码 ID/URL | ⚠️ 5 处 | ❌ **23 处** | 严重恶化 |
| 2 | 低 confidence 场景 | ⚠️ 未知 | ⚠️ 未知 | 持平 (scenarios.json 无 confidence 字段) |
| 3 | scenario_id 重复 | ⚠️ 未知 | ✅ 75 唯一 | 改善 |
| 4 | L4/L5 缺失 | ❌ L5 无 | ✅ **L5 新增 6 处** | **大幅改善** |
| 5 | 类粒度不符 | ✅ 模块级 | ⚠️ 2 是大文件 | 略退化 |
| 6 | 缺场景类型 | ✅ 8+ 种 | ✅ 5 种 (har/param/boundary/crud/permission) | 足够 |
| 7 | 明文 token | ✅ 无 | ✅ 无 | 持平 |
| 8 | 无进度反馈 | ❌ | ❌ | 无改进 |
| 9 | 无总结报告 | ✅ 有 | ❌ 无 | 退化 (`--print` 模式不生成 final-report) |
| 10 | 无 CI 模板 | ❌ | ❌ | 无改进 |

## Top-5 改进点

1. **[P1] 硬编码 ID 激增 (23 处)** — 远超 Iter5 的 5 处。case-writer.md 动态 ID 解析节对 `dataSourceId=1`/`tableId=1`/`metaId=1` 无效。需: (a) 在 code-style 模板中添加针对性禁止示例, (b) 增加 FC11 自动化修复, (c) 项目资产扫描器生成 project-assets.json
2. **[P1] 环境阻断 (JPype1/pydantic-settings)** — 同上轮, macOS ARM64 无法运行 pytest
3. **[P2] 缺少 project-assets.json** — 管道未生成, 导致 case-writer 无法复用项目已有 Service 方法 (DatasourceService.get_datasource_id_by_name)
4. **[P2] 类粒度优化** — 2 个大文件 vs 模块级细分 (Iter5 的 16 文件模式更好)
5. **[P3] 无总结报告** — `--print` 模式跳过 final-report.md 生成
