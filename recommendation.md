# Tide 插件推广建议

## 结论: Conditional Yes ✅

**Tide v1.3.0 (Iter6 改进后)** 在 6 轮迭代优化后, 可在满足以下前提条件下推广使用。

**核心依据:**
- 代码生成质量: **93/100** ✅ — 动态 ID 查询, 0 @classmethod, 模块级目录结构
- 历史代码契合度: **93/100** ✅ — 与项目已有风格高度一致
- 硬编码 ID: **1 处 fallback** (vs 基线 5 处, Iter6 前 23 处)
- 人工干预度: **93/100** — 接近零交互

## 推广前必做

### 🔴 P0: 环境兼容性修复（阻断条件）

1. **JPype1 ARM64 兼容** — 在 macOS ARM64 上 `pytest --collect-only` 无法运行
   - 根因：`jaydebeapi` 依赖 `JPype1` 原生库, 缺少 ARM64 wheel
   - 修复方案 A：使用 `conda install -c conda-forge jpype1` (conda 提供 ARM64 预编译)
   - 修复方案 B：在 `conftest.py` 中延迟导入 jaydebeapi 相关模块
   - 修复方案 C：使用 Linux CI runner（推荐）

2. **pydantic-settings 依赖** — `config/configs.py` 使用 `from pydantic import BaseSettings` (v1 API)
   - 修复: `pip install pydantic-settings` → 将导入改为 `from pydantic_settings import BaseSettings`
   - 影响范围: 项目根 conftest.py, 非 tide 生成文件

### 🟡 P1: 代码质量改进

3. **消除残余 fallback ID** — `data_map_api_test.py:122` 中 `metaId: 0`
   - 改进: 在 case-writer.md 的常见违规模式中增加 `metaId` 示例

4. **L5 链路场景强化** — 当前仅 `data_map_api_test.py` 含多步骤链路
   - 改进: scenario-analyzer 识别 HAR 中 POST→GET 依赖关系生成 e2e_chain

### 🟢 P2: 低优先级

5. **CI 模板生成** — 自动生成 `.gitlab-ci.yml` 集成 pytest + allure
6. **进度通知** — 管道运行时通过 webhook 推送进度
7. **场景审计持久化** — scenarios.json 归档到 `output/reports/`

## 使用守则

### 环境要求

```
OS:      macOS (Intel 优先) / Linux (推荐)
Python:  3.8+ (项目限制)
Model:   mimo-v2.5-pro 或更强 (避免 deepseek-v4-flash)
CLI:     claude --dangerously-skip-permissions --print  (无头模式)
Plugin:  tide v1.3.0+, 含 Iter6 改进 (commit 74fc6ee)
```

### 标准流程

```bash
# 1. 进入目标项目
cd ~/Projects/<target-project>

# 2. 确保 HAR 在 .tide/trash/ 下

# 3. 无头模式自动生成
echo "HAR 在 .tide/trash 下，请生成接口测试" | \
  claude --dangerously-skip-permissions --print

# 4. 等待完成 (约 5-15 分钟)
# 5. 检查 testcases/ 下新生成的测试文件
```

### 验证清单

```bash
# 语法检查
python3 -m py_compile testcases/scenariotest/assets/meta_data/*_test.py

# 格式检查
PYTHONPATH=/path/to/tide:$PYTHONPATH uv run python3 -m scripts.format_checker testcases/

# 检查内容
grep -n '"tableId": [0-9]\|"dataSourceId": [0-9]' testcases/**/*_test.py  # 期望: 无结果
grep -n '@classmethod' testcases/**/*_test.py  # 期望: 无结果
```

### 更新 Tide 插件

```bash
cd ~/Projects/tide
git pull origin fix/iter6-harcoded-id-enforcement
cp -r agents/* ~/.claude/plugins/cache/tide/tide/1.3.0/agents/
cp -r prompts/* ~/.claude/plugins/cache/tide/tide/1.3.0/prompts/
cp -r skills/* ~/.claude/plugins/cache/tide/tide/1.3.0/skills/
cp scripts/format_checker.py ~/.claude/plugins/cache/tide/tide/1.3.0/scripts/format_checker.py
```

## 推广评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 代码质量 | ★★★★★ **93%** | 动态 ID 查询, 0 @classmethod, 模块级结构 |
| 自动化程度 | ★★★★☆ 75% | 管道全自动, 但 print 模式有时 Wave 3 卡住 |
| 可维护性 | ★★★★☆ 80% | 需维护 plugin cache 同步 |
| 用户友好 | ★★★★☆ 80% | 一次命令生成, 无需手动干预 |
| 稳定度 | ★★★☆☆ 65% | 模型依赖 (mimo 2/4 尝试卡住) + 环境依赖 |

## 推广后预期基线

| 维度 | 基线 | Iter6 | 环境修复后预期 |
|------|------|-------|----------------|
| 用户体验 | 72 | **88** | 88 |
| 自动化流程度 | 78 | 75 | **90** |
| 人工干预度 | 65 | **93** | 93 |
| 代码生成质量 | 70 | **93** | **95** |
| 历史代码契合度 | 68 | **93** | 93 |
| 场景理解与编排 | 75 | 81 | **85** |
| **总分** | **72** | **86.55** | **≥90** ✅ |

## 证据链

- **PR**: https://github.com/koco-co/tide/pull/new/fix/iter6-harcoded-id-enforcement
- **Commit**: `74fc6ee` — 4 文件, 78 行新增, 19 行删除
- **Score**: `/Users/poco/Projects/tide/iter_6/score.md`
- **Generated test files**: 6 文件, 565 行 (dtstack-httprunner)
- **Tide 改进**: case-writer.md + format_checker.py (FC11→ERROR) + SKILL.md (确定性 project-assets) + 00-core.md (硬编码禁令)
