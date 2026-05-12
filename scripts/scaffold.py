"""脚手架生成器 — 从 Jinja2 模板创建新的项目目录结构。"""
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from scripts.common import TIDE_DIR, REPOS_DIR, TRASH_DIR

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

_CLIENT_PY = '''\
"""HTTP 客户端 — httpx 的不可变封装。"""
from dataclasses import dataclass, field
import httpx

@dataclass(frozen=True)
class APIClient:
    base_url: str
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0

    def _build_client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, headers=self.headers, timeout=self.timeout)

    def get(self, path: str, **kwargs) -> httpx.Response:
        with self._build_client() as c:
            return c.get(path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        with self._build_client() as c:
            return c.post(path, **kwargs)

    def put(self, path: str, **kwargs) -> httpx.Response:
        with self._build_client() as c:
            return c.put(path, **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        with self._build_client() as c:
            return c.delete(path, **kwargs)
'''

_ASSERTIONS_PY = '''\
"""L1-L5 断言辅助函数。"""
import httpx

def assert_protocol(  # noqa: E501
    response: httpx.Response,
    *,
    expected_status: int = 200,
    max_time_ms: int = 5000,
    expected_content_type: str = "application/json",
) -> None:
    assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
    elapsed_ms = response.elapsed.total_seconds() * 1000
    assert elapsed_ms <= max_time_ms, f"Response too slow: {elapsed_ms:.0f}ms > {max_time_ms}ms"
    content_type = response.headers.get("content-type", "")
    assert expected_content_type in content_type, f"Content-Type mismatch: {content_type}"
'''

_DB_PY = '''\
"""数据库查询辅助类 — 只读，用于断言验证。"""
from dataclasses import dataclass
import pymysql
from urllib.parse import urlparse

@dataclass(frozen=True)
class DBHelper:
    url: str

    def _connect(self):
        parsed = urlparse(self.url)
        return pymysql.connect(  # noqa: E501
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip("/"),
            cursorclass=pymysql.cursors.DictCursor,
        )

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()
        finally:
            conn.close()

    def query_all(self, sql: str, params: tuple = ()) -> list[dict]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            conn.close()

    def count(self, table: str, where: str = "1=1", params: tuple = ()) -> int:
        result = self.query_one(f"SELECT COUNT(*) as cnt FROM {table} WHERE {where}", params)
        return result["cnt"] if result else 0
'''

_GITIGNORE = """\
__pycache__/
*.py[cod]
.venv/
.tide/
.repos/
.env
htmlcov/
reports/
.pytest_cache/
*.egg-info/
dist/
"""

_MAKEFILE = """\
.PHONY: test-all test-interface test-scenario test-unit report lint typecheck

test-all:
\tuv run pytest tests/ -v

test-interface:
\tuv run pytest tests/interface/ -v -m interface

test-scenario:
\tuv run pytest tests/scenariotest/ -v -m scenario

test-unit:
\tuv run pytest tests/unittest/ -v -m unit

report:
\tuv run pytest tests/ --alluredir=reports/allure-results
\tallure serve reports/allure-results

lint:
\tuv run ruff check .
\tuv run ruff format --check .

typecheck:
\tuv run pyright .
"""


@dataclass(frozen=True)
class ScaffoldConfig:
    project_root: Path
    project_name: str
    base_url: str
    db_configured: bool = False
    config_vars: dict = field(default_factory=dict)


def _write_if_not_exists(path: Path, content: str) -> bool:
    """仅在文件不存在时才将内容写入指定路径。

    若文件被写入则返回 True，若文件已存在则返回 False。
    """
    if path.exists():
        return False
    path.write_text(content)
    return True


def _render_tide_config(
    root: Path, env: Environment, config_vars: dict, created: list[str]
) -> None:
    """渲染 tide-config.yaml，若模板存在且文件不存在则创建。"""
    template_path = TEMPLATES_DIR / "tide-config.yaml.j2"
    if not template_path.exists():
        warnings.warn(f"Template not found: {template_path}", stacklevel=2)
        return
    content = env.get_template("tide-config.yaml.j2").render(**config_vars)
    if _write_if_not_exists(root / "tide-config.yaml", content):
        created.append("tide-config.yaml")


def append_to_existing_project(config: ScaffoldConfig) -> list[str]:
    """为已有项目追加 Tide 必需文件，不覆盖现有结构。"""
    root = config.project_root
    created: list[str] = []

    # 1. 只创建 .tide 目录
    for d in [TIDE_DIR, REPOS_DIR, TRASH_DIR]:
        (root / d).mkdir(parents=True, exist_ok=True)

    # 2. 追加 .gitignore 条目（不覆盖）
    gitignore_path = root / ".gitignore"
    tide_entries = [".tide/", ".repos/"]
    if gitignore_path.exists():
        existing = gitignore_path.read_text()
        new_entries = [e for e in tide_entries if e not in existing]
        if new_entries:
            with open(gitignore_path, "a") as f:
                f.write("\n# Tide\n")
                for entry in new_entries:
                    f.write(entry + "\n")
            created.append(".gitignore (appended)")
    else:
        gitignore_path.write_text(_GITIGNORE)
        created.append(".gitignore")

    # 3. tide-config.yaml（若有配置变量）
    if config.config_vars:
        config_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), keep_trailing_newline=True)
        _render_tide_config(root, config_env, config.config_vars, created)

    return created


def generate_project(config: ScaffoldConfig) -> list[str]:
    """从模板生成脚手架项目。

    返回已创建的文件路径列表（相对于 project_root）。
    """
    root = config.project_root
    created: list[str] = []

    # 1. 创建目录结构
    dirs = [
        "tests/interface",
        "tests/scenariotest",
        "tests/unittest",
        "core/models",
        TIDE_DIR,
        REPOS_DIR,
        TRASH_DIR,
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)

    # 2. 渲染 Jinja2 模板
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), keep_trailing_newline=True)
    template_vars = {
        "project_name": config.project_name,
        "base_url": config.base_url,
        "db_configured": config.db_configured,
    }

    pyproject_content = env.get_template("pyproject.toml.j2").render(**template_vars)
    if _write_if_not_exists(root / "pyproject.toml", pyproject_content):
        created.append("pyproject.toml")

    conftest_content = env.get_template("conftest.py.j2").render(**template_vars)
    if _write_if_not_exists(root / "tests" / "conftest.py", conftest_content):
        created.append("tests/conftest.py")

    # 3. 原样复制 .env.example
    env_example_src = TEMPLATES_DIR / ".env.example"
    env_example_dst = root / ".env.example"
    if env_example_src.exists():
        if _write_if_not_exists(env_example_dst, env_example_src.read_text()):
            created.append(".env.example")
    else:
        warnings.warn(f"Template not found: {env_example_src}", stacklevel=2)

    # 4. 静态 __init__.py 文件
    init_files = [
        "core/__init__.py",
        "core/models/__init__.py",
        "tests/interface/__init__.py",
        "tests/scenariotest/__init__.py",
        "tests/unittest/__init__.py",
    ]
    for rel in init_files:
        if _write_if_not_exists(root / rel, ""):
            created.append(rel)

    # 5. core/client.py
    if _write_if_not_exists(root / "core" / "client.py", _CLIENT_PY):
        created.append("core/client.py")

    # 6. core/assertions.py
    if _write_if_not_exists(root / "core" / "assertions.py", _ASSERTIONS_PY):
        created.append("core/assertions.py")

    # 7. core/db.py（仅在配置了数据库时创建）
    if config.db_configured and _write_if_not_exists(root / "core" / "db.py", _DB_PY):
        created.append("core/db.py")

    # 8. .gitignore
    if _write_if_not_exists(root / ".gitignore", _GITIGNORE):
        created.append(".gitignore")

    # 9. Makefile
    if _write_if_not_exists(root / "Makefile", _MAKEFILE):
        created.append("Makefile")

    # 10. tide-config.yaml（若有配置变量）
    if config.config_vars:
        _render_tide_config(root, env, config.config_vars, created)

    return created


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", default="recommended")
    parser.add_argument("--base-url", default="http://localhost")
    parser.add_argument("--mode", choices=["new", "existing"], default="new")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    config = ScaffoldConfig(
        project_root=Path(args.project_root),
        project_name=Path(args.project_root).name,
        base_url=args.base_url,
    )

    created = append_to_existing_project(config) if args.mode == "existing" else generate_project(config)

    for f in created:
        print(f"  created: {f}")
