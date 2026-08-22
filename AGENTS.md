# Tide Agent Guide

## 项目概览

Tide 是一个纯 Skills 插件：先初始化已有 Python 与 pytest 接口自动化项目，再从本地 HAR 生成、审查、写入并可选执行 pytest 接口测试。

正式宿主为 Claude Code 与 Codex。`skills/` 是唯一 Skill 来源；仓库不维护宿主副本、生成镜像或第二套工作流。

## 仓库结构

- `skills/init-tide/`：只读扫描已有项目，生成项目画像和项目专属规则，经确认后原子创建 `.tide/`。
- `skills/tide/`：本地脱敏 HAR，确定性提取场景，生成并审查测试，经独立确认后写入和可选执行。
- `skills/*/scripts/`：Python 3.8+ 标准库机械门禁；不得把可确定校验退回提示词判断。
- `skills/*/prompts/`：只保存确实需要角色判断的职责说明。
- `skills/*/workflows/`、`skills/*/rules/`：对应 Skill 的工作流和公共安全规范。
- `.claude-plugin/`：Claude 插件与 Marketplace 清单。
- `.codex-plugin/`：Codex 插件清单和界面元数据。
- `.agents/plugins/marketplace.json`：公共插件 Marketplace 元数据。
- `assets/`：README 引用资源，不承载 Skill 行为。
- `.github/workflows/ci.yml`：Python 3.8 脚本、目录边界和公共内容检查。

不要创建根级 `commands/`、`codex-skills/`、`agents/`、`prompts/`、`references/`、`templates/`、`resources/`、`plugins/`、`src/`、`tests/` 或 `docs/`。Skill 所需内容必须放入对应的 `skills/<skill-name>/`。

## 单一来源与平台边界

- Claude Code 与 Codex 共用同一份 Skill 正文、工作流、规则、提示词和脚本。
- Skill 内容保持平台无关，不写 `/tide:*`、`$tide`、`$init-tide` 等宿主调用语法。
- Skill frontmatter 不添加只对单一宿主生效的 `model`、`tools` 等字段。
- 宿主差异只允许出现在各自插件清单和 README 安装说明中。
- Skill 正文、description、工作流、规则和诊断信息使用中文；代码标识符和协议字段按既有契约保留英文。
- 修改插件版本时同步更新 `.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`、`.codex-plugin/plugin.json` 和 `CHANGELOG.md`。

## Skill 开发约定

- `init-tide` 只初始化已有 Python 与 pytest 项目，不创建固定脚手架。
- 项目代码风格、fixture、认证、目录和测试约定必须从目标项目证据动态生成，不能写死在插件规则中。
- 原始 HAR 只能由 `skills/tide/scripts/sanitize_har.py` 在本地读取；不得进入提示词、角色上下文、测试、报告或 `.tide/`。
- 能由脚本确定的结构、路径、摘要、状态、数据流和安全条件必须由脚本校验。
- 提示词只处理需要语义判断的生成或审查任务，不重复实现机械门禁。
- 初始化确认、场景确认、写入确认和真实执行确认互不替代。
- 写入只允许新建确认范围内的 `.tide/` 文件和测试文件；不得覆盖或自动合并已有文件。
- 真实执行默认关闭。生产、未知环境、域名目标、未经确认的 runner 或 transport 证据不足时必须失败关闭。
- 生成状态与执行状态分别记录，不得把生成成功报告为测试执行成功。

## Python 脚本约定

- 所有随附脚本兼容 Python 3.8+，优先使用标准库。
- 每个脚本必须支持 `--help` 和隔离的 `--self-test`。
- 不依赖用户目标项目安装额外工具，不自动安装、升级或同步依赖。
- 文件系统操作必须校验真实路径、符号链接、文件类型、大小、摘要和允许目录。
- 写入使用只新增、原子发布和失败回滚语义。
- 不使用 shell 执行测试命令；runner、参数、cwd 和环境变量必须由机械白名单构造。
- 运行校验时设置 `PYTHONDONTWRITEBYTECODE=1`，不得提交 `__pycache__`、`.pytest_cache`、`.ruff_cache`、`.venv` 或 `.tide`。

## 本地验证

从仓库根目录执行：

```bash
find skills -path '*/scripts/*.py' -type f -print0 | sort -z | \
  while IFS= read -r -d '' script; do \
    PYTHONDONTWRITEBYTECODE=1 python3 "$script" --help >/dev/null && \
    PYTHONDONTWRITEBYTECODE=1 python3 "$script" --self-test; \
  done

claude plugin validate . --strict

git diff --check
```

安装了 `build-goals` 时，另外执行：

```bash
python3 <build-goals-root>/skills/build-plugin/scripts/validate_plugin.py \
  . --platform dual --strict

python3 <build-goals-root>/skills/build-skill/scripts/validate_skill.py \
  skills/init-tide --profile dual --strict

python3 <build-goals-root>/skills/build-skill/scripts/validate_skill.py \
  skills/tide --profile dual --strict
```

提交前确认：

- 三份插件版本一致；
- `skills/` 中没有宿主调用语法、平台名称、`model` 或 `tools` 字段；
- 旧名称只允许出现在 `CHANGELOG.md` 的历史记录中；
- 没有退役根目录、除 `CLAUDE.md -> AGENTS.md` 外的符号链接或缓存产物；
- 行为修改包含对应脚本自检和变更记录；
- 静态校验、真实宿主发现、真实项目生成和真实 HTTP 执行分别报告，不互相替代。

## Git 与交付

- 保留用户已有修改，只暂存当前任务文件。
- 提交信息使用 Emoji Conventional Commit，并包含：

  `Co-authored-by: Codex <noreply@openai.com>`

- commit、push、覆盖 `main`、发布和更新本地插件都需要用户明确授权。
- 推送后核对远端 SHA 和 GitHub Actions；不得通过允许真实密钥绕过 Push Protection。
