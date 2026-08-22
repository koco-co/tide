# 生成并审查测试

## 阶段 1：生成候选

当前会话完整读取 `prompts/test-generator.agent.md`，直接按其中约束形成候选，不再委派第二个生成角色。生成输入只限：

- 用户已确认的 `scenario-plan.json` 中的场景，以及其 `plan_digest`；
- 脱敏 HAR 摘要；
- 已确认项目画像和项目规则；
- 用户确认的现有测试目录；
- 可复用 fixture、客户端和现有测试风格的只读证据。

当前会话只形成实际覆盖的场景编号与候选文件，不生成运行编号、环境资格、环境变量清单、生成状态或任何文件摘要。候选只能放在系统临时目录；不得写入项目或运行 pytest。不得以耗时为由中断后重试并把重试结果冒充首轮结果；候选无法收敛时本轮明确失败并清理临时目录。

调用 `scripts/write_run.py --bind-candidate --project-root <project-root> --candidate <system-temp>/candidate.json --scenarios <system-temp>/scenario-plan.json --confirmed-scenario-digest <用户确认摘要> --environment <confirmed-environment> --output <system-temp>/write-plan.json`。脚本负责复验场景摘要与当前画像和规则，强制候选场景编号属于已确认集合，生成运行编号，从画像唯一推导目标地址变量与必需运行时变量，并按场景覆盖机械确定生成状态；失败时不得转交审查角色。

## 阶段 2：委派结果审查

先使用 `scripts/write_run.py --validate-candidates`，传入目标项目、完整写入计划和确认测试目录。脚本按画像中已确认的目标 Python 版本解析候选，并通过 `scripts/candidate_checks.py` 拒绝原生断言、直接抛异常、吞异常、异常处理块内的 `pytest.fail`、会泄漏响应内容的项目 fixture 或辅助方法、固定首屏分页、未推进的分页游标、过早失效的清理标记、运行时对象输出、不安全失败消息、硬编码完整目标地址、显式开启自动重定向以及项目现有 HTTP 证据未支持的字面量查询参数；带逻辑标签的额外源码证据已在初始化三阶段完成同构 helper 检查，生成阶段不会把标签误当项目路径。如果项目存在 Ruff 配置，则只使用画像确认且具备对应锁文件的安全 runner 和项目既有 `.venv` Python，以隔离缓存、白名单环境、无修复参数检查系统临时候选；缺少完整 `.venv` 时直接阻断，禁止 Tide 自动创建、安装或修复。任何机械检查失败都必须修改候选、重新绑定计划并重新审查。

机械检查通过后，使用 `scripts/write_run.py --inspect-plan --plan <system-temp>/write-plan.json` 取得计划摘要。完整读取 `prompts/result-reviewer.agent.md`，再创建独立结果审查任务，提供确认场景、完整写入计划和相同证据来源。审查任务只返回语义结论并写入系统临时目录；结论为 `PASS` 后，调用 `scripts/write_run.py --bind-review --project-root <project-root> --plan <system-temp>/write-plan.json --review-candidate <system-temp>/review-candidate.json --test-dir <confirmed-test-dir> --output <system-temp>/review.json`，由脚本重新执行候选机械校验，并绑定当前计划摘要、校验摘要与完整文件范围。有多个确认测试目录时重复 `--test-dir`。

不得因耗时中断、催促、重启或重新委派审查角色；持续等待同一任务自然返回完成或真实失败。中断后的结果不得算作首轮审查证据。

- `verdict` 为 `FAIL`：按阻断问题修改候选，重新绑定计划并重新执行机械检查，再次委派结果审查。
- `verdict` 为 `PASS`：绑定审查结果后进入机械预检。
- 审查无法覆盖全部文件或场景：不得标记生成状态为 `PASS`。

角色审查不能替代脚本校验、已声明的静态检查，也不能证明测试真实通过。

## 阶段 3：机械预检

使用 `scripts/write_run.py --preflight`，同时传入写入计划与审查 JSON，验证运行编号、目标地址环境变量、已证实必需运行时环境变量名、输入散列、审查绑定、相对路径、扩展名、允许目录、目标不存在和内容大小。不得为预检提前写入目标项目。原样保留脚本返回的写入授权摘要；该摘要同时绑定计划、审查结果、目标项目身份和确认测试目录。

发现路径冲突时停止，展示冲突并让用户选择新的目标路径；不覆盖或自动合并。

## 阶段 4：写入确认门

向用户展示：

- 运行编号和生成状态；
- 当前写入授权摘要；
- 每个新文件的精确相对路径；
- 完整候选内容或可审查差异；
- 断言与证据映射；
- 未覆盖项、回滚范围和不会修改的文件。

用户确认前不得执行写入脚本。确认只授权该摘要所绑定的逐字一致文件、输入证据散列、审查结果、项目身份、测试目录、环境、目标地址环境变量与必需运行时环境变量名；任一内容变化后必须重新预检并确认。

完成信号：结果审查通过、机械预检通过、用户确认精确写入计划。
