# 跨项目优化计划：qa-flow + tide

> 启动日期：2026-04-13
> 涉及项目：`/Users/poco/Projects/qa-flow` (TypeScript/Bun) + `/Users/poco/Projects/tide` (Python/uv)

---

## 总览

两个项目各有独特优势，本计划通过双向吸收实现全面提升：

| 来源 | 优势 | 目标项目 |
|------|------|----------|
| tide | 分层断言 L1-L5 | → qa-flow |
| tide | Agent 模型分层 (Haiku/Sonnet/Opus) | → qa-flow |
| tide | Pydantic 强类型数据契约 | → qa-flow (Zod) |
| tide | 不可变设计 (frozen dataclass) | → qa-flow |
| tide | Wave 可恢复状态机 | → qa-flow |
| qa-flow | 插件 Hook 系统 | → tide |
| qa-flow | 偏好学习系统 | → tide |
| qa-flow | 格式检查规则集 FC01-FC11 | → tide |
| qa-flow | Playwright E2E | → tide |
| qa-flow | Handlebars 模板引擎 | → tide (参考) |

---

## Phase 0: 安全修复 (Critical)

### qa-flow

- [ ] **QF-S1** 修复 plugin-loader 命令注入漏洞
  - 文件：`.claude/scripts/plugin-loader.ts`
  - 问题：`{{url}}` 模板替换直接拼接到 shell 命令
  - 方案：用 `Bun.spawn()` / `child_process.spawn` 数组参数替代字符串拼接
  
- [ ] **QF-S2** 修复文件路径遍历漏洞
  - 文件：所有接受 `--file` 参数的脚本
  - 方案：添加 `path.resolve()` + 白名单目录校验

- [ ] **QF-S3** 修复 plugin 空环境变量绕过
  - 文件：`plugin-loader.ts` `isPluginActive()`
  - 问题：空字符串 `""` 通过 `length > 0` 检查
  - 方案：`value.trim().length > 0`

- [ ] **QF-S4** 修复 plugin 静默失败
  - 文件：`plugin-loader.ts:71-77`
  - 方案：错误时 `process.stderr.write()` 告警而非静默 continue

### tide

- [ ] **AF-S1** HAR parser YAML schema 校验
  - 文件：`scripts/har_parser.py:312-316`
  - 问题：`yaml.safe_load()` 无结构校验
  - 方案：添加 Pydantic model 校验 repo-profiles.yaml

- [ ] **AF-S2** repo_sync Git checkout 静默失败
  - 文件：`scripts/repo_sync.py:67-73`
  - 方案：分支不存在时 `git branch -a` 列出可用分支

---

## Phase 1: 架构统一 — 消除重复 & 共享基础

### qa-flow 架构优化

- [ ] **QF-A1** 提取共享类型定义
  - 创建：`.claude/scripts/lib/types.ts`
  - 内容：`TestCase`, `TestStep`, `SubGroup`, `Page`, `Module` 接口
  - 消除：`archive-gen.ts`, `xmind-gen.ts`, `history-convert.ts` 三处重复定义

- [ ] **QF-A2** 统一 plugin 加载逻辑
  - 合并：`plugin-loader.ts` 和 `config.ts` 中的重复扫描逻辑
  - 创建：`.claude/scripts/lib/plugin-utils.ts`

- [ ] **QF-A3** 创建 CLI 工具库
  - 创建：`.claude/scripts/lib/cli.ts`
  - 内容：`outputJson()`, `errorExit()`, `successExit()`
  - 统一所有脚本的 stdout/stderr 输出规范

- [ ] **QF-A4** 统一偏好加载模块
  - 创建：`.claude/scripts/lib/preferences.ts`
  - 消除：`archive-gen.ts` 和 `xmind-gen.ts` 重复的 regex 偏好解析

- [ ] **QF-A5** 提取测试用例工具函数
  - 创建：`.claude/scripts/lib/test-case.ts`
  - 内容：`countCases()`, `priorityMapping`, `tagInference()`

- [ ] **QF-A6** 统一 JSON 验证
  - 引入 Zod schema 校验中间格式 (IntermediateJson)
  - 替代现有的 type assertion

### tide 架构优化

- [ ] **AF-A1** 提取共享路径管理
  - 创建：`scripts/common.py`
  - 内容：`TidePaths` (统一 `.tide/`, `.repos/`, `.trash/` 管理)
  - 消除：`har_parser.py`, `state_manager.py`, `scaffold.py` 三处重复

- [ ] **AF-A2** 统一 JSON I/O
  - 添加到 `scripts/common.py`：`write_json_result()`, `read_json_model()`
  - 消除 5 处重复的 `model_dump_json()` 模式

- [ ] **AF-A3** 统一错误日志
  - 创建统一 logger 配置
  - 替代现有的混合 `logger.exception()` / `str(exc)` / `ValueError` 模式

---

## Phase 2: 配置 & 工具链修复

### qa-flow

- [ ] **QF-C1** 修复 Biome 废弃配置
  - 文件：`biome.json:31`
  - 问题：`experimentalScannerIgnores` 已废弃
  - 方案：迁移到 `files.includes` 的 `!!` 语法

- [ ] **QF-C2** 强化 Biome 规则
  - `noNonNullAssertion`: `off` → `warn`
  - `noUnusedVariables`: `warn` → `error`
  - `noUnusedImports`: `warn` → `error`

- [ ] **QF-C3** 补充 package.json 脚本
  - 添加：`lint`, `format`, `type-check`, `clean`, `ci`

- [ ] **QF-C4** 创建 workspace 清理脚本
  - 清理策略：`.temp/` 超过 7 天自动清理
  - 添加 `.DS_Store` 到 `.gitignore`

- [ ] **QF-C5** 创建 env schema 校验
  - 创建：`.claude/scripts/lib/env-schema.ts`
  - 启动时校验必需环境变量

- [ ] **QF-C6** 创建 Hook 注册表
  - 创建：`.claude/scripts/lib/hooks.ts`
  - 定义 `AVAILABLE_HOOKS` 常量，校验 plugin.json 引用的 hook 名

### tide

- [ ] **AF-C1** 修复 pyproject.toml pytest markers
  - 问题：`--strict-markers` 启用但无 `markers` 定义
  - 添加：`interface`, `scenario`, `unit` markers

- [ ] **AF-C2** 分离 Makefile 测试目标
  - 添加：`test-plugin` (插件自身测试) vs `test-generated` (生成项目测试)

- [ ] **AF-C3** 修复 `$PLUGIN_DIR` 环境变量
  - Agent 定义引用 `${PLUGIN_DIR}` 但无脚本设置
  - 在 `state_manager.py` 初始化时设置

- [ ] **AF-C4** scaffold 模板缺失校验
  - 文件：`scaffold.py:279-283`
  - `tide-config.yaml.j2` 缺失时静默跳过 → 改为警告

---

## Phase 3: 测试覆盖补全

### qa-flow

- [ ] **QF-T1** 补充 archive-gen 单元测试
  - 覆盖：JSON → Markdown 转换、标签推断、用例计数
  
- [ ] **QF-T2** 补充 xmind-gen 单元测试
  - 覆盖：JSON → XMind 结构构建、Topic 树递归

- [ ] **QF-T3** 添加插件集成测试
  - 测试 plugin hook 触发链路 (skill → plugin-loader → plugin.json → command)

- [ ] **QF-T4** state.ts 添加并发测试
  - 模拟多进程同时写入 state 文件

### tide

- [ ] **AF-T1** 补充 HAR parser 边界用例
  - `time_ms=0`、不同 status code 去重保留、text 类型 request body

- [ ] **AF-T2** 补充 scaffold 模板渲染测试
  - Jinja2 模板渲染结果断言、`.gitignore` 合并逻辑

- [ ] **AF-T3** 补充 state_manager Wave 顺序校验
  - Wave 2 在 Wave 1 未完成时应拒绝推进

- [ ] **AF-T4** 补充 notifier 网络异常测试
  - 超时、URL 校验、重试逻辑

---

## Phase 4: 功能互补 — tide → qa-flow

- [ ] **QF-F1** 引入 Agent 模型分层策略
  - 轻量任务 (格式检查、XMind 操作) → Haiku
  - 标准任务 (用例生成、代码分析) → Sonnet  
  - 复杂推理 (质量评审、架构分析) → Opus

- [ ] **QF-F2** 引入分层质量评估框架
  - 参考 tide L1-L5 断言分层
  - L1: 格式合规 (FC01-FC11 规则检查)
  - L2: 结构完整 (必填字段、步骤连贯性)
  - L3: 数据准确 (优先级、标签、预期结果合理性)
  - L4: 业务覆盖 (需求追溯、边界场景、异常路径)
  - L5: AI 增强 (隐含需求推断、交叉功能影响)

- [ ] **QF-F3** state.ts 添加文件锁
  - 引入 `proper-lockfile` 或 OS-level `flock`
  - 防止多进程并发写入冲突

- [ ] **QF-F4** Wave 可恢复机制增强
  - 参考 tide 的 Wave checkpoint + 归档
  - 每个节点 (transform/enhance/analyze/write/review/format-check) 可独立恢复

---

## Phase 5: 功能互补 — qa-flow → tide

- [ ] **AF-F1** 引入插件 Hook 系统
  - 创建：`scripts/hooks.py`
  - Hook 点：`wave1:parse`, `wave2:analyze`, `wave3:generate`, `wave4:review`
  - 支持自定义断言规则注入、自定义过滤器

- [ ] **AF-F2** 引入偏好学习系统
  - 创建：`.tide/preferences.yaml`
  - 学习内容：断言风格偏好、fixture scope 偏好、Allure 标签习惯
  - 第二次运行可跳过确认步骤

- [ ] **AF-F3** 引入格式检查规则集
  - 创建：`scripts/format_checker.py`
  - 规则：FC01 方法<50行、FC02 类<15方法、FC03 无未用导入、FC04 无硬编码、FC05 断言消息描述性、FC06 Pydantic 字段描述、FC07 类文档、FC08 fixture 文档、FC09 Allure 标签一致、FC10 无 print()、FC11 行长<120

- [ ] **AF-F4** Playwright E2E 测试生成 (长期)
  - 新增 Agent：`e2e-scenario-analyzer.md`, `e2e-writer.md`
  - 从 HAR + DOM 快照推断 UI 流程
  - 生成 Playwright 脚本

---

## Phase 6: Agent/Prompt 质量提升

### tide

- [ ] **AF-P1** 完善 har-parser Agent 错误恢复规范
  - 损坏 HAR 文件处理、大文件限制 (>100MB)、超时处理

- [ ] **AF-P2** scenario-analyzer 多语言支持
  - 当前仅覆盖 Java，需添加 TypeScript/Python/Go 支持
  - 添加性能预算（源码遍历深度上限）

- [ ] **AF-P3** 修复 prompt 交叉引用不一致
  - `assertion-layers.md` vs `code-style-python.md` 导入策略对齐
  - `scenario-enrich.md` 添加断言层映射表
  - `time_ms` 舍入规则明确化

- [ ] **AF-P4** case-writer async fixture 支持
  - 添加 pytest-async fixture 生成模式

- [ ] **AF-P5** case-reviewer 回滚策略
  - auto-fix 失败时回退到原始生成代码
  - 修复历史持久化到 `.tide/fix-history.json`

### qa-flow

- [ ] **QF-P1** 拆分 test-case-gen SKILL.md
  - 当前 768 行，拆分为：快速参考 + 高级工作流 + 故障排除

- [ ] **QF-P2** 统一日志分级
  - 引入 debug/info/warn/error 四级日志
  - JSON 输出走 stdout，日志走 stderr

---

## Phase 7: 文档 & 开发者体验

- [ ] **QF-D1** 模板选择矩阵文档
  - `bug-report.html.hbs` vs `bug-report-full.html.hbs` 区别说明

- [ ] **QF-D2** 插件开发指南
  - hook 可用列表、plugin.json schema、开发示例

- [ ] **AF-D1** 行业断言扩展指南
  - 如何添加新行业的断言规则

- [ ] **AF-D2** 生成项目最佳实践
  - 推荐的 conftest.py 结构、fixture 设计模式

---

## 执行策略

| Phase | 优先级 | 预估工时 | 依赖 |
|-------|--------|---------|------|
| Phase 0 | 🔴 Critical | 4h | 无 |
| Phase 1 | 🔴 High | 8h | 无 |
| Phase 2 | 🟠 Medium | 4h | 无 |
| Phase 3 | 🟠 Medium | 8h | Phase 1 |
| Phase 4 | 🟡 Normal | 10h | Phase 1 |
| Phase 5 | 🟡 Normal | 12h | Phase 1 |
| Phase 6 | 🟢 Low | 6h | 无 |
| Phase 7 | 🟢 Low | 4h | Phase 5, 6 |

**总计约 56h，建议按 Phase 0 → 1 → 2 → 3 → 4/5 并行 → 6 → 7 顺序执行。**
