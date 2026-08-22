# 写入与可选执行

## 阶段 1：创建测试与生成记录

用户确认写入计划后执行：

```bash
python3 <Skill根目录>/scripts/write_run.py \
  --project-root <project-root> \
  --plan <system-temp>/write-plan.json \
  --review <system-temp>/review.json \
  --confirmed-write-digest <confirmed-write-digest> \
  --test-dir <confirmed-test-dir>
```

有多个确认测试目录时重复 `--test-dir`。脚本只创建计划中的新 `.py` 文件，以及 `.tide/runs/<run-id>/manifest.json` 和 `report.md`。任何目标已存在、路径越界、软链接或写入失败都会失败关闭；事务失败时只回滚本次创建且散列仍匹配的文件。

## 阶段 2：展示执行计划

写入成功不代表测试通过。根据 `manifest.json` 展示：

- 精确 pytest 节点；
- 已确认环境和目标；
- 项目画像中已证明会被测试客户端读取的目标地址环境变量；
- 项目画像中已证明且当前节点必需的其他运行时环境变量名；只展示名称和缺失状态，不显示值；
- 运行时由 `scripts/launch_pytest.py` 机械读取项目画像，只接受具备对应普通锁文件的安全 runner 白名单；所有 runner 都必须已有完整项目 `.venv`，并由该环境的 Python 启动执行器，使用一次性隔离缓存且只透传画像中必需的环境变量；不得由角色拼接 runner 命令，不创建运行环境、不安装或同步依赖；
- 执行可能产生的真实请求及其观察边界；
- 不执行时状态保持 `NOT_RUN`。

环境不在 `local`、`dev`、`development`、`test`、`testing`、`qa`、`staging`、`sandbox` 精确允许列表中，目标不是字面 IP 地址，文件散列变化，runner 未确认，或该 runner 下测试依赖未就绪时，直接记录 `BLOCKED`，不得请求绕过或临时改写环境别名。`production`、`prod`、空值和 `unknown` 始终属于阻断项；公共 IP 还必须使用 `--allow-public-target` 单独绑定当前执行摘要。域名执行保持阻断，因为脚本无法把 DNS 结果强制绑定到测试客户端实际 transport。

## 阶段 3：执行确认门

先使用相同参数执行 `--preview`，脚本必须先验证清单中的必需运行时环境变量在当前宿主中均已设置，再原样展示执行计划摘要。只有用户对当前展示的环境、目标、目标地址环境变量、必需运行时环境变量名、精确节点和执行计划摘要明确确认后，才去掉 `--preview` 并执行：

```bash
python3 <Skill根目录>/scripts/launch_pytest.py --project-root <project-root> -- \
  --run-id <run-id> \
  --environment <confirmed-environment> \
  --target-url <confirmed-target-url> \
  --confirmed-execution-digest <confirmed-execution-digest> \
  --test-node <confirmed-node>
```

需要多个节点时重复 `--test-node`。预览和执行均必须通过同一启动器；`run_pytest.py` 本体同时核验画像与 runner 摘要，以及当前 `sys.prefix` 必须精确指向目标项目的真实 `.venv`，因此宿主 Python 直接调用会在零测试、零请求状态下阻断。执行器再验证当前环境能导入 pytest；验证通过后使用同一 `.venv` 的 `sys.executable -m pytest` 和精确节点列表，不使用 shell，不透传任意 pytest 参数，不持久化原始 stdout 或 stderr。

## 阶段 4：记录与交付

执行脚本新建 `execution.json` 和 `execution-report.md`，不覆盖生成记录。根据实际结果分别报告生成状态和执行状态：

- 用户不执行：`NOT_RUN`；
- pytest 返回零：`PASS`；
- pytest 已运行且返回非零：`FAIL`；
- 安全条件、文件完整性或运行条件不满足：`BLOCKED`。

无论成功、取消或失败，都在 `finally` 路径执行 `python3 <Skill根目录>/scripts/cleanup_temp.py <本次 Tide 临时目录>`。脚本只允许删除系统临时根目录下名称以 `tide-` 开头的单层专用目录；不得用通用递归删除命令。不得删除原始 HAR、用户文件或已确认写入的测试。
