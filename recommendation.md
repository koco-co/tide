# Tide 插件推广建议书

**评估日期**: 2026-05-11
**评估人**: Hermes Agent (模拟用户测试)
**Tide 版本**: v1.3.0 (SHA: 5f7180f, branch: fix/iter1-pythonpath-and-style)
**迭代次数**: 3 轮
**最佳得分**: 76.8/100 (Iter2)

---

## 结论: Conditional Yes (条件通过)

Tide 插件在正确配置下能够显著提升接口测试生成效率，但存在环境依赖风险。

---

## 推广前必做清单

### 🔴 必须修复（否则不推荐推广）

| # | 项目 | 严重度 | 说明 |
|---|------|--------|------|
| 1 | **锁定 case-writer 模型** | HIGH | case-writer.md 配置 `model: sonnet` 但实际由主模型执行。需要在 SKILL.md 中强制指定 `--model sonnet` |
| 2 | **prompt 模块选择逻辑** | HIGH | 无 convention-fingerprint.yaml 时自动选择 DTStack 特定模块组合(20-client-custom.md + 40-test-structure-dtstack.md)，而非默认通用模块 |
| 3 | **scenario_validator 兼容 uv** | HIGH | python3.12 + uv 环境下 `scenario_validator` 模块无法被发现 |
| 4 | **FC12 纳入 pipeline** | MEDIUM | 确保 format_checker 在 Wave 3 后自动运行，FC12 ERROR 拦截 @classmethod |

### 🟡 建议修复

| # | 项目 | 说明 |
|---|------|------|
| 5 | 增加 `@classmethod` 禁止到 `00-core.md` | 核心规范文件中直接禁止，确保所有 code-style 模块组合都覆盖 |
| 6 | case-writer write-file 路径权限 | 背景 Agent 的 sandbox 写权限需调整 |
| 7 | generation-plan 场景类型多样性 | 确保 scenario-analyzer 产出 param_validation/boundary/e2e_chain 类型 |

---

## 使用守则

### 前置条件

```bash
# 1. 确认 repo-profiles.yaml 存在
test -f dtstack-httprunner/repo-profiles.yaml && echo "OK" || echo "MISSING"

# 2. 确认 python3.12 可用
which python3.12

# 3. 确认 Claude Code 版本 >= 2.1
claude --version
```

### 推荐工作流

```bash
# 第一步：首次使用交互模式
cd <project>
claude
> /tide .tide/trash/*.har

# 第二步：后续使用无头模式（配置已验证通过后）
cd <project>
claude
> /tide .tide/trash/*.har --yes

# 第三步：生成后检查
cd <tide-plugin-dir>
uv run python3 -m scripts.format_checker <project>/testcases/scenariotest/
```

### 禁止操作

- ❌ 不要在 Tide pipeline 运行时手动修改 `.tide/` 目录文件
- ❌ 不要跳过 format_checker 检查直接合入
- ❌ 不要在 deepseek-v4-flash 模型下使用 case-writer（代码质量下降 30+ 分）

---

## 3 轮迭代 PR 链接

| 迭代 | 分支 | Commit | 主要改进 |
|------|------|--------|---------|
| Iter1 | `fix/iter1-pythonpath-and-style` | `9c46d82` | PYTHONPATH 注入, VIRTUAL_ENV 静音, setup_class 风格, AssetsBaseRequest 强制 |
| Iter2 | `fix/iter1-pythonpath-and-style` | `c493384` | FC12/FC13/FC04扩展, @classmethod 禁止强化 |
| — | — | — | 无需单独分支，Iter1/Iter2 在同一 feature 分支 |

---

## 证据链清单

| 轮次 | 文件 | 说明 |
|------|------|------|
| 基线 | — | 原始 Tide v1.3.0 配置 (HAR提交积分器+积分器+积分器+积分器+积分器) |
| Iter1 | `tide/docs/superpowers/plans/2026-05-11-iter1-tide-fixes.md` | 修复计划 |
| Iter1 | `tide/iter_1/score.md` | 66.2/100 评分+证据 |
| Iter2 | `tide/iter_2/score.md` | 76.8/100 评分+证据 |
| Iter2 | `dtstack-httprunner/.tide/review-report.json` | case-reviewer 产出 (11 处自动修复) |
| Iter2 | `tide/.tide.backup.iter_2/` | 迭代 2 生成的测试文件备份(3个, 1077行) |
| Iter3 | `tide/iter_3/score.md` | 56.4/100 评分+根因分析 |
| Iter3 | `dtstack-httprunner/testcases/scenariotest/assets/test_tide_har_metadata.py` | 迭代3生成文件 (316行) |
| Iter3 | `dtstack-httprunner/testcases/scenariotest/assets/test_tide_har_assets.py` | 迭代3生成文件 (470行) |
| 终版 | `tide/final_report.md` | 本报告 |
| 终版 | `tide/recommendation.md` | 本建议书 |
