# Tide 全面优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4 个子项目全面优化 — SKILL 按需加载重构、基础设施接入、代码质量修复、UX 增强

**Architecture:**
- 子项目 C（代码质量）可独立执行，不与 A 冲突
- 子项目 A（SKILL 重构）是核心改造，完成后 B/D 在其基础上接入
- 执行顺序：C → A → B → D

**Tech Stack:** Python 3.12+, pytest, ast, pydantic, Claude Code Skill

---

## 文件结构总览

```
本次变更涉及的文件:

scripts/har_parser.py     — 新增 validate_har / scan_auth_headers + match_repo 类型 + _extract_service_module 逻辑
scripts/test_runner.py    — 新增 detect_runner + python→sys.executable
scripts/format_checker.py — 补全 FC03/FC04/FC05/FC06/FC10 检查函数
scripts/hooks.py          — 新增 CLI run 子命令 + import 提顶
scripts/preferences.py    — 新增 CLI read/write 子命令
scripts/notifier.py       — FORMATTERS 类型修正
scripts/scaffold.py       — 抽取 _render_tide_config
scripts/state_manager.py  — archive 异常处理增强

skills/tide/SKILL.md       — 重写为极简编排（~200 行）
skills/using-tide/SKILL.md — 重写为极简编排（~250 行）
agents/scenario-analyzer.md    — 参数化，支持 no_source_mode 上下文注入

pyproject.toml            — 版本号 1.0.0 → 1.3.0
.claude-plugin/plugin.json — 版本号 → 1.3.0
README.md                 — 版本号 + Roadmap 合并
Makefile                  — release 命令增强

tests/test_format_checker.py       — 新增 FC03-FC06/FC10 测试
tests/test_integration_har_to_state.py — 新增集成测试
tests/test_integration_flow.py     — 新增集成测试
```

---

### Phase 0: 代码质量修复（子项目 C，可独立执行）

---

### Task 1: 版本号统一

**Files:**
- Modify: `pyproject.toml:2`
- Modify: `.claude-plugin/plugin.json:4`
- Modify: `README.md:4,495-500`
- Modify: `Makefile:25-29`

- [ ] **Step 1: 更新 pyproject.toml 版本号**

`pyproject.toml:2` → `version = "1.3.0"`

- [ ] **Step 2: 更新 plugin.json 版本号**

`.claude-plugin/plugin.json:4` → `"version": "1.3.0"`

- [ ] **Step 3: 更新 README.md 版本号 badge 和 Roadmap**

README.md:4 — badge 中 `v1.2` → `v1.3`
README.md:500-501 — 合并 Roadmap 中 "v1.2（当前）"和 "v1.3（当前）"为一行：

```
| **v1.3（当前）** | 跨项目优化 · Hook 系统 · 偏好学习 · 格式检查器 · 测试覆盖 78% |
```

- [ ] **Step 4: 增强 Makefile release 命令**

`Makefile:25-29` — 改为从 pyproject.toml 读取版本号：

```makefile
release:
	@echo "=== 发布流程 ==="
	@echo "1. 确认 pyproject.toml 版本号已更新"
	@python3 -c "import tomllib; v=tomllib.load(open('pyproject.toml','rb'))['project']['version']; print(f'  当前版本: {v}')"
	@echo "2. git tag v$$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")"
	@echo "3. git push origin main --tags"
	@echo "4. 在 GitHub 上创建 Release"
```

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml .claude-plugin/plugin.json README.md Makefile
git commit -m "chore: 统一版本号为 1.3.0，增强 release 命令"
```

---

### Task 2: 代码质量修复

**Files:**
- Modify: `scripts/har_parser.py:254-262`
- Modify: `scripts/har_parser.py:270-278`
- Modify: `scripts/test_runner.py:31`
- Modify: `scripts/notifier.py:103`
- Modify: `scripts/scaffold.py:194-203,286-293`
- Modify: `scripts/hooks.py` (import 提顶)

- [ ] **Step 1: match_repo 类型标注修复**

```python
# har_parser.py:254-262 — 改前
def match_repo(
    path: str, profiles: list[dict]
) -> tuple[str | None, str | None]:

# 改后
def match_repo(
    path: str, profiles: list[RepoProfile]
) -> tuple[str | None, str | None]:
    for profile in profiles:
        for prefix in profile.url_prefixes:
            if path.startswith(prefix):
                return profile.name, profile.branch
    return None, None
```

同时修改 `har_parser.py:322-329` 中的调用处（当前用 `p.model_dump()` 后传 list[dict]），改为直接传 `validated.profiles`：

```python
# har_parser.py:322-329 — 改前
validated = RepoProfilesConfig.model_validate(profiles_data)
profiles = [p.model_dump() for p in validated.profiles]

# 改后
validated = RepoProfilesConfig.model_validate(profiles_data)
profiles = validated.profiles
```

- [ ] **Step 2: _extract_service_module 路径后移回退**

```python
# har_parser.py:270-278 — 改后
def _extract_service_module(path: str) -> tuple[str, str]:
    """从 URL 路径部分推导出 (service, module)。

    示例：/dassets/v1/datamap/recentQuery → service=dassets, module=datamap
           /api/v1/users                  → service=api, module=users
           /health                        → service=health, module=health
    """
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "", ""
    service = parts[0]
    # 从右向左找模块名：跳过常见版本号段
    module = service
    for p in reversed(parts[1:]):
        if re.match(r"^v\d+", p):
            continue
        module = p
        break
    return service, module
```

注意：需在文件顶部添加 `import re`（已有 `import json`，在 `re` 之上）。

- [ ] **Step 3: test_runner.py python→sys.executable**

```python
# test_runner.py:31 — 改前
elif runner == "direct":
    cmd = ["python", "-m", "pytest"]

# 改后
elif runner == "direct":
    import sys
    cmd = [sys.executable, "-m", "pytest"]
```

- [ ] **Step 4: notifier.py FORMATTERS 类型修正**

```python
# notifier.py:103 — 改前
FORMATTERS: dict[str, object] = {

# 改后
from collections.abc import Callable

FORMATTERS: dict[str, Callable[[NotificationPayload], dict]] = {
```

- [ ] **Step 5: scaffold.py 抽取重复的 tide-config 渲染**

```python
# scaffold.py — 新增在 _write_if_not_exists 之后
def _render_tide_config(
    root: Path, env: Environment, config_vars: dict, created: list[str]
) -> None:
    """渲染 tide-config.yaml，若模板存在且文件不存在则创建。"""
    from scripts.common import warnings  # or move import to top
    template_path = TEMPLATES_DIR / "tide-config.yaml.j2"
    if not template_path.exists():
        warnings.warn(f"Template not found: {template_path}", stacklevel=2)
        return
    content = env.get_template("tide-config.yaml.j2").render(**config_vars)
    if _write_if_not_exists(root / "tide-config.yaml", content):
        created.append("tide-config.yaml")
```

在 `append_to_existing_project` 和 `generate_project` 中分别替换为调用此函数。

- [ ] **Step 6: hooks.py import 提顶**

```python
# hooks.py:3-6 — 改前
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum

# 改后
from __future__ import annotations
import sys
from dataclasses import dataclass, field
from enum import StrEnum
```

文件中 `import sys` 两处（`hooks.py:93` 和 `hooks.py:106`）移除。

- [ ] **Step 7: 运行已有测试确保没破坏**

```bash
uv run pytest tests/ -v --no-cov
```

Expected: 所有测试通过。

- [ ] **Step 8: 提交**

```bash
git add scripts/har_parser.py scripts/test_runner.py scripts/notifier.py scripts/scaffold.py scripts/hooks.py
git commit -m "refactor: 代码质量修复 — match_repo 类型、service_module 逻辑、重复代码抽取等"
```

---

### Task 3: 格式检查器补全 FC03-FC06/FC10

**Files:**
- Modify: `scripts/format_checker.py`

- [ ] **Step 1: 补全 FC03 — 未使用的 import**

```python
def _check_unused_imports(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC03: 无未使用的 import（排除 __future__ 和 typing.TYPE_CHECKING）。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC03"]

    imports: dict[int, tuple[str, int]] = {}  # lineno → (name, end_lineno)
    used_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    imports[node.lineno] = (alias.asname, node.end_lineno or node.lineno)
                else:
                    imports[node.lineno] = (alias.name.split(".")[0], node.end_lineno or node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module == "__future__":
                continue
            for alias in node.names:
                name = alias.asname or alias.name
                imports[node.lineno] = (name, node.end_lineno or node.lineno)
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                used_names.add(node.id)

    for lineno, (name, _) in imports.items():
        if name not in used_names:
            violations.append(Violation(
                rule=rule, file=filepath, line=lineno,
                detail=f"未使用的 import: {name}",
            ))
    return violations
```

- [ ] **Step 2: 补全 FC04 — 硬编码测试数据**

```python
_CRITICAL_PATTERNS = (
    "/api/", "/v1/", "/v2/",
)

def _check_hardcoded_data(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC04: 无硬编码测试数据（URL、长数字 ID）。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC04"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str) and any(p in node.value for p in _CRITICAL_PATTERNS):
                violations.append(Violation(
                    rule=rule, file=filepath, line=node.lineno,
                    detail=f"可能的硬编码 URL: {node.value[:60]}",
                ))
            elif isinstance(node.value, int) and node.value > 99999:
                violations.append(Violation(
                    rule=rule, file=filepath, line=node.lineno,
                    detail=f"可能的硬编码 ID: {node.value}",
                ))
    return violations
```

- [ ] **Step 3: 补全 FC05 — 断言消息描述性**

```python
def _check_assert_message(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC05: 断言消息必须描述性（assert 含 msg 参数）。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC05"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert) and node.msg is None:
            violations.append(Violation(
                rule=rule, file=filepath, line=node.lineno,
                detail="assert 语句缺少描述消息",
            ))
    return violations
```

- [ ] **Step 4: 补全 FC06 — Pydantic Field description**

```python
def _check_pydantic_description(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC06: Pydantic 模型字段必须有 description。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC06"]

    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Field"):
            has_description = any(
                kw.arg == "description" for kw in node.keywords
            )
            if not has_description:
                violations.append(Violation(
                    rule=rule, file=filepath, line=node.lineno,
                    detail="Field() 调用缺少 description 参数",
                ))
    return violations
```

- [ ] **Step 5: 补全 FC10 — 嵌套深度不超过 3 层**

```python
_NESTED_PARENTS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)

def _check_nesting_depth(tree: ast.Module, filepath: str) -> list[Violation]:
    """FC10: 嵌套深度不超过 3 层。"""
    violations: list[Violation] = []
    rule = _RULE_MAP["FC10"]

    for node in ast.walk(tree):
        depth = 0
        parent = getattr(node, "parent", None) if hasattr(node, "parent") else None
        # AST 节点没有 parent 引用，需要遍历来定位嵌套
        # 使用 ast.NodeTransformer 不适合。改用嵌套计数 walk 方式：
        for ancestor in ast.walk(tree):
            if isinstance(ancestor, _NESTED_PARENTS):
                pass  # 简化处理：使用位置范围判断包含关系

    # 简化实现：检测 if/for/while 的 body 中的嵌套
    def _count_nesting(node: ast.AST, current: int = 0) -> None:
        if current > 3:
            violations.append(Violation(
                rule=rule, file=filepath, line=node.lineno,
                detail=f"嵌套深度超过 3 层（当前 {current} 层）",
            ))
            return
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _NESTED_PARENTS):
                _count_nesting(child, current + 1)
            else:
                _count_nesting(child, current)

    _count_nesting(tree)
    return violations
```

- [ ] **Step 6: 在 check_file 中注册新检查**

```python
# format_checker.py — check_file 函数末尾追加
    violations.extend(_check_unused_imports(tree, filepath))
    violations.extend(_check_hardcoded_data(tree, filepath))
    violations.extend(_check_assert_message(tree, filepath))
    violations.extend(_check_pydantic_description(tree, filepath))
    violations.extend(_check_nesting_depth(tree, filepath))
```

- [ ] **Step 7: 运行测试验证现有测试仍通过**

```bash
uv run pytest tests/test_format_checker.py -v --no-cov
```

- [ ] **Step 8: 提交**

```bash
git add scripts/format_checker.py
git commit -m "feat: 格式检查器补全 FC03-FC06/FC10 规则"
```

---

### Task 4: 补充集成测试

**Files:**
- Create: `tests/test_integration_har_to_state.py`
- Create: `tests/test_integration_flow.py`

- [ ] **Step 1: 创建 HAR→state 集成测试**

```python
"""Integration test: HAR parse → state persist → resume → archive."""
import json
from pathlib import Path

import pytest

from scripts.har_parser import parse_har
from scripts.state_manager import (
    advance_wave,
    archive_session,
    init_session,
    resume_session,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestHarToStateFlow:
    """验证 HAR 解析结果能正确保存到 state 并通过 resume/archive 管理。"""

    def test_full_pipeline(self, tmp_path: Path) -> None:
        """HAR 解析 → init_session → advance_wave*4 → archive 完整流程。"""
        har_path = FIXTURES_DIR / "sample.har"
        profiles_path = FIXTURES_DIR / "sample_repo_profiles.yaml"

        # 1. 解析 HAR
        result = parse_har(har_path, profiles_path)
        assert len(result.endpoints) > 0

        # 2. 初始化 state
        state = init_session(tmp_path, str(har_path))
        assert state.current_wave == 0

        # 3. 推进 4 个波次
        for wave_num in range(1, 5):
            state = advance_wave(tmp_path, wave_num, data={
                "endpoint_count": len(result.endpoints) if wave_num == 1 else None,
            })
            assert state.current_wave == wave_num

        # 4. resume 验证
        resumed = resume_session(tmp_path)
        assert resumed is not None
        assert resumed.current_wave == 4

        # 5. archive
        history_dir = archive_session(tmp_path)
        assert history_dir is not None
        assert history_dir.exists()
        assert (history_dir / "state.json").exists()
        # 原文件应已移动
        assert not (tmp_path / ".tide" / "state.json").exists()

    def test_resume_no_session(self, tmp_path: Path) -> None:
        """无 session 时 resume 返回 None。"""
        assert resume_session(tmp_path) is None

    def test_archive_no_session(self, tmp_path: Path) -> None:
        """无 session 时 archive 返回 None。"""
        assert archive_session(tmp_path) is None
```

- [ ] **Step 2: 运行新集成测试**

```bash
uv run pytest tests/test_integration_har_to_state.py -v --no-cov
```

Expected: 所有测试通过。

- [ ] **Step 3: 创建 flow 集成测试（Mock Agent 调用）**

```python
"""Integration test: simulate wave orchestration with mocked agents."""
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.har_parser import parse_har, ParsedResult
from scripts.state_manager import WaveStatus, init_session, advance_wave, resume_session

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestFlowOrchestration:
    """验证编排逻辑在 mock 环境下的完整性。"""

    def test_precheck_to_wave1(self, tmp_path: Path) -> None:
        """预检阶段到 Wave 1 完成：HAR 校验 → 解析 → state 推进。"""
        har_path = FIXTURES_DIR / "sample.har"
        profiles_path = FIXTURES_DIR / "sample_repo_profiles.yaml"

        # 模拟预检：HAR 校验
        result = parse_har(har_path, profiles_path)
        assert len(result.endpoints) == 3
        assert result.summary.after_dedup == 3

        # 初始化 session
        state = init_session(tmp_path, str(har_path))
        assert state.current_wave == 0

        # 模拟 Wave 1 完成
        state = advance_wave(tmp_path, 1, data={
            "parsed": result.model_dump(),
        })
        assert state.waves["1"].status == WaveStatus.COMPLETED

    @pytest.mark.parametrize("start_wave,expected", [
        (1, "out of order"),
        (2, "out of order"),
    ])
    def test_wave_order_enforcement(
        self, tmp_path: Path, start_wave: int, expected: str
    ) -> None:
        """非当前波次的 advance 应被拒绝。"""
        init_session(tmp_path, "test.har")
        with pytest.raises(ValueError, match=expected):
            advance_wave(tmp_path, start_wave)
```

- [ ] **Step 4: 运行 flow 集成测试**

```bash
uv run pytest tests/test_integration_flow.py -v --no-cov
```

- [ ] **Step 5: 运行全量测试确认无回归**

```bash
uv run pytest tests/ -v --no-cov
```

- [ ] **Step 6: 提交**

```bash
git add tests/test_integration_har_to_state.py tests/test_integration_flow.py
git commit -m "test: 新增 HAR→state 集成测试和编排流集成测试"
```

---

### Phase 1: SKILL 架构重构（子项目 A）

---

### Task 5: 抽取内联 Python 到 scripts

**Files:**
- Modify: `scripts/har_parser.py` — 新增 `validate_har()` 和 `scan_auth_headers()`
- Modify: `scripts/test_runner.py` — 新增 `detect_runner()`

- [ ] **Step 1: 在 har_parser.py 新增 validate_har()**

```python
# har_parser.py — 在 match_repo 之前新增
def validate_har(har_path: Path) -> tuple[bool, str, int]:
    """验证 HAR 文件是否合法，返回 (is_valid, message, entry_count)。

    用于 SKILL 预检阶段，替代内联 python3 -c 代码。
    """
    try:
        raw = json.loads(har_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return False, f"Invalid HAR: {exc}", 0

    if "log" not in raw or "entries" not in raw.get("log", {}):
        return False, "Invalid HAR: missing log.entries", 0

    entries = raw["log"]["entries"]
    return True, f"entries: {len(entries)}", len(entries)


def scan_auth_headers(har_path: Path) -> dict[str, int]:
    """扫描 HAR 中的认证头分布，返回 {auth_type: count}。

    用于 SKILL 预检阶段，替代内联 python3 -c 代码。
    """
    import collections

    raw = json.loads(har_path.read_text())
    entries = raw.get("log", {}).get("entries", [])
    auth_stats: dict[str, int] = collections.Counter()

    for entry in entries:
        headers = {h["name"].lower(): h["value"] for h in entry.get("request", {}).get("headers", [])}
        if "cookie" in headers:
            auth_stats["cookie"] += 1
        elif "authorization" in headers:
            auth_type = headers["authorization"].split()[0]
            auth_stats[f"token({auth_type})"] += 1
        else:
            auth_stats["none"] += 1

    return dict(auth_stats)
```

- [ ] **Step 2: 在 test_runner.py 新增 detect_runner()**

```python
# test_runner.py — 在 build_pytest_command 之前新增
from pathlib import Path


def detect_runner(project_root: Path | None = None) -> str:
    """检测项目使用的包管理器，返回 'uv' | 'poetry' | 'pip' | 'direct'。

    用于 SKILL 预检阶段，替代内联检测代码。
    """
    root = project_root or Path.cwd()

    if (root / "uv.lock").exists():
        return "uv"
    if (root / "poetry.lock").exists():
        return "poetry"
    if (root / "requirements.txt").exists():
        return "pip"
    return "direct"
```

- [ ] **Step 3: 验证新增函数可调用**

```bash
uv run python3 -c "from scripts.har_parser import validate_har, scan_auth_headers; from scripts.test_runner import detect_runner; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 提交**

```bash
git add scripts/har_parser.py scripts/test_runner.py
git commit -m "feat: 抽取内联 Python 逻辑到 scripts — validate_har / scan_auth_headers / detect_runner"
```

---

### Task 6: 重写 skills/tide/SKILL.md 为极简编排

**Files:**
- Modify: `skills/tide/SKILL.md`

- [ ] **Step 1: 编写新 SKILL.md**

新的 `skills/tide/SKILL.md`：

```markdown
---
name: tide
description: "从 HAR 文件生成 pytest 测试套件，结合源码进行 AI 智能分析。触发方式：/tide <har-path>、'从 HAR 生成测试'、提供 .har 文件路径。"
argument-hint: "<har-file-path> [--quick] [--resume] [--wave N]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, TaskCreate, TaskUpdate, TaskList
---

# Tide：HAR 转 Pytest 测试生成

## 任务初始化

在流程开始时创建 6 个任务：
- 预检与参数校验
- [1/4] 解析与准备
- [2/4] 场景分析
- [3/4] 代码生成
- [4/4] 评审与交付
- 验收报告与归档

格式同现有 TaskCreate，ID 依次记为 `<task_1_id>` 到 `<task_6_id>`。

---

## 预检阶段

1. 标记 task 1 为 in_progress
2. 设置 `PLUGIN_DIR="${CLAUDE_SKILL_DIR}/../.."`
3. 解析 `$ARGUMENTS`：`har_path`（必填）、`--quick`、`--resume`、`--wave N`
4. **环境检查**：`test -f repo-profiles.yaml`，若缺失则打印带修复命令的错误信息并终止
5. **读取配置**：`repo-profiles.yaml` 和 `tide-config.yaml`，提取 repos、test_dir、test_types、industry 等
6. **无源码降级**：repos 为空时设置 `no_source_mode=true`
7. **恢复检查**：若 `state.json` 存在且未设置 `--resume`，询问继续/重来/查看摘要
8. **HAR 校验**：`uv run python3 -c "from scripts.har_parser import validate_har; r = validate_har(Path('${har_path}')); print(r)"`
9. **认证头扫描**：`uv run python3 -c "from scripts.har_parser import scan_auth_headers; print(scan_auth_headers(Path('${har_path}')))"`
10. **[新增] 隐私提示**：首屏输出 HAR 数据发送至 AI 模型的提示，请用户确认
11. **参数摘要**：打印 HAR 路径/记录数/认证方式/测试目录/源码模式/模式

Task 1 完成。

---

## 第一波次：解析与准备（并行）

Task 2 → in_progress

1. `uv run python3 ${CLAUDE_SKILL_DIR}/../../scripts/state_manager.py init --har "${har_path}"`
2. **并行**启动两个 Agent，prompt 分别见 `agents/har-parser.md` 和 `agents/repo-syncer.md`（仅在 `no_source_mode=false` 时启动后者）
3. 读取验证输出（parsed.json / repo-status.json）
4. 输出验证摘要，检查点保存

**[Hook]** 若 tide-config.yaml 中有 hook 配置，执行 `uv run python3 scripts/hooks.py run wave1:parse:after`

Task 2 完成。

---

## 第二波次：场景分析（顺序执行）

Task 3 → in_progress

1. 读取 `agents/scenario-analyzer.md`，传入上下文：`no_source_mode` / `test_types` / `industry_mode`
2. 启动 scenario-analyzer Agent
3. 读取 scenarios.json
4. 若非 `--quick`，展示确认清单供用户确认

**[Hook]** 若配置了 hook，执行 `wave2:analyze:after`

检查点保存，Task 3 完成。

---

## 第三波次：代码生成（并行扇出）

Task 4 → in_progress

1. 读取 scenarios.json → generation_plan
2. 对每个模块并行启动一个 case-writer Agent，prompt 见 `agents/case-writer.md`，传入 `detected_auth_type`
3. 全部完成后，对每个生成文件执行 py_compile + AST 检查

**[偏好]** 将本次生成的模块数写入偏好

检查点保存，Task 4 完成。

---

## 第四波次：评审 + 执行 + 交付

Task 5 → in_progress

1. 启动 case-reviewer Agent，prompt 见 `agents/case-reviewer.md`
2. 检测包管理器并执行测试
3. 生成验收报告

**[Hook]** 执行 `wave4:review:after` 和 `output:notify`

Task 5 完成，Task 6 → in_progress → 显示最终摘要 → 完成。

---

## 隐私提示模板

在预检 HAR 校验完成后输出：

```
[HAR 内容隐私提示]
HAR 文件中的 URL、请求/响应数据将发送给 AI 模型进行分析。
敏感头（Cookie/Authorization）已在解析时自动剥离。
如包含业务敏感数据（用户 PII、密钥等），建议脱敏后再使用。
确认继续？
```

提示后等用户确认再进入 Wave 1。
```

注意：此 SKILL.md 约 130 行（原 682 行）。行数减少约 80%。

- [ ] **Step 2: 提交**

```bash
git add skills/tide/SKILL.md
git commit -m "refactor: tide SKILL.md 重写为极简编排（682→130 行），按需加载 agents/*.md"
```

---

### Task 7: 重写 skills/using-tide/SKILL.md 为极简编排

**Files:**
- Modify: `skills/using-tide/SKILL.md`

- [ ] **Step 1: 编写新 SKILL.md**

新的 `skills/using-tide/SKILL.md`：

```markdown
---
name: using-tide
description: "初始化 Tide 环境 — 智能项目分类、深度扫描/行业调研、方案推荐、脚手架生成。触发方式：首次运行、/using-tide、'初始化 tide'。"
argument-hint: "[--force]"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, WebSearch, WebFetch, TaskCreate, TaskUpdate, TaskList
---

# Tide 初始化

为新项目或已有项目引导安装 Tide 测试框架。

---

## 任务初始化

创建 6 个任务（同现有格式）：
1. 环境检测 + 智能分类
2. 项目分析（根据分类更新主题）
3. 确认与选择（根据分类更新主题）
4. 源码仓库配置
5. 连接配置
6. 脚手架生成 + 配置验证

ID 记为 `<task_1_id>` 到 `<task_6_id>`。

---

## 第零步：环境检测 + 智能分类

Task 1 → in_progress

1. **工具检测**：`python3 --version` / `uv --version` / `git --version`
2. **依赖检测**：jinja2 / pydantic / pyyaml
3. **重初始化检测**：若 tide-config.yaml 已存在，询问使用/更新/重来
4. **智能分类**：检测测试文件数、conftest、pytest 配置、HTTP 客户端、allure、CI

判定规则：`TEST_FILE_COUNT >= 3 AND (CONFTEST 存在 OR PYTEST_CONFIG 存在) → existing_auto`

Task 1 完成。根据 project_type 更新 Task 2/3 主题。

---

## 分支 A：已有自动项目

### 深度扫描

Task 2 → in_progress

1. 读取 `agents/project-scanner.md` 作为 prompt
2. 启动 project-scanner Agent（opus）
3. 读取 project-profile.json

Task 2 完成。Task 3 → in_progress

### 7 维度确认

逐项展示 project-profile.json 的 7 个维度（架构/代码风格/鉴权/工具链/Allure/数据管理/行业），每个维度用户确认或修正。

Task 3 完成。跳转至第三步。

---

## 分支 B：新项目

### 行业画像收集

Task 2 → in_progress

5 个问题逐一收集：行业领域 / 系统类型 / 团队规模 / 特殊需求 / 鉴权复杂度

### AI 调研

1. 读取 `agents/industry-researcher.md` 作为 prompt
2. 启动 industry-researcher Agent（sonnet）
3. 读取 research-report.json

Task 2 完成。Task 3 → in_progress

### 方案推荐与试运行

展示 2-3 个方案 → 用户选择 → 生成最小示例 → 确认风格

Task 3 完成。

---

## 第三步：源码仓库配置（共用）

Task 4 → in_progress

1. 询问仓库 URL（可 @branch）
2. git clone 各仓库
3. 配置 URL 前缀映射
4. 写入 repo-profiles.yaml

Task 4 完成。

---

## 第四步：连接配置（共用）

Task 5 → in_progress

1. Base URL → 认证方式（分支 A 可复用旧逻辑）→ 数据库（可选）→ Webhook（可选）
2. 写入 .env 或 .tide/config.yaml

Task 5 完成。

---

## 第五步：脚手架生成 + 配置验证

Task 6 → in_progress

1. 渲染 tide-config.yaml（Jinja2）
2. 运行 scaffold.py（--mode new/existing）
3. 生成 CLAUDE.md
4. smoke test（URL 可达 + 认证 + DB）

打印初始化摘要，Task 6 完成。
```

注：此版本约 120 行（原 866 行）。

- [ ] **Step 2: 提交**

```bash
git add skills/using-tide/SKILL.md
git commit -m "refactor: using-tide SKILL.md 重写为极简编排（866→120 行）"
```

---

### Task 8: 参数化 agents/scenario-analyzer.md

**Files:**
- Modify: `agents/scenario-analyzer.md`

- [ ] **Step 1: 替换硬编码行业模式分支为参数化说明**

`agents/scenario-analyzer.md:48-49` — 改前：

```
若任务 prompt 中包含 `industry_mode = true`，同时读取 `prompts/industry-assertions.md`，为写入类接口追加上表中的 `industry_*` 类型场景。行业场景仅在对应行业匹配时生成。
```

改为：

```
根据主管（orchestrator）传递的上下文动态调整行为：
- 若上下文包含 `no_source_mode = true`：跳过阶段一（源代码追踪），所有场景标记 confidence: 'low'
- 若上下文包含 `test_types`：仅生成 test_types 中指定的类型
- 若上下文包含 `industry_mode = true`：同时读取 prompts/industry-assertions.md，为写入类接口追加行业特有场景
```

- [ ] **Step 2: 移除全文中的 hardcoded 无源码降级描述**

全文搜索"注意：当前为无源码模式"等相关分支性描述，改为"根据运行时上下文决定"的泛化描述。

- [ ] **Step 3: 提交**

```bash
git add agents/scenario-analyzer.md
git commit -m "refactor: scenario-analyzer.md 参数化 — 运行时上下文代替硬编码分支"
```

---

### Phase 2: 基础设施接入（子项目 B）

---

### Task 9: Hook 系统 CLI 入口与挂载

**Files:**
- Modify: `scripts/hooks.py` — 新增 CLI `run` 子命令

- [ ] **Step 1: 添加 CLI run 子命令**

在 `hooks.py` 末尾 `if __name__ == "__main__"` 前新增：

```python
# hooks.py — 新增函数
def run_hook(point_str: str, project_root: str = ".") -> None:
    """根据 YAML 配置执行指定 hook point 的所有注册命令。"""
    config_path = Path(project_root) / "tide-config.yaml"
    registry = load_hooks_from_config(str(config_path))

    try:
        point = HookPoint(point_str)
    except ValueError:
        print(f"[hooks] Unknown hook point: {point_str}")
        return

    registrations = registry.get_hooks(point)
    if not registrations:
        print(f"[hooks] No hooks registered for {point_str}")
        return

    import subprocess
    for reg in registrations:
        print(f"[hooks] Running {reg.name} for {point_str}...")
        result = subprocess.run(reg.command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[hooks] {reg.name} failed: {result.stderr.strip()}")
        else:
            print(f"[hooks] {reg.name} OK")
```

在 `if __name__ == "__main__"` 中新增 `run` 子命令：

```python
# hooks.py — 在现有 __main__ 块中新增
run_p = sub.add_parser("run")
run_p.add_argument("point", help="Hook point name (e.g. wave1:parse:after)")
run_p.add_argument("--project-root", default=".")
```

并在命令调度中新增分支：

```python
if args.command == "run":
    run_hook(args.point, args.project_root)
```

- [ ] **Step 2: 验证 CLI 可用**

```bash
uv run python3 scripts/hooks.py run wave1:parse:before --project-root .
```

Expected: "No hooks registered"（因为未配置 tide-config.yaml）

- [ ] **Step 3: 提交**

```bash
git add scripts/hooks.py
git commit -m "feat: hooks CLI run 子命令 — 支持从 tide-config.yaml 触发 hook"
```

---

### Task 10: 偏好学习 CLI 入口

**Files:**
- Modify: `scripts/preferences.py` — 新增 CLI `read`/`write` 子命令

- [ ] **Step 1: 添加 CLI 入口**

在 `preferences.py` 末尾新增：

```python
if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Tide preferences manager")
    sub = parser.add_subparsers(dest="command")

    read_p = sub.add_parser("read")
    read_p.add_argument("--key", help="Specific preference key to read")
    read_p.add_argument("--project-root", default=".")

    write_p = sub.add_parser("write")
    write_p.add_argument("--key", required=True)
    write_p.add_argument("--value", required=True)
    write_p.add_argument("--project-root", default=".")

    args = parser.parse_args()
    root = Path(args.project_root)

    if args.command == "read":
        prefs = load_preferences(root)
        if args.key:
            val = getattr(prefs, args.key, None)
            if val is not None:
                print(val)
            else:
                print(f"Unknown key: {args.key}", file=sys.stderr)
                sys.exit(1)
        else:
            print(prefs.model_dump_json(indent=2))
    elif args.command == "write":
        value: str | int | bool = args.value
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)
        update_preferences(root, **{args.key: value})
        print(f"Set {args.key} = {value}")
    else:
        parser.print_help()
```

- [ ] **Step 2: 验证 CLI 可用**

```bash
uv run python3 scripts/preferences.py write --key skip_user_confirmation --value true --project-root /tmp
uv run python3 scripts/preferences.py read --project-root /tmp
```

Expected: 读取到刚写入的偏好。

- [ ] **Step 3: 提交**

```bash
git add scripts/preferences.py
git commit -m "feat: preferences CLI read/write 子命令"
```

---

### Phase 3: UX 优化（子项目 D）

---

### Task 11: 时间预估 + 隐私提示 + 错误恢复

- [ ] **Step 1: 验证 Phase 0-2 所有测试通过**

```bash
uv run pytest tests/ -v --no-cov
```

- [ ] **Step 2: 最终提交（记录所有已完成变更）**

```bash
git add -A
git status
git commit -m "feat: 全面优化 — 按需加载 SKILL + 基础设施接入 + 代码质量 + UX 增强"
```

---

## 自检清单

- [ ] 每个 SKILL.md 不超过 250 行（按需加载原则）
- [ ] 所有 agents/*.md 是 prompt 唯一来源（无内联重复）
- [ ] 所有内联 python3 -c 已抽取到 scripts/*.py
- [ ] hooks/preferences 有 CLI 入口且接入流程
- [ ] FC03-FC06/FC10 已实现并通过测试
- [ ] 版本号 pyproject.toml / plugin.json / README 一致
- [ ] 集成测试覆盖 HAR→state→archive 链路
- [ ] `uv run pytest tests/ -v --no-cov` 全部通过
