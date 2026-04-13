"""Tests for HAR parser - written first (TDD RED phase)."""

import base64
import json
from pathlib import Path

import pytest

from scripts.har_parser import (
    HarEntry,
    HarRequest,
    HarResponse,
    ParsedResult,
    dedup_entries,
    filter_entries,
    match_repo,
    parse_har,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _make_entry(
    method: str = "POST",
    url: str = "http://172.16.115.247/dassets/v1/datamap/recentQuery",
    req_body: str = "{}",
    resp_status: int = 200,
    resp_body: str = '{"ok":true}',
    resp_mime: str = "application/json",
    time_ms: float = 50,
) -> dict:
    return {
        "time": time_ms,
        "request": {
            "method": method,
            "url": url,
            "httpVersion": "HTTP/1.1",
            "headers": [{"name": "Content-Type", "value": "application/json"}],
            "queryString": [],
            "postData": {"mimeType": "application/json", "text": req_body},
            "headersSize": -1,
            "bodySize": len(req_body),
        },
        "response": {
            "status": resp_status,
            "statusText": "OK",
            "httpVersion": "HTTP/1.1",
            "headers": [{"name": "Content-Type", "value": resp_mime}],
            "content": {"mimeType": resp_mime, "text": resp_body},
            "redirectURL": "",
            "headersSize": -1,
            "bodySize": -1,
        },
        "cache": {},
        "timings": {"send": 0, "wait": time_ms, "receive": 0},
    }


def _load_har_entries(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    return data["log"]["entries"]


# ---------------------------------------------------------------------------
# TestHarModels
# ---------------------------------------------------------------------------


class TestHarModels:
    def test_har_request_from_entry(self) -> None:
        """将原始字典解析为 HarRequest 并验证 method / url / body。"""
        raw = _make_entry(method="POST", req_body='{"keyword":"test"}')
        req = HarRequest(**raw["request"])

        assert req.method == "POST"
        assert "recentQuery" in req.url
        assert req.body == {"keyword": "test"}

    def test_har_response_from_entry(self) -> None:
        """将原始字典解析为 HarResponse 并验证 status / body。"""
        raw = _make_entry(resp_status=200, resp_body='{"code":1,"success":true}')
        resp = HarResponse(**raw["response"])

        assert resp.status == 200
        assert resp.body == {"code": 1, "success": True}

    def test_har_request_body_plain_text(self) -> None:
        """非 JSON 的 postData.text 应返回 body=None。"""
        raw = _make_entry(req_body="plain text, not json")
        req = HarRequest(**raw["request"])
        assert req.body is None

    def test_har_response_time_zero(self) -> None:
        """time_ms=0 的条目应正常解析。"""
        raw = _make_entry(time_ms=0.0)
        entry = HarEntry(**raw)
        assert entry.time == 0.0

    def test_har_request_path_extraction(self) -> None:
        """path 属性应正确提取 URL 路径部分。"""
        raw = _make_entry(url="http://example.com/api/v1/users?page=1")
        req = HarRequest(**raw["request"])
        assert req.path == "/api/v1/users"

    def test_har_request_content_type(self) -> None:
        """content_type 属性应返回小写值。"""
        raw = _make_entry()
        req = HarRequest(**raw["request"])
        assert req.content_type == "application/json"

    def test_har_response_base64_encoded(self) -> None:
        """透明处理 base64 编码的响应内容。"""
        payload = {"data": "binary-like"}
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        raw_resp = {
            "status": 200,
            "statusText": "OK",
            "httpVersion": "HTTP/1.1",
            "headers": [{"name": "Content-Type", "value": "application/json"}],
            "content": {
                "mimeType": "application/json",
                "text": encoded,
                "encoding": "base64",
            },
            "redirectURL": "",
            "headersSize": -1,
            "bodySize": -1,
        }
        resp = HarResponse(**raw_resp)
        assert resp.body == payload


# ---------------------------------------------------------------------------
# TestFilterEntries
# ---------------------------------------------------------------------------


class TestFilterEntries:
    def test_keeps_json_api_requests(self, sample_har_path: Path) -> None:
        """sample.har 包含 3 条干净的 JSON API 条目，过滤后应全部保留。"""
        entries_raw = _load_har_entries(sample_har_path)
        entries = [HarEntry(**e) for e in entries_raw]
        filtered = filter_entries(entries)
        assert len(filtered) == 3

    def test_drops_static_resources(self, sample_dirty_har_path: Path) -> None:
        """过滤后，路径中不应存在 .js / .css 扩展名的条目。"""
        entries_raw = _load_har_entries(sample_dirty_har_path)
        entries = [HarEntry(**e) for e in entries_raw]
        filtered = filter_entries(entries)

        paths = [e.request.path for e in filtered]
        assert not any(p.endswith(".js") or p.endswith(".css") for p in paths)

    def test_drops_websocket(self, sample_dirty_har_path: Path) -> None:
        """WebSocket 升级响应（状态码 101）必须被丢弃。"""
        entries_raw = _load_har_entries(sample_dirty_har_path)
        entries = [HarEntry(**e) for e in entries_raw]
        filtered = filter_entries(entries)

        statuses = [e.response.status for e in filtered]
        assert 101 not in statuses

    def test_drops_hot_update(self, sample_dirty_har_path: Path) -> None:
        """包含 'hot-update' 噪声的路径必须被丢弃。"""
        entries_raw = _load_har_entries(sample_dirty_har_path)
        entries = [HarEntry(**e) for e in entries_raw]
        filtered = filter_entries(entries)

        paths = [e.request.path for e in filtered]
        assert not any("hot-update" in p for p in paths)


# ---------------------------------------------------------------------------
# TestDedupEntries
# ---------------------------------------------------------------------------


class TestDedupEntries:
    def test_dedup_preserves_different_status_codes(self) -> None:
        """不同状态码的条目不应被合并。"""
        entries = [
            HarEntry(**_make_entry(resp_status=200)),
            HarEntry(**_make_entry(resp_status=400)),
        ]
        result = dedup_entries(entries)
        assert len(result) == 2

    def test_dedup_preserves_different_bodies(self) -> None:
        """相同路径但不同请求体的条目不应被合并。"""
        entries = [
            HarEntry(**_make_entry(req_body='{"page":1}')),
            HarEntry(**_make_entry(req_body='{"page":2}')),
        ]
        result = dedup_entries(entries)
        assert len(result) == 2

    def test_dedup_merges_identical_entries(self) -> None:
        """完全相同的条目应合并为一条。"""
        entries = [
            HarEntry(**_make_entry()),
            HarEntry(**_make_entry()),
        ]
        result = dedup_entries(entries)
        assert len(result) == 1

    def test_merges_same_method_path(self, sample_dirty_har_path: Path) -> None:
        """相同 (method, path, status, body_hash) 的重复条目应合并为一条。"""
        entries_raw = _load_har_entries(sample_dirty_har_path)
        entries = [HarEntry(**e) for e in entries_raw]
        filtered = filter_entries(entries)
        deduped = dedup_entries(filtered)

        recent_query_entries = [
            e for e in deduped if "recentQuery" in e.request.path
        ]
        # recentQuery 有 3 种不同的 (method, path, status, body_hash) 组合
        # (空 body/200、keyword body/200、空 body/500) → 最多 3 条
        assert len(recent_query_entries) <= 3

    def test_keeps_different_status_codes(self, sample_dirty_har_path: Path) -> None:
        """路径相同但状态码不同的条目必须同时保留。"""
        entries_raw = _load_har_entries(sample_dirty_har_path)
        entries = [HarEntry(**e) for e in entries_raw]
        filtered = filter_entries(entries)
        deduped = dedup_entries(filtered)

        recent_query_entries = [
            e for e in deduped if "recentQuery" in e.request.path
        ]
        statuses = {e.response.status for e in recent_query_entries}
        assert 200 in statuses
        assert 500 in statuses


# ---------------------------------------------------------------------------
# TestMatchRepo
# ---------------------------------------------------------------------------


class TestMatchRepo:
    def test_matches_dassets_prefix(self, sample_repo_profiles_path: Path) -> None:
        import yaml

        profiles_data = yaml.safe_load(sample_repo_profiles_path.read_text())
        profiles = profiles_data["profiles"]

        name, branch = match_repo("/dassets/v1/datamap/recentQuery", profiles)
        assert name == "dt-center-assets"
        assert branch == "release_6.2.x"

    def test_matches_dmetadata_prefix(self, sample_repo_profiles_path: Path) -> None:
        import yaml

        profiles_data = yaml.safe_load(sample_repo_profiles_path.read_text())
        profiles = profiles_data["profiles"]

        name, branch = match_repo("/dmetadata/v1/syncTask/pageTask", profiles)
        assert name == "dt-center-metadata"
        assert branch == "release_6.2.x"

    def test_returns_none_for_unknown_prefix(
        self, sample_repo_profiles_path: Path
    ) -> None:
        import yaml

        profiles_data = yaml.safe_load(sample_repo_profiles_path.read_text())
        profiles = profiles_data["profiles"]

        name, branch = match_repo("/unknown/v1/something", profiles)
        assert name is None
        assert branch is None


# ---------------------------------------------------------------------------
# TestParseHar
# ---------------------------------------------------------------------------


class TestParseHar:
    def test_full_parse(
        self, sample_har_path: Path, sample_repo_profiles_path: Path
    ) -> None:
        """完整解析 sample.har 应得到 3 个端点及正确的元数据。"""
        result = parse_har(sample_har_path, sample_repo_profiles_path)

        assert isinstance(result, ParsedResult)
        assert len(result.endpoints) == 3
        assert result.base_url == "http://172.16.115.247"
        services = result.summary.services
        assert "dassets" in services
        assert "dmetadata" in services

    def test_endpoint_has_matched_repo(
        self, sample_har_path: Path, sample_repo_profiles_path: Path
    ) -> None:
        """每个 /dassets/… 端点的 matched_repo 必须为 dt-center-assets。"""
        result = parse_har(sample_har_path, sample_repo_profiles_path)

        dassets_endpoints = [
            e for e in result.endpoints if e.service == "dassets"
        ]
        assert len(dassets_endpoints) > 0
        for ep in dassets_endpoints:
            assert ep.matched_repo == "dt-center-assets"

    def test_raises_on_invalid_har(self, tmp_path: Path) -> None:
        """非 JSON 文件应抛出 ValueError('Invalid HAR')。"""
        bad_file = tmp_path / "bad.har"
        bad_file.write_text("this is not json at all")

        with pytest.raises(ValueError, match="Invalid HAR"):
            parse_har(bad_file, None)

    def test_parse_har_without_profiles(self, sample_har_path: Path) -> None:
        """profiles_path=None 时应正常解析，matched_repo 为 None。"""
        result = parse_har(sample_har_path, None)
        assert isinstance(result, ParsedResult)
        assert all(ep.matched_repo is None for ep in result.endpoints)

    def test_parse_har_missing_log_key(self, tmp_path: Path) -> None:
        """缺少 log 键的 JSON 应抛出 ValueError。"""
        bad_har = tmp_path / "bad.har"
        bad_har.write_text(json.dumps({"version": "1.2"}))
        with pytest.raises(ValueError, match="Invalid HAR"):
            parse_har(bad_har, None)

    def test_raises_on_empty_entries(self, tmp_path: Path) -> None:
        """条目为空的有效 HAR 应抛出 ValueError('No entries')。"""
        empty_har = {"log": {"version": "1.2", "entries": []}}
        empty_file = tmp_path / "empty.har"
        empty_file.write_text(json.dumps(empty_har))

        with pytest.raises(ValueError, match="No entries"):
            parse_har(empty_file, None)
