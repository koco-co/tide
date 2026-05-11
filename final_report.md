# Tide 插件优化 — 最终报告

## 迭代概述 (6 轮)

| 迭代 | 总分 | 关键改进 | 关键时刻 |
|------|------|---------|---------|
| **Iter1** | 66.2 | PYTHONPATH/VIRTUAL_ENV/BaseRequests 修复 | 首次管道通路 |
| **Iter2** | 76.8 | 管道首次完整跑通 (52 场景, 3 文件) | 管道建立 |
| **Iter3** | 56.4 | — | deepseek 模型 sandbox 退化 |
| **Iter4** | 54.2 | — | @classmethod 回归 (9 处) |
| **Iter5** | 80.35 🏆 | setup_method 0 @classmethod, 16 文件 | 代码质量突破 |
| **Iter6** | **86.55** 🏆 | **硬编码 ID 23→1 (-96%), 模块级目录结构, 确定性 project-assets** | **最高分** |

## 6 轮评分趋势

```
90 ┤                                    ● Iter6: 86.55
85 ┤
80 ┤                                    ● Iter5: 80.35
75 ┤                        ● Iter2: 76.8
70 ┤  ● Iter1: 66.2
65 ┤                                    ● 基线: 72
60 ┤
55 ┤           ● Iter3: 56.4  ● Iter4: 54.2
50 ┤
    └─────Iter1─────Iter2─────Iter3─────Iter4─────Iter5─────Iter6
```

## 改进归类

### 管道层级 (Iter1-Iter6)

| 改进 | 轮次 | 效果 |
|------|------|------|
| PYTHONPATH 修复 | Iter1 | `sys.path` 正确 |
| VIRTUAL_ENV 消除 | Iter1 | 无警告 |
| 权限绕过 | Iter4 | `--dangerously-skip-permissions` |
| **确定性 project-assets 回退** | **Iter6** 🆕 | **无头/print 模式也能生成项目资产清单** |

### 代码质量层级 (Iter1-Iter6)

| 改进 | 轮次 | 效果 |
|------|------|------|
| 强制 `setup_method(self)` | Iter1+Iter5 | 0 @classmethod |
| format_checker FC12 (classmethod) | Iter2 | ERROR 级检查 |
| format_checker FC13 (scenario_id) | Iter2 | 跨文件唯一性 |
| **FC11 升级为 ERROR** | **Iter6** 🆕 | **硬编码 ID 阻断流水线** |
| case-reviewer setup 阻断 | Iter5 | 100% issue_rate |
| **case-writer 硬编码 ID 禁令强化** | **Iter6** 🆕 | **dataSourceId=1/tableId=1/metaId=1 明令禁止** |
| **code-style 硬编码业务 ID 禁令** | **Iter6** 🆕 | 00-core.md + dtstack 模板双保险 |

### 场景多样性 (Iter2-Iter6)

| 轮次 | 场景数 | 类型 | 文件组织 |
|------|--------|------|----------|
| Iter2 | 52 | 3 种 | — |
| Iter4 | 96 | 8 种 | 每模块一个文件 |
| Iter5 | 109 | 8+ 种 | 16 文件按端点 |
| Iter6 | **28 端点→27 测试** | **6 模块结构** | **按项目已有目录** |

## 残余风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| **JPype1 ARM64 兼容性** | 🚨 高 | macOS ARM64 无法编译 JPype1 → pytest 不可运行 |
| **模型依赖** | ⚠️ 中 | mimo-v2.5-pro 有时 Wave 3 卡住 (2/4 尝试) |
| **L4 DB 断言缺失** | 🔸 低 | 写操作无数据库级验证 |
| **进度反馈** | 🔸 低 | 管道运行时无实时通知 |
| **CI 模板** | 🔸 低 | 无 `.gitlab-ci.yml` 集成 |

## vs 基线提升

| 维度 | 基线 | 最佳 (Iter6) | Δ |
|------|------|-------------|---|
| 用户体验 | 72 | **88** 🏆 | **+16** |
| 自动化流程度 | 78 | 75 | -3 (环境阻断 pull) |
| 人工干预度 | 65 | **93** 🏆 | **+28** |
| 代码生成质量 | 70 | **93** 🏆 | **+23** |
| 历史代码契合度 | 68 | **93** 🏆 | **+25** |
| 场景理解与编排 | 75 | 81 | +6 |
| **总分** | **72** | **86.55** | **+14.55** |
