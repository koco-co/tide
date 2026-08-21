# 分析并确认场景

## 阶段 1：加载分析约束

完整读取：

- `rules/confirmation-and-evidence.md`；
- `rules/assertion-layers.md`。

只准备以下输入：脱敏 HAR 摘要、项目画像、与本次接口相关的项目规则，以及用户已授权的只读源码证据。

## 阶段 2：确定性提取并绑定场景

执行 `scripts/derive_scenarios.py --summary <system-temp>/har-summary.json --output <system-temp>/scenario-analysis.json`。脚本仅从脱敏结构中识别成功 JSON 请求、去重和完整 CRUD 时序，排除失败响应、静态资源和不完整记录；仅凭 HAR 形成的 CRUD 场景最多绑定协议、结构和关系三层，不得臆测业务层断言；不得让角色重复完成这些机械工作。

收到结果后立即执行 `scripts/bind_scenarios.py --project-root <project-root> --summary <system-temp>/har-summary.json --analysis <system-temp>/scenario-analysis.json --output <system-temp>/scenario-plan.json`。脚本严格校验字段、重复键、场景编号、已有 `entry_id`、断言层级、证据引用和隐私风险文本，并绑定当前画像、规则、脱敏摘要与分析内容。脚本非零退出时停止，不把结果传给后续角色；不得用人工判断替代或修改脚本摘要。

## 阶段 3：分析确认门

原样展示 `scenario-plan.json` 中的 `confirmation_summary` 与 `plan_digest`，再说明脱敏接口概览、每个场景的断言层级和必要问题。只询问会改变场景或安全边界的问题。环境确认必须单独展示，并原样使用用户确认的环境名；其生成与执行资格由脚本校验。

- 用户确认：记录用户明确确认的当前 `plan_digest`，冻结该脚本绑定的场景集合，进入生成阶段。
- 用户要求调整：只重新分析受影响场景，再次展示完整确认结果。
- 用户拒绝或取消：以只读分析结果结束，项目中不产生新文件。

完成信号：当前场景计划摘要、排除项、测试目录和生成边界均得到明确确认；此时仍未生成或写入测试代码。
