# Tide 插件推广建议

## 结论: Conditional Yes ✅ (条件性推广)

**Tide v1.3.0** (Claude Code 接口测试生成) 在经过 5 轮迭代优化后, 可以在**满足以下前置条件**的前提下推广使用。

## 推广前必做

### 🔴 P0: 环境兼容性修复（阻断条件）

1. **SM2 加密库兼容** — 在 macOS ARM64 上 `pytest --collect-only` 触发 segfault
   - 根因：`gmssl` 或类似 SM2 原生库缺少 ARM64 编译版本
   - 修复：绑定平台特定版本, 或用纯 Python 实现替换
   - 影响：不修复则无法在任何 ARM Mac 上验证测试执行

2. **@classmethod 防护** — 已通过模板+reviewer 双重阻断, 但需确认 case-reviewer 升级到最新版 (含 Iter5 Section 6 检查)
   - 检查：`agents/case-reviewer.md` 是否包含 `Setup 模式检查（⚠️ 硬性阻断条件）`

### 🟡 P1: 代码质量改进

3. **硬编码 ID 消除** — 生成代码仍有 `dataSourceId=1`, `tableId=1`, `taskId=1`
   - 改进建议：在 case-writer.md 动态 ID 解析节中增加更多项目特定查询示例
   - 或：集成项目已有的 `DatasourceService.get_datasource_id_by_name()` 等查询方法

4. **确保场景元数据审计持久化** — 管道完成清理 .tide/ 后, scenarios.json 丢失
   - 改进：添加归档步骤, 将场景元数据保留到 `output/reports/` 或 git 追踪

### 🟢 P2: 体验改进

5. **添加 L5 链路场景生成** — 当前仅单接口测试
   - 可接入 case-writer 的 e2e_chain 模式, 但需要更精确的链路识别
6. **进度通知** — 管道运行时无进度推送, 用户需主动检查 tmux

## 使用守则

### 环境要求

```
OS:      macOS (Intel 优先) / Linux
Python:  3.8+ (项目限制)
Model:   mimo-v2.5-pro 或更强 (避免 deepseek-v4-flash)
CLI:     claude --dangerously-skip-permissions (bypass sandbox)
Plugin:  tide v1.3.0+, 含 Iter1-Iter5 修复
```

### 标准流程

```bash
# 1. 进入目标项目
cd ~/Projects/<target-project>

# 2. 确保 HAR 在 .tide/trash/ 下

# 3. 启动 Claude Code CLI
claude --dangerously-skip-permissions

# 4. 发送提示
"HAR 在 .tide/trash 下，请生成接口测试"

# 5. 确认 HAR 选择 + 隐私确认

# 6. 等待完成 (约 15-30 分钟, 取决于场景数)

# 7. 验证产出
# 检查 testcases/ 下新生成的测试文件
# 运行 pytest --collect-only 验证语法
# 运行 format_checker 检查代码质量
```

### 注意事项

1. **首次运行需要隐私确认** — HAR 数据发送到 AI 模型, 需用户确认
2. **有多 HAR 时需选择特定文件** — Tide 会询问处理哪个
3. **测试执行可能被环境阻断** — SM2 等平台依赖库可能失败, 不影响代码生成质量
4. **更新 Tide 插件** — 修改 `~/Projects/tide/` 后需同步到插件缓存:
   ```bash
   cp -r ~/Projects/tide/agents/* ~/.claude/plugins/cache/tide/tide/1.3.0/agents/
   cp -r ~/Projects/tide/prompts/* ~/.claude/plugins/cache/tide/tide/1.3.0/prompts/
   ```

## 推广评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 代码质量 | ★★★★☆ 85% | 核心模式正确, setup_method/L1-L4 断言完整 |
| 自动化程度 | ★★★★☆ 80% | 4 个 Wave 全自动, 仅需 2 次点击确认 |
| 可维护性 | ★★★☆☆ 60% | 需维护 plugin cache 同步, SM2 兼容性依赖 |
| 用户友好 | ★★★☆☆ 65% | 无进度反馈, 需 tmux 经验 |
| 稳定度 | ★★★☆☆ 70% | 模型依赖 (deepseek 退化), SM2 平台依赖 |

## 推广后预期基线

| 维度 | 基线 | 推广值 |
|------|------|--------|
| 用户体验 | 72 | **80** |
| 自动化流程度 | 78 | 66 (SM2 修复后 → **85**) |
| 人工干预度 | 65 | **83** |
| 代码生成质量 | 70 | **91** |
| 历史代码契合度 | 68 | **86** |
| 场景理解与编排 | 75 | **79** |
| **总分** | **72** | **80 (修复后 85+)** |
