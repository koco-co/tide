# Tide 插件推广建议

## 结论: Conditional Yes ✅ (Iter7 已达目标)

**Tide v1.3.0 (Iter7 验证后)** — 总分 **92.95/100**，7 轮迭代从基线 72 提升至 **≥90**，满足推广条件。

**核心依据:**
- 总分: **92.95/100** ✅ — 超过 ≥90 目标
- 代码生成质量: **92/100** ✅ — 动态 ID 查询、Allure 注解、param/boundary/error tests
- 历史代码契合度: **93/100** ✅ — AssetsApi 枚举模式、MetaDataRequest、setup_method
- 硬编码 ID: **0 处** ✅ — 全部动态发现 (`self.ds_id` / `_resolve_table_id_helper()`)
- 零人工干预: **95/100** — `--yes --non-interactive` 全自动流水线
- 无头模式: **36/36 pytest collect-only 通过** ✅

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
| 代码质量 | ★★★★★ **92%** | 动态 ID 查询、Allure 注释、param/boundary/error |
| 自动化程度 | ★★★★★ **94%** | --yes --non-interactive 全自动，无需交互 |
| 可维护性 | ★★★★☆ **80%** | 需定期 rsync 插件缓存 |
| 用户友好 | ★★★★★ **92%** | 一句"HAR在trash下"得36个测试 |
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
