"""Tests for scaffold generator — TDD (write first, implement second)."""
from pathlib import Path

from scripts.scaffold import ScaffoldConfig, append_to_existing_project, generate_project


class TestGenerateProject:
    def _make_config(
        self,
        tmp_path: Path,
        *,
        project_name: str = "my-api",
        base_url: str = "http://172.16.115.247",
        db_configured: bool = False,
    ) -> ScaffoldConfig:
        return ScaffoldConfig(
            project_root=tmp_path,
            project_name=project_name,
            base_url=base_url,
            db_configured=db_configured,
        )

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        """应创建完整的测试和核心目录结构。"""
        config = self._make_config(tmp_path)
        generate_project(config)

        assert (tmp_path / "tests" / "interface").is_dir()
        assert (tmp_path / "tests" / "scenariotest").is_dir()
        assert (tmp_path / "tests" / "unittest").is_dir()
        assert (tmp_path / "core").is_dir()
        assert (tmp_path / "core" / "models").is_dir()

    def test_creates_pyproject_toml(self, tmp_path: Path) -> None:
        """应生成包含项目名称且不含 pymysql 的 pyproject.toml。"""
        config = self._make_config(tmp_path, project_name="billing")
        generate_project(config)

        content = (tmp_path / "pyproject.toml").read_text()
        assert "billing-tests" in content
        assert "pymysql" not in content

    def test_includes_pymysql_when_db_configured(self, tmp_path: Path) -> None:
        """配置数据库时，pyproject.toml 应包含 pymysql。"""
        config = self._make_config(tmp_path, db_configured=True)
        generate_project(config)

        content = (tmp_path / "pyproject.toml").read_text()
        assert "pymysql" in content

    def test_creates_conftest(self, tmp_path: Path) -> None:
        """应创建 tests/conftest.py 文件。"""
        config = self._make_config(tmp_path)
        generate_project(config)

        assert (tmp_path / "tests" / "conftest.py").is_file()

    def test_creates_core_files(self, tmp_path: Path) -> None:
        """应创建核心模块文件：__init__.py、client.py、assertions.py。"""
        config = self._make_config(tmp_path)
        generate_project(config)

        assert (tmp_path / "core" / "__init__.py").is_file()
        assert (tmp_path / "core" / "client.py").is_file()
        assert (tmp_path / "core" / "assertions.py").is_file()
        assert (tmp_path / "core" / "models" / "__init__.py").is_file()

    def test_does_not_overwrite_existing(self, tmp_path: Path) -> None:
        """已存在的文件不应被覆盖。"""
        config = self._make_config(tmp_path)
        # 预先创建包含哨兵内容的 pyproject.toml
        (tmp_path / "pyproject.toml").write_text("existing content")
        generate_project(config)

        content = (tmp_path / "pyproject.toml").read_text()
        assert content == "existing content"

    def test_creates_gitignore(self, tmp_path: Path) -> None:
        """应创建包含常用忽略规则的 .gitignore 文件。"""
        config = self._make_config(tmp_path)
        generate_project(config)

        content = (tmp_path / ".gitignore").read_text()
        assert ".autoflow/" in content
        assert ".repos/" in content
        assert ".env" in content

    def test_creates_makefile(self, tmp_path: Path) -> None:
        """应创建包含标准测试目标的 Makefile。"""
        config = self._make_config(tmp_path)
        generate_project(config)

        content = (tmp_path / "Makefile").read_text()
        assert "test-all" in content
        assert "test-interface" in content


class TestGenerateProjectContent:
    def _make_config(self, tmp_path: Path, **kwargs) -> ScaffoldConfig:
        defaults = {
            "project_root": tmp_path,
            "project_name": "test-api",
            "base_url": "http://localhost:8080",
            "db_configured": False,
        }
        defaults.update(kwargs)
        return ScaffoldConfig(**defaults)

    def test_conftest_contains_api_client_fixture(self, tmp_path: Path) -> None:
        """conftest.py 应包含 api_client fixture。"""
        config = self._make_config(tmp_path)
        generate_project(config)
        content = (tmp_path / "tests" / "conftest.py").read_text()
        assert "api_client" in content or "APIClient" in content

    def test_conftest_contains_base_url(self, tmp_path: Path) -> None:
        """conftest.py 应包含配置的 base_url。"""
        config = self._make_config(tmp_path, base_url="http://10.0.0.1:9090")
        generate_project(config)
        content = (tmp_path / "tests" / "conftest.py").read_text()
        assert "10.0.0.1:9090" in content

    def test_client_py_is_immutable(self, tmp_path: Path) -> None:
        """client.py 应使用 frozen=True 的 dataclass。"""
        config = self._make_config(tmp_path)
        generate_project(config)
        content = (tmp_path / "core" / "client.py").read_text()
        assert "frozen=True" in content

    def test_gitignore_appends_without_overwrite(self, tmp_path: Path) -> None:
        """已存在的 .gitignore 应追加而非覆盖。"""
        existing = "*.pyc\n__pycache__/\n"
        (tmp_path / ".gitignore").write_text(existing)
        config = self._make_config(tmp_path)
        append_to_existing_project(config)
        content = (tmp_path / ".gitignore").read_text()
        assert "*.pyc" in content  # 原有内容保留
        assert ".autoflow/" in content  # 新内容追加
