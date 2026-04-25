# Task 可视化集成设计

**日期：** 2026-04-13
**状态：** 已批准

---

## 概述

为 tide 的两个核心 Skill（`/tide` 和 `/using-tide`）加入 Task 工具（TaskCreate / TaskUpdate / TaskList），实现全流程进度实时可视化。

## 设计原则

1. 每个 Skill 在流程**最前面**批量 `TaskCreate` 所有主任务
2. 每个任务进入时 `TaskUpdate` → `in_progress`（触发 spinner + activeForm）
3. 完成时 `TaskUpdate` → `completed`
4. 子步骤写在 `description` 中，不单独建任务（两层混合粒度）
5. 错误处理：任务失败不标记 `completed`，保持 `in_progress`，由 Skill 自身的错误逻辑决定是否终止

## `/tide` 任务定义

流程开始时（预检阶段之前）批量创建 6 个任务：

| # | subject | activeForm | description（子步骤） |
|---|---------|-----------|---------------------|
| 1 | 预检与参数校验 | 校验 HAR 文件与项目配置 | 环境检查 → HAR 校验 → 认证头扫描 → 参数摘要输出 |
| 2 | [1/4] 解析与准备 | 解析 HAR 文件 | 启动 har-parser Agent → 启动 repo-syncer Agent（若有源码）→ 验证 parsed.json 完整性 → 输出验证摘要 → 检查点保存 |
| 3 | [2/4] 场景分析 | 分析测试场景 | 启动 scenario-analyzer Agent → 生成 scenarios.json → 展示确认清单（--quick 跳过）→ 验证摘要 → 检查点保存 |
| 4 | [3/4] 代码生成 | 生成测试代码 | 按模块并行启动 case-writer Agent ×N → py_compile 验证 → AST 检查 → 失败文件自动修复 → 验证摘要 → 检查点保存 |
| 5 | [4/4] 评审与交付 | 评审测试代码 | 启动 case-reviewer Agent → 5 维评审 → 自动修复 → 执行测试 → 生成执行报告 |
| 6 | 验收报告与归档 | 生成验收报告 | 汇总评审+执行报告 → 展示验收清单 → 发送通知（若配置）→ 归档会话 |

**生命周期示例：**

```
预检与参数校验    ████████████ completed
[1/4] 解析与准备  ████████████ completed
[2/4] 场景分析    ▶ 分析测试场景...  (spinner)
[3/4] 代码生成    ○ pending
[4/4] 评审与交付  ○ pending
验收报告与归档    ○ pending
```

### 插入位置

- 在"预检阶段"标题之前，新增"任务初始化"段落，包含 6 个 TaskCreate
- 在每个阶段的开头添加 `TaskUpdate → in_progress`
- 在每个阶段的检查点之后添加 `TaskUpdate → completed`

## `/using-tide` 任务定义

流程开始时批量创建 6 个任务（通用措辞，分支确定后动态更新）：

| # | subject | activeForm | description（子步骤） |
|---|---------|-----------|---------------------|
| 1 | 环境检测 + 智能分类 | 检测项目环境 | 工具版本检查 → 依赖检测与安装 → 重初始化检测 → 项目标志扫描 → 判定 existing_auto / new |
| 2 | 项目分析 | 分析项目特征 | 待分类后更新 |
| 3 | 确认与选择 | 确认分析结果 | 待分类后更新 |
| 4 | 源码仓库配置 | 配置源码仓库 | 收集仓库 URL → git clone → URL 前缀映射 → 写入 repo-profiles.yaml |
| 5 | 连接配置 | 配置连接信息 | Base URL → 认证方式与凭证 → 数据库（可选）→ 通知 Webhook（可选） |
| 6 | 脚手架生成 + 配置验证 | 生成项目脚手架 | 渲染 tide-config.yaml → 运行 scaffold.py → 生成 CLAUDE.md → smoke test → 输出初始化摘要 |

### 任务 ID 引用

Skill 文本中使用 `<task_N_id>` 占位符引用第 N 个 TaskCreate 返回的实际 ID。运行时 Claude 需将 TaskCreate 返回的 ID 存储并在后续 TaskUpdate 中使用。

### 分支确定后动态更新

任务 1 完成后已知分支类型，立即更新任务 2 和 3：

**分支 A（existing_auto）：**

```
TaskUpdate(taskId=2, subject="深度扫描（已有项目）", activeForm="扫描项目代码",
  description="启动 project-scanner Agent → 7 维度分析 → 写入 project-profile.json")

TaskUpdate(taskId=3, subject="7 维度确认", activeForm="确认扫描结果",
  description="项目架构 → 代码风格 → 鉴权方式 → 依赖工具链 → Allure 模式 → 数据管理 → 行业上下文，逐项确认")
```

**分支 B（new）：**

```
TaskUpdate(taskId=2, subject="行业调研（新项目）", activeForm="调研行业最佳实践",
  description="5 问行业画像收集 → 启动 industry-researcher Agent → 写入 research-report.json")

TaskUpdate(taskId=3, subject="方案推荐与试运行", activeForm="推荐技术方案",
  description="展示 2-3 个方案 → 用户选择 → 生成最小示例 → 确认代码风格")
```

### 插入位置

- 在"第零步"标题之前，新增"任务初始化"段落，包含 6 个 TaskCreate
- 在智能分类完成后添加分支动态更新逻辑
- 在每个步骤的开头添加 `TaskUpdate → in_progress`
- 在每个步骤结束时添加 `TaskUpdate → completed`

## Skill 文件变更

### `allowed-tools` 追加

```yaml
# tide/SKILL.md
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, TaskCreate, TaskUpdate, TaskList

# using-tide/SKILL.md
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, WebSearch, WebFetch, TaskCreate, TaskUpdate, TaskList
```

## README 更新

### 核心特性表格新增一行

```markdown
| **任务可视化** | 全流程进度实时可见，spinner 显示当前阶段，子步骤逐项追踪 |
```

### 工作流总览新增折叠段落

在 4 波次详解之后新增：

```markdown
<details>
<summary><b>任务可视化</b></summary>

Tide 在流程开始时创建任务清单，实时展示当前进度：

**`/tide` 执行时的任务面板：**

| 状态 | 任务 |
|------|------|
| ✅ | 预检与参数校验 |
| ✅ | [1/4] 解析与准备 |
| ▶ 分析测试场景... | [2/4] 场景分析 |
| ○ | [3/4] 代码生成 |
| ○ | [4/4] 评审与交付 |
| ○ | 验收报告与归档 |

每个任务包含子步骤描述，完成后自动标记。

</details>
```

## PLUGIN.md

无需变更。Task 工具是 Claude Code 内置能力，不需要额外声明。

## 不在范围内

- 不引入 `blockedBy` 依赖关系（波次本身就是串行的，依赖关系是隐式的）
- 不为每个 Agent 调用创建独立子任务
- 不修改现有的波次逻辑和 Agent 调度方式
