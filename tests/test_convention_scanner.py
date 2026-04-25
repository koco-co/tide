"""Tests for convention scanner."""
from pathlib import Path

from scripts.convention_scanner import (
    detect_api_pattern,
    detect_assertion_style,
    detect_env_management,
    detect_http_client,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestDetectApiPattern:
    def test_detects_enum_pattern(self, tmp_path: Path) -> None:
        api_dir = tmp_path / "api" / "batch"
        api_dir.mkdir(parents=True)
        (api_dir / "__init__.py").write_text("")
        (api_dir / "batch_api.py").write_text(
            "from enum import Enum\nclass BatchApi(Enum):\n    get_task = '/path'"
        )
        result = detect_api_pattern(tmp_path)
        assert result["type"] == "enum"
        assert len(result["modules"]) == 1
        assert result["modules"][0]["class"] == "BatchApi"

    def test_detects_inline_when_no_api_dir(self, tmp_path: Path) -> None:
        result = detect_api_pattern(tmp_path)
        assert result["type"] == "inline"

    def test_detects_dict_when_no_enum(self, tmp_path: Path) -> None:
        api_dir = tmp_path / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "endpoints.py").write_text("ENDPOINTS = {'url': '/path'}")
        result = detect_api_pattern(tmp_path)
        assert result["type"] == "dict"

    def test_detects_constant_pattern(self, tmp_path: Path) -> None:
        api_dir = tmp_path / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "urls.py").write_text("BATCH_API_URL = '/api/batch'")
        result = detect_api_pattern(tmp_path)
        assert result["type"] == "constant"

    def test_detects_enum_enum_import_style(self, tmp_path: Path) -> None:
        """Support both 'from enum import Enum' and 'import enum'."""
        api_dir = tmp_path / "api" / "batch"
        api_dir.mkdir(parents=True)
        (api_dir / "__init__.py").write_text("")
        (api_dir / "batch_api.py").write_text(
            "import enum\nclass BatchApi(enum.Enum):\n    get_task = '/path'"
        )
        result = detect_api_pattern(tmp_path)
        assert result["type"] == "enum"


class TestDetectHttpClient:
    def test_detects_requests(self, tmp_path: Path) -> None:
        (tmp_path / "test_a.py").write_text("import requests\nrequests.get('/url')")
        result = detect_http_client(tmp_path)
        assert result["library"] == "requests"
        assert result["client_pattern"] == "direct"

    def test_detects_session_usage(self, tmp_path: Path) -> None:
        (tmp_path / "test_b.py").write_text(
            "import requests\nsession = requests.Session()\nsession.get('/url')"
        )
        result = detect_http_client(tmp_path)
        assert result["library"] == "requests"
        assert result["client_pattern"] == "session"

    def test_detects_custom_class(self, tmp_path: Path) -> None:
        (tmp_path / "base.py").write_text(
            "class BaseRequests:\n    def post(self, url, **kwargs): ..."
        )
        result = detect_http_client(tmp_path)
        assert result["library"] == "unknown"
        assert result["client_pattern"] == "custom_class"
        assert result["custom_class"] == "BaseRequests"
        detail = result["custom_class_detail"]
        assert detail["name"] == "BaseRequests"
        assert isinstance(detail["module"], str) and len(detail["module"]) > 0
        method = detail.get("method")
        assert method is not None, "custom_class_detail.method should not be None"
        assert method["has_desc_param"] is False
        assert "self" in method["signature"]
        assert "url" in method["signature"]

    def test_ignores_venv(self, tmp_path: Path) -> None:
        """Files in .venv should be excluded."""
        venv_dir = tmp_path / ".venv" / "site-packages"
        venv_dir.mkdir(parents=True)
        (venv_dir / "lib.py").write_text("import httpx\nhttpx.get('/url')")
        (tmp_path / "test.py").write_text("import requests")
        result = detect_http_client(tmp_path)
        assert result["library"] == "requests"


class TestDetectAssertionStyle:
    def test_detects_dict_get(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_x.py"
        test_file.write_text(
            "def test_x():\n"
            "    resp = {'code': 1}\n"
            "    assert resp.get('code') == 1\n"
        )
        result = detect_assertion_style(tmp_path, project_root=tmp_path)
        assert result["style"] == "dict_get"

    def test_detects_bracket(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_y.py"
        test_file.write_text(
            "def test_y():\n"
            "    resp = {'code': 0}\n"
            "    assert resp['code'] == 0\n"
        )
        result = detect_assertion_style(tmp_path, project_root=tmp_path)
        assert result["style"] == "bracket"

    def test_empty_dir_returns_unknown(self, tmp_path: Path) -> None:
        result = detect_assertion_style(tmp_path, project_root=tmp_path)
        assert result["style"] == "unknown"

    def test_status_only(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_z.py"
        test_file.write_text(
            "def test_z():\n"
            "    resp = mock_response()\n"
            "    assert resp.status_code == 200\n"
        )
        result = detect_assertion_style(tmp_path, project_root=tmp_path)
        assert result["style"] == "status_only"

    def test_detects_code_success(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_code.py"
        test_file.write_text(
            "def test():\n"
            '    assert resp["code"] == 1\n'
        )
        result = detect_assertion_style(tmp_path, project_root=tmp_path)
        assert result["has_code_success"] is True


class TestDetectEnvManagement:
    def test_detect_env_management(self, tmp_path: Path) -> None:
        """检测多环境配置。"""
        env_dir = tmp_path / "config" / "env"
        env_dir.mkdir(parents=True)
        (env_dir / "ci_62.ini").write_text("[base]\nurl=http://ci-62.com\n")
        (env_dir / "ci_63.ini").write_text("[base]\nurl=http://ci-63.com\n")
        env_file = tmp_path / ".env"
        env_file.write_text("env_file = config/env/ci_63.ini\n")

        result = detect_env_management(tmp_path)
        assert result["detected"] is True
        assert result["count"] == 2
        assert result["switch_method"] == "dotenv"
        assert result["active"] == "ci_63"

    def test_detect_env_management_no_env(self, tmp_path: Path) -> None:
        """没有多环境配置时返回 detected=False。"""
        result = detect_env_management(tmp_path)
        assert result["detected"] is False
