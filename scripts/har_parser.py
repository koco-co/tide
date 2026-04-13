"""HAR 解析器：将原始 HAR JSON 转换为结构化的 ParsedResult。

处理流程：加载 → 过滤条目 → 去重条目 → 匹配仓库 → 构建 ParsedResult
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# 从解析结果中剔除的敏感请求头
# ---------------------------------------------------------------------------
_SENSITIVE_HEADERS = frozenset({"cookie", "authorization", "x-auth-token"})

# ---------------------------------------------------------------------------
# 需要丢弃的静态资源扩展名
# ---------------------------------------------------------------------------
_STATIC_EXTS = frozenset(
    {".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
     ".woff", ".woff2", ".ttf", ".map"}
)

# ---------------------------------------------------------------------------
# 需要丢弃的噪声 URL 模式（子字符串匹配）
# ---------------------------------------------------------------------------
_NOISE_PATTERNS = ("hot-update", "sockjs", "__webpack", "source-map")


# ---------------------------------------------------------------------------
# Pydantic 模型定义
# ---------------------------------------------------------------------------


class HarHeader(BaseModel):
    name: str
    value: str


class HarRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    method: str
    url: str
    headers: list[HarHeader] = []
    post_data: dict | None = Field(default=None, alias="postData")

    # ---- 计算属性 ----

    @property
    def body(self) -> dict | None:
        """将 post_data.text 解析为 JSON；若不存在或非 JSON 则返回 None。"""
        if self.post_data is None:
            return None
        text = self.post_data.get("text")
        if not text:
            return None
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None

    @property
    def path(self) -> str:
        """URL 路径部分。"""
        return urlparse(self.url).path

    @property
    def content_type(self) -> str | None:
        """请求头中 Content-Type 的值（小写）。"""
        for h in self.headers:
            if h.name.lower() == "content-type":
                return h.value.lower()
        return None


class HarContent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mime_type: str = Field(default="", alias="mimeType")
    text: str | None = None
    encoding: str | None = None


class HarResponse(BaseModel):
    status: int
    headers: list[HarHeader] = []
    content: HarContent = HarContent()

    # ---- 计算属性 ----

    @property
    def body(self) -> dict | None:
        """将 content.text 解析为 JSON，支持可选的 base64 编码。"""
        text = self.content.text
        if not text:
            return None
        if self.content.encoding == "base64":
            try:
                text = base64.b64decode(text).decode()
            except Exception:
                return None
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None

    @property
    def content_type(self) -> str | None:
        """响应头中 Content-Type 的值（小写）。"""
        for h in self.headers:
            if h.name.lower() == "content-type":
                return h.value.lower()
        # 回退到 mime_type 字段
        if self.content.mime_type:
            return self.content.mime_type.lower()
        return None


class HarEntry(BaseModel):
    time: float = 0.0
    request: HarRequest
    response: HarResponse

    @model_validator(mode="before")
    @classmethod
    def _coerce_fields(cls, data: dict) -> dict:
        """接受包含额外字段（cache、timings 等）的原始 HAR 字典。"""
        return data


# ---------------------------------------------------------------------------
# 解析结果输出模型
# ---------------------------------------------------------------------------


class RepoProfile(BaseModel):
    name: str
    url: str = ""
    branch: str = "main"
    path: str = ""
    url_prefixes: list[str] = []


class RepoProfilesConfig(BaseModel):
    profiles: list[RepoProfile] = []


class ParsedEndpoint(BaseModel):
    id: str
    method: str
    path: str
    service: str
    module: str
    request: dict
    response: dict
    matched_repo: str | None
    matched_branch: str | None


class ParsedSummary(BaseModel):
    total_raw: int
    after_filter: int
    after_dedup: int
    services: list[str]
    modules: list[str]


class ParsedResult(BaseModel):
    source_har: str
    parsed_at: str
    base_url: str
    endpoints: list[ParsedEndpoint]
    summary: ParsedSummary


# ---------------------------------------------------------------------------
# filter_entries
# ---------------------------------------------------------------------------


def filter_entries(entries: list[HarEntry]) -> list[HarEntry]:
    """丢弃静态资源、WebSocket 升级、噪声模式及非 JSON 响应。"""
    result: list[HarEntry] = []
    for entry in entries:
        path = entry.request.path

        # 丢弃 WebSocket（状态码 101）
        if entry.response.status == 101:
            continue

        # 丢弃静态文件扩展名
        path_lower = path.lower()
        suffix = Path(path_lower).suffix
        if suffix in _STATIC_EXTS:
            continue

        # 丢弃噪声模式
        if any(pattern in path_lower for pattern in _NOISE_PATTERNS):
            continue

        # 仅保留 application/json 响应
        ct = entry.response.content_type or ""
        if "application/json" not in ct:
            continue

        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# dedup_entries
# ---------------------------------------------------------------------------


def _body_hash(body: dict | None) -> str:
    if body is None:
        return "null"
    return hashlib.md5(
        json.dumps(body, sort_keys=True).encode(), usedforsecurity=False
    ).hexdigest()


def dedup_entries(entries: list[HarEntry]) -> list[HarEntry]:
    """按 (method, path, status, body_hash) 去重；保留首次出现的条目。"""
    seen: set[str] = set()
    result: list[HarEntry] = []
    for entry in entries:
        key = ":".join([
            entry.request.method,
            entry.request.path,
            str(entry.response.status),
            _body_hash(entry.request.body),
        ])
        if key not in seen:
            seen.add(key)
            result.append(entry)
    return result


# ---------------------------------------------------------------------------
# match_repo
# ---------------------------------------------------------------------------


def match_repo(
    path: str, profiles: list[dict]
) -> tuple[str | None, str | None]:
    """将 *path* 与 profiles 中的 url_prefixes 进行匹配；返回 (name, branch) 或 (None, None)。"""
    for profile in profiles:
        for prefix in profile.get("url_prefixes", []):
            if path.startswith(prefix):
                return profile["name"], profile["branch"]
    return None, None


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


def _extract_service_module(path: str) -> tuple[str, str]:
    """从 URL 路径部分推导出 (service, module)。

    示例：/dassets/v1/datamap/recentQuery → service=dassets, module=datamap
    """
    parts = [p for p in path.split("/") if p]
    service = parts[0] if len(parts) > 0 else ""
    module = parts[2] if len(parts) > 2 else (parts[1] if len(parts) > 1 else "")
    return service, module


def _strip_sensitive_headers(headers: list[HarHeader]) -> list[dict]:
    return [
        {"name": h.name, "value": h.value}
        for h in headers
        if h.name.lower() not in _SENSITIVE_HEADERS
    ]


def _extract_base_url(entry: HarEntry) -> str:
    parsed = urlparse(entry.request.url)
    return f"{parsed.scheme}://{parsed.netloc}"


# ---------------------------------------------------------------------------
# parse_har
# ---------------------------------------------------------------------------


def parse_har(
    har_path: Path,
    profiles_path: Path | None,
) -> ParsedResult:
    """加载、验证、过滤、去重并丰富 HAR 条目，生成 ParsedResult。"""
    # --- 加载 ---
    try:
        raw = json.loads(har_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Invalid HAR: {exc}") from exc

    if "log" not in raw or "entries" not in raw.get("log", {}):
        raise ValueError("Invalid HAR: missing log.entries")

    raw_entries = raw["log"]["entries"]

    if not raw_entries:
        raise ValueError("No entries found in HAR")

    entries = [HarEntry(**e) for e in raw_entries]
    total_raw = len(entries)

    # --- 加载 profiles ---
    profiles: list[dict] = []
    if profiles_path is not None:
        try:
            profiles_data = yaml.safe_load(profiles_path.read_text())
            if profiles_data is None:
                profiles_data = {}
            validated = RepoProfilesConfig.model_validate(profiles_data)
            profiles = [p.model_dump() for p in validated.profiles]
        except Exception as exc:
            import sys
            print(f"[har-parser] Warning: failed to parse profiles: {exc}", file=sys.stderr)
            profiles = []

    # --- 过滤与去重 ---
    filtered = filter_entries(entries)
    after_filter = len(filtered)

    deduped = dedup_entries(filtered)
    after_dedup = len(deduped)

    # --- 构建 base_url ---
    base_url = _extract_base_url(entries[0])

    # --- 构建 endpoints ---
    endpoints: list[ParsedEndpoint] = []
    services: set[str] = set()
    modules: set[str] = set()

    for entry in deduped:
        path = entry.request.path
        service, module = _extract_service_module(path)
        matched_repo, matched_branch = match_repo(path, profiles)

        services.add(service)
        modules.add(module)

        endpoints.append(
            ParsedEndpoint(
                id=str(uuid.uuid4()),
                method=entry.request.method,
                path=path,
                service=service,
                module=module,
                request={
                    "headers": _strip_sensitive_headers(entry.request.headers),
                    "body": entry.request.body,
                },
                response={
                    "status": entry.response.status,
                    "body": entry.response.body,
                    "time_ms": entry.time,
                },
                matched_repo=matched_repo,
                matched_branch=matched_branch,
            )
        )

    return ParsedResult(
        source_har=str(har_path),
        parsed_at=datetime.now(tz=UTC).isoformat(),
        base_url=base_url,
        endpoints=endpoints,
        summary=ParsedSummary(
            total_raw=total_raw,
            after_filter=after_filter,
            after_dedup=after_dedup,
            services=sorted(services),
            modules=sorted(modules),
        ),
    )
