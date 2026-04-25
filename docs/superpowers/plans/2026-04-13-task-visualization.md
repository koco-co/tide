# Task 可视化集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `/tide` 和 `/using-tide` 两个 Skill 加入 Task 工具（TaskCreate/TaskUpdate/TaskList），实现全流程进度实时可视化。

**Architecture:** 在每个 Skill 的 YAML frontmatter 中追加 Task 工具权限，在流程最前面新增"任务初始化"段落批量创建任务，在每个阶段的开头/结尾插入 TaskUpdate 状态转换指令。README 新增特性说明。

**Tech Stack:** Claude Code Plugin Skill（Markdown）、TaskCreate/TaskUpdate/TaskList API

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `skills/tide/SKILL.md` | 追加 Task 工具权限 + 插入任务初始化 + 各阶段状态转换 |
| Modify | `skills/using-tide/SKILL.md` | 追加 Task 工具权限 + 插入任务初始化 + 分支动态更新 + 各步骤状态转换 |
| Modify | `README.md` | 核心特性表格新增一行 + 工作流总览新增任务可视化折叠段落 |

---

### Task 1: `/tide` — 追加 allowed-tools 权限

**Files:**
- Modify: `skills/tide/SKILL.md:6`

- [ ] **Step 1: 修改 allowed-tools**

在 `skills/tide/SKILL.md` 第 6 行，将：

```yaml
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion
```

改为：

```yaml
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, TaskCreate, TaskUpdate, TaskList
```

- [ ] **Step 2: 验证 YAML frontmatter 格式**

打开文件确认 frontmatter（`---` 包裹的 YAML 块）仍然合法，`allowed-tools` 行在第 6 行，前后无多余空行或缩进错误。

- [ ] **Step 3: Commit**

```bash
git add skills/tide/SKILL.md
git commit -m "feat: tide Skill 追加 TaskCreate/TaskUpdate/TaskList 工具权限"
```

---

### Task 2: `/tide` — 插入任务初始化段落

**Files:**
- Modify: `skills/tide/SKILL.md:9-10`（在"预检阶段"标题之前）

- [ ] **Step 1: 在第 9 行（`---` 分隔线之后、`## 预检阶段` 之前）插入任务初始化段落**

在 `skills/tide/SKILL.md` 中，紧接文件头部描述段落（第 8 行 `采用四波次编排流水线：解析、分析、生成、评审。`）之后、`---` 分隔线之前，插入以下内容：

```markdown

---

## 任务初始化

在流程开始时，批量创建 6 个任务以可视化全流程进度：

```
TaskCreate(subject="预检与参数校验", activeForm="校验 HAR 文件与项目配置",
  description="子步骤：环境检查 → HAR 校验 → 认证头扫描 → 参数摘要输出")

TaskCreate(subject="[1/4] 解析与准备", activeForm="解析 HAR 文件",
  description="子步骤：启动 har-parser Agent → 启动 repo-syncer Agent（若有源码）→ 验证 parsed.json 完整性 → 输出验证摘要 → 检查点保存")

TaskCreate(subject="[2/4] 场景分析", activeForm="分析测试场景",
  description="子步骤：启动 scenario-analyzer Agent → 生成 scenarios.json → 展示确认清单（--quick 跳过）→ 验证摘要 → 检查点保存")

TaskCreate(subject="[3/4] 代码生成", activeForm="生成测试代码",
  description="子步骤：按模块并行启动 case-writer Agent ×N → py_compile 验证 → AST 检查 → 失败文件自动修复 → 验证摘要 → 检查点保存")

TaskCreate(subject="[4/4] 评审与交付", activeForm="评审测试代码",
  description="子步骤：启动 case-reviewer Agent → 5 维评审 → 自动修复 → 执行测试 → 生成执行报告")

TaskCreate(subject="验收报告与归档", activeForm="生成验收报告",
  description="子步骤：汇总评审+执行报告 → 展示验收清单 → 发送通知（若配置）→ 归档会话")
```

将每个 TaskCreate 返回的 ID 依次记为 `<task_1_id>` 到 `<task_6_id>`，后续阶段引用这些 ID 进行状态更新。
```

- [ ] **Step 2: 验证插入后的文件结构**

确认文件结构为：YAML frontmatter → 描述 → 任务初始化 → `---` → 预检阶段 → ...

- [ ] **Step 3: Commit**

```bash
git add skills/tide/SKILL.md
git commit -m "feat: tide 新增任务初始化段落 — 批量创建 6 个进度追踪任务"
```

---

### Task 3: `/tide` — 插入各阶段 TaskUpdate 状态转换

**Files:**
- Modify: `skills/tide/SKILL.md`（预检阶段、第一至四波次、验收报告各段）

- [ ] **Step 1: 预检阶段 — 开头插入 in_progress**

在 `## 预检阶段` 标题下方（`设置路径变量：` 之前）插入：

```markdown
将任务 1 标记为进行中：

```
TaskUpdate(taskId=<task_1_id>, status="in_progress")
```
```

- [ ] **Step 2: 预检阶段 — 结尾插入 completed**

在预检阶段最末尾（`打印已确认的输入信息：` 代码块之后、`---` 分隔线之前）插入：

```markdown
预检完成，标记任务 1：

```
TaskUpdate(taskId=<task_1_id>, status="completed")
```
```

- [ ] **Step 3: 第一波次 — 开头插入 in_progress**

在 `## 第一波次：解析与准备（并行）` 标题下方（`[1/4] 解析与准备 ▶ 开始...` 之前）插入：

```markdown
将任务 2 标记为进行中：

```
TaskUpdate(taskId=<task_2_id>, status="in_progress")
```
```

- [ ] **Step 4: 第一波次 — 结尾插入 completed**

在第一波次末尾（`[1/4] 解析与准备 ✓ 完成` 之后、`---` 分隔线之前）插入：

```markdown
标记任务 2 完成：

```
TaskUpdate(taskId=<task_2_id>, status="completed")
```
```

- [ ] **Step 5: 第二波次 — 开头插入 in_progress**

在 `## 第二波次：场景分析（顺序执行，交互式）` 标题下方（`[2/4] 场景分析 ▶ 开始...` 之前）插入：

```markdown
将任务 3 标记为进行中：

```
TaskUpdate(taskId=<task_3_id>, status="in_progress")
```
```

- [ ] **Step 6: 第二波次 — 结尾插入 completed**

在第二波次末尾（`[2/4] 场景分析 ✓ 完成` 之后、`---` 分隔线之前）插入：

```markdown
标记任务 3 完成：

```
TaskUpdate(taskId=<task_3_id>, status="completed")
```
```

- [ ] **Step 7: 第三波次 — 开头插入 in_progress**

在 `## 第三波次：代码生成（并行扇出）` 标题下方（`[3/4] 代码生成 ▶ 开始...` 之前）插入：

```markdown
将任务 4 标记为进行中：

```
TaskUpdate(taskId=<task_4_id>, status="in_progress")
```
```

- [ ] **Step 8: 第三波次 — 结尾插入 completed**

在第三波次末尾（`[3/4] 代码生成 ✓ 完成` 之后、`---` 分隔线之前）插入：

```markdown
标记任务 4 完成：

```
TaskUpdate(taskId=<task_4_id>, status="completed")
```
```

- [ ] **Step 9: 第四波次 — 开头插入 in_progress，拆分评审和验收**

在 `## 第四波次：评审 + 执行 + 交付（顺序执行，交互式）` 标题下方（`[4/4] 评审与交付 ▶ 开始...` 之前）插入：

```markdown
将任务 5 标记为进行中：

```
TaskUpdate(taskId=<task_5_id>, status="in_progress")
```
```

- [ ] **Step 10: 第四波次 — 评审+执行完成后，在验收报告之前切换任务**

在 `**验收报告**` 小标题之前（即 `读取 .tide/review-report.json 和 .tide/execution-report.json。` 之前）插入：

```markdown
标记任务 5 完成，将任务 6 标记为进行中：

```
TaskUpdate(taskId=<task_5_id>, status="completed")
TaskUpdate(taskId=<task_6_id>, status="in_progress")
```
```

- [ ] **Step 11: 流程最末尾 — 归档后标记任务 6 完成**

在文件最末尾（最终摘要代码块之后）插入：

```markdown
标记任务 6 完成：

```
TaskUpdate(taskId=<task_6_id>, status="completed")
```
```

- [ ] **Step 12: 验证完整文件**

通读整个文件，确认：
- 6 个 TaskCreate 在最前面
- 6 个 in_progress 分别在各阶段开头
- 6 个 completed 分别在各阶段结尾
- `<task_N_id>` 引用与创建顺序一致

- [ ] **Step 13: Commit**

```bash
git add skills/tide/SKILL.md
git commit -m "feat: tide 各阶段插入 TaskUpdate 状态转换 — in_progress/completed"
```

---

### Task 4: `/using-tide` — 追加 allowed-tools 权限

**Files:**
- Modify: `skills/using-tide/SKILL.md:6`

- [ ] **Step 1: 修改 allowed-tools**

在 `skills/using-tide/SKILL.md` 第 6 行，将：

```yaml
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, WebSearch, WebFetch
```

改为：

```yaml
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, WebSearch, WebFetch, TaskCreate, TaskUpdate, TaskList
```

- [ ] **Step 2: 验证 YAML frontmatter 格式**

确认 frontmatter 合法。

- [ ] **Step 3: Commit**

```bash
git add skills/using-tide/SKILL.md
git commit -m "feat: using-tide Skill 追加 TaskCreate/TaskUpdate/TaskList 工具权限"
```

---

### Task 5: `/using-tide` — 插入任务初始化段落

**Files:**
- Modify: `skills/using-tide/SKILL.md:8-10`（在"第零步"标题之前）

- [ ] **Step 1: 在文件头部描述段落之后、`---` 分隔线之前插入任务初始化段落**

在 `skills/using-tide/SKILL.md` 中，紧接头部描述段落（第 6 行 `最终生成项目脚手架和 CLAUDE.md。`）之后、`---` 分隔线之前，插入以下内容：

```markdown

---

## 任务初始化

在流程开始时，批量创建 6 个任务以可视化全流程进度。任务 2 和 3 使用通用措辞，在分支确定后动态更新：

```
TaskCreate(subject="环境检测 + 智能分类", activeForm="检测项目环境",
  description="子步骤：工具版本检查 → 依赖检测与安装 → 重初始化检测 → 项目标志扫描 → 判定 existing_auto / new")

TaskCreate(subject="项目分析", activeForm="分析项目特征",
  description="子步骤：待分类后更新（分支 A: project-scanner 深度扫描；分支 B: 行业画像收集 + industry-researcher 调研）")

TaskCreate(subject="确认与选择", activeForm="确认分析结果",
  description="子步骤：待分类后更新（分支 A: 7 维度逐项确认；分支 B: 方案推荐 + 试运行）")

TaskCreate(subject="源码仓库配置", activeForm="配置源码仓库",
  description="子步骤：收集仓库 URL → git clone → URL 前缀映射 → 写入 repo-profiles.yaml")

TaskCreate(subject="连接配置", activeForm="配置连接信息",
  description="子步骤：Base URL → 认证方式与凭证 → 数据库（可选）→ 通知 Webhook（可选）")

TaskCreate(subject="脚手架生成 + 配置验证", activeForm="生成项目脚手架",
  description="子步骤：渲染 tide-config.yaml → 运行 scaffold.py → 生成 CLAUDE.md → smoke test → 输出初始化摘要")
```

将每个 TaskCreate 返回的 ID 依次记为 `<task_1_id>` 到 `<task_6_id>`，后续步骤引用这些 ID 进行状态更新。
```

- [ ] **Step 2: 验证插入后的文件结构**

确认文件结构为：YAML frontmatter → 描述 → 任务初始化 → `---` → 第零步 → ...

- [ ] **Step 3: Commit**

```bash
git add skills/using-tide/SKILL.md
git commit -m "feat: using-tide 新增任务初始化段落 — 批量创建 6 个进度追踪任务"
```

---

### Task 6: `/using-tide` — 插入各步骤 TaskUpdate 状态转换 + 分支动态更新

**Files:**
- Modify: `skills/using-tide/SKILL.md`（第零步到第五步各段）

- [ ] **Step 1: 第零步 — 开头插入 in_progress**

在 `## 第零步：环境检测 + 智能分类` 标题下方（`### 环境检测` 之前）插入：

```markdown
将任务 1 标记为进行中：

```
TaskUpdate(taskId=<task_1_id>, status="in_progress")
```
```

- [ ] **Step 2: 第零步 — 智能分类判定后插入 completed + 分支动态更新**

在智能分类的 `根据 project_type 进入对应分支。` 之前插入：

```markdown
标记任务 1 完成：

```
TaskUpdate(taskId=<task_1_id>, status="completed")
```

根据 `project_type` 动态更新任务 2 和 3 的内容：

若 `project_type = "existing_auto"`：

```
TaskUpdate(taskId=<task_2_id>, subject="深度扫描（已有项目）", activeForm="扫描项目代码",
  description="子步骤：启动 project-scanner Agent → 7 维度分析 → 写入 project-profile.json")

TaskUpdate(taskId=<task_3_id>, subject="7 维度确认", activeForm="确认扫描结果",
  description="子步骤：项目架构 → 代码风格 → 鉴权方式 → 依赖工具链 → Allure 模式 → 数据管理 → 行业上下文，逐项确认")
```

若 `project_type = "new"`：

```
TaskUpdate(taskId=<task_2_id>, subject="行业调研（新项目）", activeForm="调研行业最佳实践",
  description="子步骤：5 问行业画像收集 → 启动 industry-researcher Agent → 写入 research-report.json")

TaskUpdate(taskId=<task_3_id>, subject="方案推荐与试运行", activeForm="推荐技术方案",
  description="子步骤：展示 2-3 个方案 → 用户选择 → 生成最小示例 → 确认代码风格")
```
```

- [ ] **Step 3: 分支 A 第一步 — 开头插入 in_progress**

在 `## 分支 A：已有自动化项目` 的 `### 第一步：深度扫描 Agent` 下方（Agent 调用之前）插入：

```markdown
将任务 2 标记为进行中：

```
TaskUpdate(taskId=<task_2_id>, status="in_progress")
```
```

- [ ] **Step 4: 分支 A 第一步 — 扫描完成后插入 completed + 第一步续开始**

在 `### 第一步续：交互式逐项确认` 标题下方插入：

```markdown
标记任务 2 完成，将任务 3 标记为进行中：

```
TaskUpdate(taskId=<task_2_id>, status="completed")
TaskUpdate(taskId=<task_3_id>, status="in_progress")
```
```

- [ ] **Step 5: 分支 A — 7 维度确认完成后插入 completed**

在 `分支 A 完成后，跳转到第三步。` 之前插入：

```markdown
标记任务 3 完成：

```
TaskUpdate(taskId=<task_3_id>, status="completed")
```
```

- [ ] **Step 6: 分支 B 第一步 — 开头插入 in_progress**

在 `## 分支 B：新项目 / 非自动化项目` 的 `### 第一步：行业画像收集` 下方插入：

```markdown
将任务 2 标记为进行中：

```
TaskUpdate(taskId=<task_2_id>, status="in_progress")
```
```

- [ ] **Step 7: 分支 B 第二步 — Agent 完成后切换任务**

在 `### 第二步续：方案呈现与选择` 标题下方插入：

```markdown
标记任务 2 完成，将任务 3 标记为进行中：

```
TaskUpdate(taskId=<task_2_id>, status="completed")
TaskUpdate(taskId=<task_3_id>, status="in_progress")
```
```

- [ ] **Step 8: 分支 B — 方案选择+试运行完成后插入 completed**

在 `分支 B 完成后，继续第三步。` 之前插入：

```markdown
标记任务 3 完成：

```
TaskUpdate(taskId=<task_3_id>, status="completed")
```
```

- [ ] **Step 9: 第三步（共用）— 开头插入 in_progress**

在 `## 第三步：源码仓库配置（两个分支共用）` 标题下方插入：

```markdown
将任务 4 标记为进行中：

```
TaskUpdate(taskId=<task_4_id>, status="in_progress")
```
```

- [ ] **Step 10: 第三步 — 结尾插入 completed**

在第三步末尾（`repo-profiles.yaml` 生成代码块之后、`---` 分隔线之前）插入：

```markdown
标记任务 4 完成：

```
TaskUpdate(taskId=<task_4_id>, status="completed")
```
```

- [ ] **Step 11: 第四步 — 开头插入 in_progress**

在 `## 第四步：连接配置（两个分支共用，深度按鉴权复杂度分级）` 标题下方插入：

```markdown
将任务 5 标记为进行中：

```
TaskUpdate(taskId=<task_5_id>, status="in_progress")
```
```

- [ ] **Step 12: 第四步 — 结尾插入 completed**

在第四步的 `### 配置文件写入` 段落末尾（分支 B 写入说明之后、`---` 分隔线之前）插入：

```markdown
标记任务 5 完成：

```
TaskUpdate(taskId=<task_5_id>, status="completed")
```
```

- [ ] **Step 13: 第五步 — 开头插入 in_progress**

在 `## 第五步：脚手架生成 + CLAUDE.md + 配置验证` 标题下方插入：

```markdown
将任务 6 标记为进行中：

```
TaskUpdate(taskId=<task_6_id>, status="in_progress")
```
```

- [ ] **Step 14: 第五步 — 初始化摘要之后插入 completed**

在文件最末尾（初始化摘要代码块 `下一步：执行 /tide <path-to.har>` 之后）插入：

```markdown
标记任务 6 完成：

```
TaskUpdate(taskId=<task_6_id>, status="completed")
```
```

- [ ] **Step 15: 验证完整文件**

通读整个文件，确认：
- 6 个 TaskCreate 在最前面
- 分支动态更新逻辑在第零步末尾
- 分支 A 和 B 各有独立的 in_progress/completed 对（任务 2 和 3）
- 共用步骤（第三步到第五步）各有 in_progress/completed 对（任务 4-6）
- `<task_N_id>` 引用与创建顺序一致

- [ ] **Step 16: Commit**

```bash
git add skills/using-tide/SKILL.md
git commit -m "feat: using-tide 各步骤插入 TaskUpdate 状态转换 + 分支动态更新"
```

---

### Task 7: README 更新

**Files:**
- Modify: `README.md:60-73`（核心特性表格）、`README.md:128`（波次详解 `</details>` 之后）

- [ ] **Step 1: 核心特性表格新增一行**

在 `README.md` 的核心特性表格中，在 `| **验证透明** |` 行之后插入：

```markdown
| **任务可视化** | 全流程进度实时可见，spinner 显示当前阶段，子步骤逐项追踪 |
```

- [ ] **Step 2: 工作流总览新增折叠段落**

在 `README.md` 的 `</details>`（4 波次详解的结束标签，约第 128 行）之后、`---` 分隔线之前插入：

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

**`/using-tide` 执行时的任务面板：**

| 状态 | 任务 |
|------|------|
| ✅ | 环境检测 + 智能分类 |
| ▶ 扫描项目代码... | 深度扫描（已有项目） |
| ○ | 7 维度确认 |
| ○ | 源码仓库配置 |
| ○ | 连接配置 |
| ○ | 脚手架生成 + 配置验证 |

每个任务包含子步骤描述，完成后自动标记。分支确定后任务名称自动更新。

</details>
```

- [ ] **Step 3: 验证 README 渲染**

确认两个 `<details>` 块不嵌套、表格语法正确、无多余空行导致渲染异常。

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README 新增任务可视化特性说明"
```
