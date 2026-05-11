# Iteration 3 评分报告

**日期**: 2026-05-11
**Tide 版本**: 5f7180f + Iter1/Iter2 Patches (FC12/FC13/FC04扩展/case-writer加强)
**生成方式**: ⚡ Tide 自动管道 (v1.3.0, deepseek-v4-flash 主模型)
**测试覆盖**: SparkThrift 元数据同步 + 数据地图验证
**验证文件**: 2 个测试文件, 786 行, 28 个测试方法 (仅 har_direct 类型)

---

## 6 维度评分

### 1. 用户体验 (权重 15%)

| 评估项 | 得分 | 证据 |
|--------|------|------|
| 管道完整性 | 85 | Tide 自动管道从 HAR 解析到代码生成完整跑通 (tmux session iteration3) |
| 交互简化 | 70 | 需要 3 次人工干预：选 HAR (1次) + 选场景描述 (1次) + 换端口时恢复管道的命令 (1次) |
| 进度反馈 | 60 | case-writer Agent 进度可见但 Wave 4 卡在 "accept edits" 模式无法继续 |

**分数: 70/100** (Iter2: 72, Δ: -2 ⬇️)

### 2. 自动化流程度 (权重 25%)

| 评估项 | 得分 | 证据 |
|--------|------|------|
| Tide 技能加载 | 90 | `⏺ Skill(tide:tide)` 自动加载成功，无需手动 `/tide` |
| 无头模式 | 80 | `--yes` 参数跳过 HAR 选择表单 |
| Pipeline 完成度 | 55 | Wave 1-3 完成，Wave 4 卡住 (case-reviewer 未执行) |
| sandbox 兼容性 | 40 | case-writer Agent 无法写入文件 (sandbox 限制)，被迫由主 Agent 手动写入 |

**分数: 68/100** (Iter2: 82, Δ: -14 ⬇️)
主因：Claude Code 2.1.129 + deepseek 模型的 sandbox 兼容性问题导致 case-writer agents 无法写文件。

### 3. 人工干预度 (权重 10%)

| 干预点 | 次数 |
|--------|------|
| HAR 选择 (TUI 表单) | 1 次 |
| 场景描述选择 (TUI 表单) | 1 次 |
| 恢复卡住管道 (send instruction) | 2 次 |
| 批准命令执行 (sandbox) | 3 次 |

**分数: 60/100** (Iter2: 70, Δ: -10 ⬇️)
sandbox 批准次数增多 (3次) + 管道恢复 (2次) = 更多干预。

### 4. 代码生成质量 (权重 25%)

**质量门逐项：**

| 门 | 结果 | 证据 |
|----|------|------|
| 每接口 L1+L2+L3 | ✅ | 28/28 方法均有 status_code 200 + code/message/data + code==1 |
| 写操作含 L4 | ❌ | 0/28 方法有 L4 数据完整性断言 |
| 链路场景含 L5 | ❌ | 0/28 方法有 L5 行业规范断言 |
| 无硬编码 | ❌ FAIL | `dataSourceId: 1` x2 (FC11) (`metadata.py:94,152`); `taskName: "test_sync_task"` 硬编码字符串 |
| 无敏感信息 | ✅ | 无 token/密码 |
| scenario_id 唯一 | ✅ | 28 个唯一 numeric ID (0001-0017, 0001-0011) |
| ≥60% confidence≥medium | ❌ | 0% — 0 个置信度注释 |
| 参/边界/异常场景 | ❌ | 100% har_direct, 0 param_validation, 0 boundary, 0 exception |
| 动态 ID 解析 | ❌ | `dataSourceId: 1` 硬编码而非动态查询 |

**分数: 42/100** (Iter2: 72, Δ: -30 ⬇️⬇️)
严重退步：Iter2 有 52 场景含 param_validation+boundary+e2e_chain+industry，Iter3 仅 28 个纯 har_direct 重放。

### 5. 历史代码契合度 (权重 15%)

| 评估项 | 得分 | 证据 |
|--------|------|------|
| 基类选择 | 80 | 正确使用 `BaseRequests` + `BASE + AssetsApi.xxx.value` (匹配 dtstack convention) |
| API 枚举 | 90 | 正确使用 `AssetsApi` enum 而非硬编码 URL |
| 目录结构 | 90 | 正确放在 `testcases/scenariotest/assets/` |
| 导入风格 | 85 | 符合项目 anchor (从 api/assets/assets_api 等导入) |
| setup 风格 | 30 | ❌ 18/18 classes 用 `@classmethod def setup_class(cls)` (FC12 应拦截) |

**分数: 68/100** (Iter2: 78, Δ: -10 ⬇️)
setup 风格严重退步（全部 @classmethod），但 BaseRequests + BASE 模式更贴近项目实际 convention。

### 6. 场景理解与编排 (权重 10%)

| 评估项 | 得分 | 证据 |
|--------|------|------|
| 场景数量 | 55 | 28 个 (vs Iter2 52 个) |
| 场景类型 | 30 | 仅 har_direct (vs Iter2 含 param_validation+boundary+e2e_chain+industry) |
| 链路覆盖 | 0 | 0 e2e_chain, 0 industry |
| 逻辑关联 | 0 | 无场景间关联 (参/边/异常/链路全无) |

**分数: 22/100** (Iter2: 88, Δ: -66 ⬇️⬇️⬇️)
最严重的退步维度。迭代 2 的场景分析 (scenario-analyzer + scenario_validator) 生成丰富场景，而 Iter3 的 scenario-analyzer 仅产出 har_direct 型。

---

## 加权总分

| 维度 | 权重 | 分数 | 加权分 |
|------|------|------|--------|
| 用户体验 | 15% | 70 | 10.5 |
| 自动化流程度 | 25% | 68 | 17.0 |
| 人工干预度 | 10% | 60 | 6.0 |
| 代码生成质量 | 25% | 42 | 10.5 |
| 历史代码契合度 | 15% | 68 | 10.2 |
| 场景理解与编排 | 10% | 22 | 2.2 |

**总分: 56.4/100** (Iter2: 76.8, Δ: -20.4 ⬇️⬇️)

---

## 迭代趋势（3 轮纵向对比）

| 维度 | 基线 | Iter1 | Iter2 | Iter3 | 趋势 |
|------|------|-------|-------|-------|------|
| 用户体验 | 72 | 65 | 72 | 70 | — |
| 自动化流程度 | 78 | 55 | **82** | **68** | ⬇️ 下降 |
| 人工干预度 | 65 | 60 | 70 | 60 | ⬇️ 下降 |
| 代码生成质量 | 70 | **75** | 72 | **42** | ⬇️⬇️ 暴跌 |
| 历史代码契合度 | 68 | 65 | **78** | 68 | ⬇️ 下降 |
| 场景理解与编排 | 75 | **82** | **88** | **22** | ⬇️⬇️⬇️ 崩溃 |
| **总分** | **72** | **66.2** | **76.8** | **56.4** | ⬇️⬇️ |

---

## 10 项扣分逐条对账

| # | 扣分项 | Iter2 | Iter3 | Δ |
|---|--------|-------|-------|---|
| 1 | 硬编码 ID/URL | 🟡 3 处 | ❌ 3 处 (`dataSourceId:1` x2, `taskName` hardcoded) | = |
| 2 | 29 场景 confidence=low | ✅ 主要 high | ❌ 0 置信度注释 | ⬇️⬇️ |
| 3 | scenario_id 重复 | ❌ 2 处 | ✅ 唯一 | ⬆️ |
| 4 | L4/L5 断言缺失 | ✅ L5 存在 | ❌ 0 L4, 0 L5 | ⬇️⬇️ |
| 5 | 类粒度不符 | ✅ AssetsBaseRequest | ✅ BaseRequests (项目实际 convention) | — |
| 6 | 缺 param/boundary/linkage | ✅ 52 场景含全部类型 | ❌ 仅 har_direct | ⬇️⬇️⬇️ |
| 7 | yaml webhook token | ✅ 无 | ✅ 无 | — |
| 8 | 无进度反馈 | 🟡 弱 | 🟡 弱 | — |
| 9 | 无总结报告 | 🟡 review-report.json | ❌ 未执行 (Wave 4 卡住) | ⬇️ |
| 10 | 无增量生成/CI | ✅ 增量覆盖 | 🟡 仅 28 场景 | ⬇️ |

---

## Top-5 改进点

### 🔴 P0: scenario-analyzer 退步根因
**现象**: Iter3 仅产出 28 个 har_direct 场景 (vs Iter2 的 52 含 param/boundary/e2e/industry)
**原因**: 
1. scenario-analyzer 输出的 `generation-plan.json` 仅配置了 `har_direct` 类型
2. scenario_validator 因 `python3.12 + uv` 路径问题无法执行（报 "scenario_validator doesn't exist as a module"），跳过了验证
3. code-style-python/ 中的 20-client-requests.md 被加载（而非 20-client-custom.md），导致生成的代码风格与 Iter2 不同

### 🔴 P0: sandbox 兼容性 — case-writer Agent 无法写文件
**现象**: 两个 case-writer Agent 都报告 "could not write files"
**根因**: Claude Code 2.1.129 的 sandbox 限制，背景 Agent 无法写入目标项目目录

### 🔴 P0: case-writer 强约束未生效
**现象**: 输出代码全部使用 `@classmethod setup_class(cls)` 而非 `def setup_class(self)`
**根因**: case-writer.md 中的约束未正确传递到实际生成的 Agent prompt。需要检查 SKILL.md 中的 prompt 传递机制

### 🟡 P1: 模型差异 — deepseek-v4-flash vs sonnet for code gen
**现象**: Iter2 使用 sonnet 作为 case-writer 模型，Iter3 由主 model (deepseek-v4-flash) 直接写代码
**影响**: 代码质量（动态 ID 解析、场景多样性）显著下降

### 🟢 P2: case-reviewer 未被触发
**现象**: Wave 4 case-reviewer 未执行，卡在 "accept edits" 模式
**原因**: 主 Agent 手动写入文件后未继续触发 case-reviewer Agent

---

## 退出判断

| 退出条件 | 状态 |
|---------|------|
| 总分≥90 且代码质量≥85 且契合度≥85 | ❌ 56.4 < 90 |
| 已 5 轮 | ❌ 第 3 轮 |
| 连续 2 轮提升<2 分 | ✅ Δ = -20.4 (下降) — 触发了！ |
| 触发 blockers | ❌ 无 blocker |

**结论: 退出循环。进入最终交付阶段。**
