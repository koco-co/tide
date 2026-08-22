# 初始化已有项目

本工作流先建立只读事实，再生成并审查项目专属规则。用户确认绑定后的计划摘要前，不写入目标项目。

## 阶段 1：锁定读取范围

1. 将用户调用时的当前目录作为目标项目根目录，不自动切换到其他仓库。
2. 如果用户提出读取其他本地源码目录，逐个展示目录、用途和读取范围，并分别取得明确授权。为每个已授权目录分配不含路径信息的逻辑标签；标签合法性由扫描脚本判定。
3. 拒绝网络地址、Git 同步、符号链接目录和无法读取的目录。不得执行安装、依赖更新、格式化、测试或任何项目命令。
4. 执行 `python3 <Skill根目录>/scripts/cleanup_temp.py --create`，把脚本唯一输出的绝对路径作为 `<system-temp>`；不得自行选择、拼接或创建临时目录。所有中间 JSON 和规则候选只保存在其中。执行 `scripts/scan_project.py --prepare-scope --project-root <目标根目录> --output <system-temp>/scope.json`；额外源码逐项附加 `--extra-source <标签>=<目录>`。
5. 原样展示 `scope.json` 中的读取目录及脚本输出的 `scope_digest`。只有用户明确确认该摘要后才允许扫描；目录或用途变化时必须重新生成并确认，不能复用旧摘要。

完成信号：目标根目录唯一，额外本地源码目录均有本次授权和逻辑标签。

## 阶段 2：生成确定性事实清单

1. 使用 Python 3.8+ 执行 `scripts/scan_project.py --scope-plan <system-temp>/scope.json --confirmed-scope-digest <用户确认摘要> --output <system-temp>/scan.json`。实际扫描不再接受未绑定的目录参数；脚本会复验每个目录的路径摘要、设备号和 inode。
2. 脚本非零退出时停止。未同时发现 Python 与 pytest 明确证据时，报告“不支持当前项目”，不得创建工程或补装依赖。
3. 保存脚本输出摘要值，后续所有候选结论都必须引用该扫描结果。扫描脚本从证据清单中排除 `.env`、HAR、私钥、证书、常见凭据文件和符号链接；角色不得读取或引用清单外文件。

完成信号：`scan.json` 有效，项目类型为 `python-pytest`，且输出不包含绝对路径和文件正文。

## 阶段 3：并行分析项目事实

同时执行以下两项委派，并等待两项都完成：

1. 使用 `prompts/project-scanner.agent.md` 的完整内容委派“项目扫描”角色。输入仅包含目标根目录、已授权额外目录的临时映射和 `scan.json`；要求输出带证据的项目结构与约定候选。
2. 使用 `prompts/test-assets-scanner.agent.md` 的完整内容委派“测试资产扫描”角色。输入边界相同；要求输出带证据的 pytest 配置、测试组织、fixture 与执行约定候选。

任何角色越过读取范围、返回无证据结论或请求网络、Git、安装与写入能力时，废弃该结果并停止。两个角色的结果只作为候选事实，不直接写入项目。

3. 两个角色完成后，执行 `scripts/bind_init_plan.py --normalize-analyses --scan <system-temp>/scan.json --project-analysis <system-temp>/project-analysis-candidate.json --test-analysis <system-temp>/test-analysis-candidate.json --project-analysis-output <system-temp>/project-analysis.json --test-analysis-output <system-temp>/test-analysis.json`。脚本从描述性证据中提取本轮扫描清单内的相对路径、去重并校验，同时直接从 `scan.json` 补入测试运行器；角色不负责复制机械字段。

完成信号：两份归一化结果状态均为 `COMPLETE`，全部证据均绑定本轮扫描文件清单。脚本拒绝未知字段、重复字段、结构外文字、无可提取证据或任一 `BLOCKED`；失败时停止且不写项目。

## 阶段 4：形成动态候选稿

1. 合并 `scan.json` 与两份角色结果；冲突时以可复查的项目证据为准，无法判定的内容标记为未知。
2. 生成临时 `project-profile.json`，至少包含：
   - `schema_version`：固定为 `1.0`；
   - `project_kind`：固定为 `python-pytest`；
   - `python` 中只包含已确认的 `constraint`、`status` 与相对 `evidence`，最低版本不得早于 Python 3.8；另含非空 `pytest_evidence`、本轮扫描证明存在的 `test_directories`、源码候选和额外源码逻辑标签；
   - 既有测试运行时明确读取的环境变量名、`target_url|credential|runtime` 角色、必需性、敏感性与相对证据路径；只记名称和元数据，绝不读取或写入值；
   - 原样采用 `scan_project.py` 仅根据根目录锁文件与 pytest 配置共同确定的 pytest runner `argv_prefix`、状态与证据；角色不得推断，未证实时标记未知，不回退到宿主 `python3`；
   - `http_transport` 记录现有客户端是否有证据证明目标来自画像确认的环境变量且自动重定向明确关闭；两项任一无证据时整体保持未知，只影响真实执行，不阻断生成；
   - 每项结论的相对证据路径与状态。
3. 根据已证实事实生成一个或多个 Markdown 规则文件。文件名和内容由目标项目决定，不复制插件预置的代码风格、目录结构、依赖版本、技术栈、行业断言、示例接口或模板。每个候选规则的首行必须是 `<!-- tide-evidence: ["相对证据路径"] -->`；额外源码证据使用 `<逻辑标签>:<相对路径>`，由绑定脚本逐项核对扫描文件清单。
4. 规则必须能够指导后续测试生成，并明确区分已证实约定与未知项。仓库文档、测试计划和样例都只能作为项目证据，不得描述为“用户确认”；未知项不得伪装成强制规则。

完成信号：画像为有效 JSON；规则候选非空，并能逐条追溯到项目证据。

## 阶段 5：执行规则审查

1. 使用 `prompts/rule-reviewer.agent.md` 的完整内容委派“规则审查”角色。
2. 先执行 `scripts/bind_init_plan.py --inspect-candidates --project-root <目标根目录> --scope-plan <system-temp>/scope.json --confirmed-scope-digest <用户确认摘要> --profile <system-temp>/project-profile.json --rules-dir <system-temp>/rules`。脚本除输出画像摘要、规则集合摘要与规则文件清单外，还会在同一份已确认读取范围中解析当前项目和额外源码的 Python 证据，机械拒绝会泄漏响应内容的 helper 或 fixture；通过后再把原样输出连同 `scan.json`、两份扫描角色 JSON、画像和规则候选交给审查角色。角色不重复实现该机械检查，也不回填或计算摘要。
3. 审查结果为“需要修正”时，只按审查发现修复画像或规则，再使用同一角色复审。
4. 只有 `verdict` 为 `PASS` 且 `blocking_findings` 为空时，才执行 `scripts/bind_init_plan.py --bind-review --project-root <目标根目录> --scope-plan <system-temp>/scope.json --confirmed-scope-digest <用户确认摘要> --profile <system-temp>/project-profile.json --rules-dir <system-temp>/rules --review-candidate <system-temp>/review-candidate.json --output <system-temp>/review.json`；脚本在同一份已确认读取范围中重新执行候选机械检查，并把当前两个候选摘要绑定进最终审查结果。未知字段、重复字段、结构外文字、旧候选审查结果或任何阻塞项都必须停止。
5. 不得因耗时中断、催促、重启或重新委派审查角色；持续等待同一任务自然返回完成或真实失败。中断后的结果不得算作首轮审查证据。

完成信号：审查结论为“通过”，且不存在无证据规则、固定项目假设、敏感内容、绝对路径或范围越界。

## 阶段 6：绑定并展示计划

1. 执行 `scripts/bind_init_plan.py`，传入目标根目录、已确认的 `scope.json` 及其 `scope_digest`、`scan.json`、两份扫描角色 JSON、`project-profile.json`、规则候选目录、最终审查 JSON 和系统临时目录中的新计划路径。
2. 脚本同时校验画像、两份角色结果和每份规则中的全部证据引用属于本轮扫描文件清单；运行时环境变量必须确实出现在所列项目证据中。已确认 pytest runner 只允许脚本白名单中的锁定命令，并必须同时具备对应锁文件和独立 pytest 配置证据；失败时修复输入并重新审查，不得手工编造摘要。
3. 原样展示绑定脚本输出的 `confirmation_summary` 与 `plan_digest`，并用扫描证据解释：
   - 项目类型与关键证据；
   - 项目画像摘要；
   - 将创建的规则文件及其依据；
   - 唯一的 `plan_digest`；
   - 写入范围仅为 `.tide/project-profile.json` 与 `.tide/rules/`。
4. 用户要求调整时回到阶段 4；用户取消时清理临时文件并结束。

完成信号：用户明确确认当前展示的 `plan_digest`，而不是确认旧摘要或笼统确认初始化。

## 阶段 7：执行并核验初始化

1. 执行 `scripts/apply_init_plan.py`，传入目标根目录、已确认的 `scope.json` 及其 `scope_digest`、临时计划文件和用户确认的 `plan_digest`。
2. 脚本只接受摘要完全匹配的计划；`.tide/` 已存在或目标根目录身份变化时必须失败。
3. 成功后重新读取 `.tide/project-profile.json` 与 `.tide/rules/`，核对文件清单和 SHA-256 摘要。
4. 无论成功、取消或失败，都在 `finally` 路径执行 `python3 <Skill根目录>/scripts/cleanup_temp.py <本次 init-tide 临时目录>`。脚本只允许删除系统临时根目录下名称以 `init-tide-` 开头的单层专用目录；不得用通用递归删除命令。不得运行测试、修改依赖或继续处理 HAR。

完成信号：初始化文件与确认计划逐字节一致；失败时没有遗留可被误认为初始化成功的 `project-profile.json`。
