---
name: tide
description: 基于已初始化的 Python 与 pytest 项目，在本地安全解析 HAR，分析接口场景、生成并审查测试，经逐级确认后写入新文件并可选执行。
disable-model-invocation: true
compatibility: 需要 macOS 或 Linux、Python 3.8+，且目标项目已配置 pytest。
---

# Outcome

把原始 HAR 转换为与当前项目一致、经过审查且可追溯的 pytest 接口测试；原始内容始终停留在本地确定性脚本边界内。

## Routing

- 目标项目已经由 `init-tide` 初始化，且用户提供本地 HAR 时，执行完整生成流程。
- 用户尚未明确提供本地 HAR 路径时，只请求该路径并结束当前交互；不搜索、枚举、猜测或自动选择项目中的 HAR。
- 用户只要求分析时，完成脱敏、场景分析和分析确认，不生成或写入测试。
- 用户要求继续已中断运行时，读取已有运行记录作为事实，重新分析；不隐式续跑旧状态。
- 未找到 `.tide/project-profile.json`、项目不是已有的 Python 与 pytest 项目，或任务要求创建新项目、同步仓库、安装依赖、修改已有文件时，停止并说明边界。

## Steps

1. 建立安全输入
   - 完整读取 `workflows/§01-prepare.md`。
   - 使用本地脚本把 HAR 转换为脱敏摘要；任何角色都不得读取原始 HAR。
   - 完成条件：项目画像有效，脱敏摘要通过结构检查，环境与允许范围明确。

2. 分析并确认场景
   - 完整读取 `workflows/§02-analyze.md`。
   - 由本地脚本从脱敏摘要确定性提取并绑定场景。
   - 完成条件：用户确认场景、排除项和待补信息；未确认时保持只读。

3. 生成并审查测试
   - 完整读取 `workflows/§03-generate.md`。
   - 当前会话按生成约束形成候选，再由独立结果审查角色检查；存在阻断问题时先修正并复审。
   - 完成条件：写入计划审查通过，且用户确认精确文件清单与内容。

4. 写入与可选执行
   - 完整读取 `workflows/§04-write-and-run.md`。
   - 只创建确认清单中的新测试文件和本次运行记录；执行 pytest 前再次取得单独确认。
   - 完成条件：生成状态与执行状态分别记录，所有结论都有本地证据；用户拒绝执行时执行状态为 `NOT_RUN`。

## Delivery

- 输出已确认场景、生成文件、运行编号、生成状态和执行状态。
- 分别标记 `PASS`、`PARTIAL`、`FAIL` 与 `NOT_RUN`、`PASS`、`FAIL`、`BLOCKED`，不得合并两条状态轴。
- 说明实际运行的脚本或 pytest 节点、证据文件位置、未验证内容和阻断原因。
- 只把脱敏后的运行记录保存在 `.tide/runs/<run-id>/`；原始 HAR、请求值、响应值和凭据不进入报告。

## Guardrails

- 原始 HAR 只能由 `scripts/sanitize_har.py` 在本地读取；不得交给任何角色、复制到 `.tide/`、日志、提示词或测试产物。
- 写入仅限 `.tide/` 和用户确认的现有测试目录；不得覆盖、合并或修改已有文件。
- 分析确认、写入确认和执行确认相互独立；任何快捷表达都不能替代后续确认。
- `production`、`prod`、空值和 `unknown` 环境永久阻断真实执行；真实执行的环境名只能从 `local`、`dev`、`development`、`test`、`testing`、`qa`、`staging`、`sandbox` 中选择，不接受描述性别名。
- 真实执行只接受字面 IP 目标，且项目画像必须有证据确认客户端从目标环境变量取址并明确关闭自动重定向；否则只生成并记录 `BLOCKED`。
- 不安装或升级依赖，不修改 Git，不访问外部服务，不发送通知，不自动清理用户文件。
- 不猜测业务规则、固定技术栈、行业断言、认证值、测试数据或预期结果；缺少证据时标记待确认或降低断言层级。

## References

- 开始处理 HAR 时，完整读取 `workflows/§01-prepare.md` 和 `rules/security-and-privacy.md`。
- 进入场景分析时，完整读取 `workflows/§02-analyze.md`、`rules/confirmation-and-evidence.md` 和 `rules/assertion-layers.md`。
- 用户确认场景后，完整读取 `workflows/§03-generate.md`、`prompts/test-generator.agent.md` 和 `prompts/result-reviewer.agent.md`。
- 使用 `scripts/derive_scenarios.py` 确定性提取场景后立即执行 `scripts/bind_scenarios.py` 绑定场景计划；用户确认写入后完整读取 `workflows/§04-write-and-run.md`，按其中条件执行 `scripts/write_run.py`、`scripts/launch_pytest.py` 与 `scripts/run_pytest.py`。
- 成功、取消或失败后均执行 `scripts/cleanup_temp.py` 清理本次系统临时专用目录。
