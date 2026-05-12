# Tide 插件推广建议

## 2026-05-12 Iter9 审计更新

推广结论从 **Conditional Yes** 调整为 **Conditional / Hold**，直到完成一次 fresh Claude Code + Tide 生成并通过所有硬性质量门。

原因：
- Iter9 发现原 FC11 未拦截字符串数字业务 ID，现已修复 validator/prompt，但尚未重新跑 Claude 生成验证。
- 全量目标项目 `pytest --collect-only` 当前不是绿色；scoped generated tests collect-only 通过，但不能替代目标里写明的全量命令。
- Iter10 在用户授权后完成 fresh Claude 运行，但 `.tide/trash` 多 HAR 场景下静默选择了 `batch_orchestration_rules.har`，不是目标 SparkThrift HAR。
- Iter11 选中了正确 SparkThrift HAR，但 `metadata_direct_test.py` 生成的 21 个 `test_*` 方法位于非 `Test*` 类中，pytest 收集为 0。

推广前新增必做项：
1. 重新运行时必须传入精确 HAR 路径，例如 `.tide/trash/20260509_152002_20260509_150847_172.16.122.52.har`，不得只说 `.tide/trash`。
2. 新增的 `resolve_har_input` no-guess 规则必须随插件发布并重载。
3. 新生成文件必须通过 FC11：不得出现数字或数字字符串业务 ID，包括负向场景的不存在 ID。
4. 新生成文件必须通过 FC14：任何包含 `test_*` 方法的类名都必须以 `Test` 开头，并且每个文件都要单独跑 scoped `pytest --collect-only`。

Iter9 分支/PR：`codex/tide-iter-9-audit-quality-gates`，https://github.com/koco-co/tide/pull/1

## 结论: Conditional / Hold

**Tide v1.3.0 (Iter9/Iter10/Iter11 审计后)** — 暂不建议推广。Iter7 的 **92.95/100** 只能作为历史局部验证记录，不能作为硬性质量门全过的结论；Iter10 暴露多 HAR 静默误选，Iter11 暴露 pytest 类名收集漏检。

**当前阻断依据:**
- Iter9 audited score: **83.75/100**，未达 `>=90`。
- Iter7 生成文件存在 `dataSourceId: "43"`、`dataSourceId: "99999999"`、`tableId: "99999999"` 等 FC11 违规，现有 checker 已能检出。
- 全量目标项目 `pytest --collect-only` 当前失败，scoped collect 不能直接替代原始硬门。
- Iter10 的初始审批阻塞已被用户授权解除；原审批边界证据保留在 `evals/tide-optimization/iter_10/blockers.md`。
- Iter10 授权后 fresh run 分数为 **65.0/100**，因为生成了 batch orchestration suite 而非 SparkThrift metadata-sync suite；证据见 `evals/tide-optimization/iter_10/score.md`。
- Iter11 授权后 fresh run 分数为 **78.9/100**，正确 HAR 但 metadata 文件 0 tests collected；证据见 `evals/tide-optimization/iter_11/score.md`。

## 推广前必做

### 🔴 P0: 环境兼容性修复（阻断条件）

1. **SM2 加密库 ARM64 兼容** — macOS ARM64 + Python 3.8 下 Segmentation fault
   - 根因：`jaydebeapi` 依赖 `JPype1` 原生库，缺少 ARM64 wheel
   - 修复方案 A：Linux CI runner（推荐）
   - 修复方案 B：`conda install -c conda-forge jpype1`（conda 提供 ARM64 预编译）
   - 影响：pytest 可 **collect** 不可 **execute**（SM2 库 crash）

2. **pydantic-settings 依赖** — 项目使用 `pydantic v1` API
   - Tide 已通过 PYTHON_BIN 自动检测 `.venv/bin/python3` 解决 ✅
   - 环境迁移后需确认 `.venv/` 存在

### 🟡 P1: 代码质量改进

3. **scenarios.json 添加 confidence 字段** — 当前所有场景 confidence="unknown"
   - 改进：scenario-analyzer 输出时显式标注 high/medium/low
   - 便于更精确的质量门控

4. **测试输出路径对齐** — 当前 `tests/interface/` vs 项目 CLAUDE.md 建议 `testcases/`
   - 改进：tide-config.yaml 中设置 `test_dir: testcases` 或匹配项目主流规范

5. **convention-fingerprint 集成** — 按需 prompt 组装未激活
   - 改进：启用 convention-scanner → fingerprint → 按需加载 code-style 模块

### 🟢 P2: 低优先级

6. **CI 模板生成** — 自动生成 `.gitlab-ci.yml` 集成 pytest + allure
7. **进度通知** — 管道运行时通过 webhook 推送进度
8. **场景审计持久化** — scenarios.json 归档到 `output/reports/`
9. **test_granularity 默认值优化** — 当前默认 e2e_chain，对大 HAR 文件可降级为 hybrid

## 使用守则

### 环境要求

```
OS:      macOS (Intel) / Linux (推荐)
Python:  3.8+ (项目限制，需 .venv/)
Model:   mimo-v2.5-pro 或更强 (避免 deepseek-v4-flash)
CLI:     claude 2.1.129+ (需支持 --yes --non-interactive)
Plugin:  tide v1.3.0+, main @59b7450b (含所有 iter1-6 修复)
```

### 标准流程

```bash
# 1. 进入目标项目
cd ~/Projects/<target-project>

# 2. 确保 HAR 在 .tide/trash/ 下
#    确保 .venv/ 存在（PYTHON_BIN 自动检测用）

# 3. 无头模式自动生成（推荐）
claude "请使用 /tide .tide/trash/<har-file>.har --yes --non-interactive 生成接口测试套件"

# 4. 等待完成（约 5-15 分钟）
# 5. 检查 tests/ 或 testcases/ 下新生成的测试文件
```

### 验证清单

```bash
# 语法 + collect
python3 -m pytest tests/interface/test_*.py --collect-only -q

# 格式检查
PYTHONPATH=/path/to/tide:$PYTHONPATH uv run python3 -m scripts.format_checker tests/

# 硬编码 ID 检查
grep -nP '"[a-zA-Z]*[Ii][Dd]":\s*\d+' tests/interface/test_*.py  # 期望：无结果

# @classmethod 检查
grep -rn '@classmethod' tests/interface/test_*.py  # 期望：无结果
```

### 更新 Tide 插件

```bash
cd ~/Projects/tide
git pull origin main
rsync -av --exclude=".venv" --exclude=".git" --exclude="__pycache__" \
  --exclude="*.pyc" --exclude=".pytest_cache" --exclude=".DS_Store" \
  . ~/.claude/plugins/cache/tide/tide/1.3.0/
```

## 推广评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 代码质量 | ★★★★☆ **84%** | Iter9 审计发现字符串数字业务 ID 漏检，validator 已修复但未 fresh run 验证 |
| 自动化程度 | ★★★★☆ **80%** | Claude fresh run 需要外部服务和目标仓写入审批 |
| 可维护性 | ★★★★☆ **80%** | 需定期 rsync 插件缓存 |
| 用户友好 | ★★★★☆ **86%** | 历史上可一句话生成，但当前授权/清理流程仍有摩擦 |
| 稳定度 | ★★★☆☆ **65%** | 模型依赖 + SM2 ARM64 环境兼容 |

## 证据链

- **PR 链接**: `59b7450b` (main) — https://github.com/koco-co/tide
- **所有迭代证据**: `/Users/poco/Projects/tide/iter_*/score.md`
- **Iter7 证据**: `/Users/poco/Projects/dtstack-httprunner/tests/iter_7/score.md`
- **生成文件**: `tests/interface/test_metadata_sync.py` (401行) + `test_assets_datamap.py` (267行)
- **Tide 改进清单**:
  - `agents/case-writer.md` — 硬编码 ID 禁令
  - `prompts/code-style-python/00-core.md` — 业务 ID 硬编码禁令
  - `prompts/code-style-python/40-test-structure-dtstack.md` — setup_method 强制
  - `scripts/format_checker.py` — FC11→ERROR 级阻断
  - `skills/tide/SKILL.md` — PYTHON_BIN 自动检测 + 确定性 project-assets 回退
