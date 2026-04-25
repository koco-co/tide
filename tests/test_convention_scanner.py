"""Tests for convention scanner."""
from pathlib import Path

from scripts.convention_scanner import (
    detect_api_pattern,
    detect_assertion_style,
    detect_auth_flow,
    detect_conftest_chain,
    detect_env_management,
    detect_http_client,
    detect_module_dependencies,
    detect_monitoring,
    detect_service_utilities,
    detect_test_runner,
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

    def test_detect_env_management_with_config_module(self, tmp_path: Path) -> None:
        """检测 config_module 派生逻辑。"""
        env_dir = tmp_path / "config" / "env"
        env_dir.mkdir(parents=True)
        (env_dir / "ci_62.ini").write_text("[base]\nurl=http://ci-62.com\n")
        env_config_dir = tmp_path / "config"
        (env_config_dir / "env_config.py").write_text("ENV_CONF = 'test'")
        result = detect_env_management(tmp_path)
        assert result["detected"] is True
        assert result["config_module"] == "config.env_config"

    def test_detect_env_management_no_env(self, tmp_path: Path) -> None:
        """没有多环境配置时返回 detected=False。"""
        result = detect_env_management(tmp_path)
        assert result["detected"] is False


class TestDetectTestRunner:
    def test_detect_custom_runner_with_module_entries(self, tmp_path: Path) -> None:
        runner = tmp_path / "run_demo.py"
        runner.write_text('''
class Run:
    def run_batch_scenariotest(self):
        runner.run_with_option(rerun=1, test_path="...", workers=8)
    def run_stream_scenariotest(self):
        pass
''')
        result = detect_test_runner(tmp_path)
        assert result["type"] == "custom"
        assert result["entry"] == "run_demo.py"
        assert "batch" in result["module_entries"]

    def test_detect_pytest_direct_when_no_runner(self, tmp_path: Path) -> None:
        result = detect_test_runner(tmp_path)
        assert result["type"] == "pytest_direct"
        assert result["entry"] is None

    def test_detect_parallel_and_reruns_options(self, tmp_path: Path) -> None:
        runner = tmp_path / "run.py"
        runner.write_text('''
if __name__ == "__main__":
    pytest.main(["-n", "4", "--reruns=2", "--alluredir=allure-results"])
''')
        result = detect_test_runner(tmp_path)
        assert result["type"] == "custom"
        assert result["entry"] == "run.py"
        assert result["options"]["parallel"] is True
        assert result["options"]["reruns"] == 2
        assert "allure" in result["options"]["report"]

    def test_detect_runner_txt_name(self, tmp_path: Path) -> None:
        runner = tmp_path / "runner.py"
        runner.write_text("print('runner')\n")
        result = detect_test_runner(tmp_path)
        assert result["type"] == "custom"
        assert result["entry"] == "runner.py"

    def test_detect_workers_extraction(self, tmp_path: Path) -> None:
        """测试从 runner 中提取 workers 数量。"""
        runner = tmp_path / "run_demo.py"
        runner.write_text('''
import pytest
if __name__ == "__main__":
    pytest.main(["-n", "auto", "--reruns=1"])
class Run:
    def run_batch_scenariotest(self):
        runner.run_with_option(workers=8, test_path="...")
''')
        result = detect_test_runner(tmp_path)
        assert result["options"]["parallel"] is True
        assert result["options"]["workers"] == 8


class TestDetectConftestChain:
    def test_detect_conftest_chain(self, tmp_path: Path) -> None:
        root = tmp_path / "conftest.py"
        root.write_text("""
import pytest
@pytest.fixture
def client(): ...
@pytest.fixture
def db(): ...
""")
        result = detect_conftest_chain(tmp_path)
        assert len(result["layers"]) >= 1
        assert "client" in result["fixture_types"].get("other", [])

    def test_detect_conftest_chain_none(self, tmp_path: Path) -> None:
        result = detect_conftest_chain(tmp_path)
        assert result["layers"] == []
        assert result["fixture_count"] == 0


class TestDetectMonitoring:
    def test_detect_monitoring(self, tmp_path: Path) -> None:
        base = tmp_path / "utils/common"
        base.mkdir(parents=True)
        (base / "base.py").write_text('''
def calc_request_time_and_alarm(func):
    def wrapper(*args, **kwargs):
        cost_time = 3.5
        if cost_time > 3:
            send_ding_talk("alert")
        return func(*args, **kwargs)
    return wrapper
''')
        result = detect_monitoring(tmp_path)
        assert result["detected"] is True
        assert "dingtalk" in result.get("alert_channels", [])

    def test_detect_monitoring_none(self, tmp_path: Path) -> None:
        result = detect_monitoring(tmp_path)
        assert result["detected"] is False


class TestDetectAuthFlow:
    def test_detect_auth_flow_no_auth(self, tmp_path: Path) -> None:
        """无认证文件时返回 method=none。"""
        result = detect_auth_flow(tmp_path)
        assert result["method"] == "none"

    def test_detect_auth_flow_cookie(self, tmp_path: Path) -> None:
        utils = tmp_path / "utils" / "common"
        utils.mkdir(parents=True)
        auth_file = utils / "get_cookies.py"
        auth_file.write_text('''
class BaseCookies:
    def get_public_key(self): ...
    def login(self): ...
    def refresh(self): ...
from config.env_config import ENV_CONF
''')
        (tmp_path / "conftest.py").write_text("import pytest")
        result = detect_auth_flow(tmp_path)
        assert result["method"] == "cookie"
        assert result["auth_class"] == "BaseCookies"
        assert result["flow"] is not None
        assert "login" in result["flow"]

    def test_detect_auth_flow_none(self, tmp_path: Path) -> None:
        result = detect_auth_flow(tmp_path)
        assert result["method"] == "none"
        assert result["flow"] is None


class TestDetectModuleDependencies:
    def test_detect_module_dependencies(self, tmp_path: Path) -> None:
        for mod in ["batch", "dataapi", "uic"]:
            (tmp_path / "api" / mod).mkdir(parents=True)
            (tmp_path / "api" / mod / "__init__.py").write_text("")
        result = detect_module_dependencies(tmp_path)
        assert result["count"] == 3
        names = [m["name"] for m in result["modules"]]
        assert "batch" in names

    def test_detect_module_dependencies_none(self, tmp_path: Path) -> None:
        result = detect_module_dependencies(tmp_path)
        assert result["count"] == 0


class TestDetectServiceUtilities:
    """Service/Request 工具类扫描测试"""

    def test_detects_services_and_requests(self, tmp_path: Path) -> None:
        utils_services = tmp_path / "utils" / "assets" / "services"
        utils_services.mkdir(parents=True)
        (utils_services / "__init__.py").write_text("")
        (utils_services / "datasource.py").write_text("""
class DatasourceService:
    \"\"\"数据源服务\"\"\"
    def get_datasource_id_by_name(self, datasource_name):
        \"\"\"根据名称查ID\"\"\"
        pass
    def import_datasource(self, ds_id):
        \"\"\"导入数据源\"\"\"
        pass
""")
        utils_requests = tmp_path / "utils" / "assets" / "requests"
        utils_requests.mkdir(parents=True)
        (utils_requests / "__init__.py").write_text("")
        (utils_requests / "meta_data_requests.py").write_text("""
class MetaDataRequest:
    \"\"\"元数据请求\"\"\"
    def page_table_column(self, table_id):
        \"\"\"分页查字段\"\"\"
        pass
""")
        result = detect_service_utilities(tmp_path)
        assert result["detected"] is True
        assert "assets" in result["modules"]
        assert len(result["modules"]["assets"]["services"]) == 1
        assert len(result["modules"]["assets"]["requests"]) == 1

        svc = result["modules"]["assets"]["services"][0]
        assert svc["class"] == "DatasourceService"
        assert len(svc["methods"]) == 2
        assert svc["methods"][0]["name"] == "get_datasource_id_by_name"

        req = result["modules"]["assets"]["requests"][0]
        assert req["class"] == "MetaDataRequest"
        assert req["methods"][0]["name"] == "page_table_column"

    def test_no_utils_dir_returns_not_detected(self, tmp_path: Path) -> None:
        result = detect_service_utilities(tmp_path)
        assert result["detected"] is False
        assert result["modules"] == {}

    def test_skips_init_py(self, tmp_path: Path) -> None:
        """仅有 __init__.py 的目录被视为无有效工具类。"""
        utils_dir = tmp_path / "utils" / "assets" / "services"
        utils_dir.mkdir(parents=True)
        (utils_dir / "__init__.py").write_text("# empty")
        result = detect_service_utilities(tmp_path)
        assert result["detected"] is False

    def test_method_signature_parsing(self, tmp_path: Path) -> None:
        utils_dir = tmp_path / "utils" / "test" / "services"
        utils_dir.mkdir(parents=True)
        (utils_dir / "svc.py").write_text("""
from typing import Optional

class QueryService:
    def get_by_name(self, name: str, age: int = 0) -> Optional[dict]:
        \"\"\"按名称查询\"\"\"
        pass
""")
        result = detect_service_utilities(tmp_path)
        svc = result["modules"]["test"]["services"][0]
        m = svc["methods"][0]
        assert m["name"] == "get_by_name"
        assert m["args"] == [
            {"name": "name", "type": "str"},
            {"name": "age", "type": "int"},
        ]
        assert m["returns"] == "Optional[dict]"
        assert m["doc"] == "按名称查询"

    def test_skips_test_classes(self, tmp_path: Path) -> None:
        utils_dir = tmp_path / "utils" / "test" / "services"
        utils_dir.mkdir(parents=True)
        (utils_dir / "svc.py").write_text("""
class TestHelperService:
    def helper_method(self): pass
class RealService:
    def real_method(self): pass
""")
        result = detect_service_utilities(tmp_path)
        classes = result["modules"]["test"]["services"]
        names = [c["class"] for c in classes]
        assert "TestHelperService" not in names
        assert "RealService" in names
