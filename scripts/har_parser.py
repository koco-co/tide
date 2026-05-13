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
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scripts.repo_profiles import NormalizedRepoProfile, load_repo_profiles

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
    sequences: list[dict] = []
    """Request sequence analysis: operation chains, async patterns, CRUD pairs."""


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
# 预检函数（供 SKILL 调用，替代内联代码）
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# match_repo
# ---------------------------------------------------------------------------


def _service_aliases(path: str) -> set[str]:
    service, _ = _extract_service_module(path)
    aliases = {service}
    if service.startswith("d") and len(service) > 1:
        aliases.add(service[1:])
    return aliases


def _prefix_service(prefix: str) -> str:
    parts = [part for part in prefix.strip("/").split("/") if part]
    if not parts:
        return ""
    if parts[0] == "api" and len(parts) > 1:
        return parts[1]
    return parts[0]


def match_repo(path: str, profiles: list) -> tuple[str | None, str | None]:
    """将 *path* 与 profiles 中的 url_prefixes 进行匹配；返回 (name, branch) 或 (None, None)。"""
    for profile in profiles:
        for prefix in profile.url_prefixes:
            if path.startswith(prefix):
                return profile.name, profile.branch
    aliases = _service_aliases(path)
    for profile in profiles:
        for prefix in profile.url_prefixes:
            if _prefix_service(prefix) in aliases:
                return profile.name, profile.branch
    return None, None


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


def _extract_service_module(path: str) -> tuple[str, str]:
    """从 URL 路径部分推导出 (service, module)。

    示例：/dassets/v1/datamap/recentQuery → service=dassets, module=datamap
           /api/v1/users                  → service=api, module=users
           /health                        → service=health, module=health
    """
    import re
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


def analyze_request_sequences(
    endpoints: list[ParsedEndpoint], entries: list[HarEntry],
) -> list[dict[str, Any]]:
    """分析 HAR 条目请求序列，识别操作链和异步模式。

    按时间戳排序，识别：
    1. **操作链**：同一 module 下，按时间顺序的连续调用（如：查列表→查详情）
    2. **异步模式**：请求返回 taskId → 随后有状态轮询调用
    3. **CRUD 对**：同一资源路径的 POST→GET→PUT→DELETE 序列

    返回 detected_sequences：
    ```json
    [
      {
        "type": "operation_chain | async_pattern | crud_pair",
        "module": "assets",
        "flows": [
          {"step": 1, "method": "POST", "path": "/create", "description": "..."},
          {"step": 2, "method": "GET", "path": "/{id}"}
        ],
        "confidence": "high | medium"
      }
    ]
    ```
    """
    if not entries or not endpoints:
        return []

    # Build a mapping from endpoint path to endpoint id
    path_to_endpoint: dict[str, ParsedEndpoint] = {}
    for ep in endpoints:
        path_to_endpoint[ep.path] = ep

    # Sort entries by time
    sorted_entries = sorted(entries, key=lambda e: e.time)

    sequences: list[dict[str, Any]] = []
    current_module = None
    current_chain: list[dict[str, Any]] = []
    seen_async_task_ids: dict[str, int] = {}

    for entry in sorted_entries:
        path = entry.request.path
        method = entry.request.method
        _, module = _extract_service_module(path)

        # Detect module transitions
        if module != current_module and current_chain:
            if len(current_chain) >= 2:
                sequences.append({
                    "type": "operation_chain",
                    "module": current_module or "",
                    "flows": list(current_chain),
                    "confidence": "medium",
                })
            current_chain = []
        current_module = module

        # Detect async pattern: response body contains taskId/flowId/jobId
        is_async = False
        task_id = None
        resp_body = entry.response.body
        if resp_body and isinstance(resp_body, dict):
            data = resp_body.get("data")
            if isinstance(data, dict):
                for key in ("taskId", "flowId", "jobId", "id"):
                    if data.get(key) and isinstance(data[key], (int, str)):
                        task_id = str(data[key])
                        is_async = True
                        break
            elif isinstance(data, (int, str)):
                task_id = str(data)
                # Check if this looks like a generated ID (not a small number)
                if task_id.isdigit() and int(task_id) > 1000:
                    is_async = True

        # Track async task IDs and look for subsequent polling
        for task_key, step_count in list(seen_async_task_ids.items()):
            if task_key in path:
                # This is a poll request referencing a task
                sequences.append({
                    "type": "async_pattern",
                    "module": module,
                    "flows": [
                        {"step": step_count, "method": method, "path": path,
                         "description": f"轮询异步任务 {task_key}"},
                    ],
                    "confidence": "high",
                })
                del seen_async_task_ids[task_key]

        if is_async and task_id:
            step_num = len(current_chain) + 1
            seen_async_task_ids[task_id] = step_num
            current_chain.append({
                "step": step_num,
                "method": method,
                "path": path,
                "description": f"触发异步任务(taskId={task_id})",
            })
        else:
            current_chain.append({
                "step": len(current_chain) + 1,
                "method": method,
                "path": path,
                "description": f"{method} {path.split('/')[-1]}",
            })

        # Detect if path contains {id} patterns that match previous create
        for prev in current_chain[:-1]:
            prev_path = prev["path"]
            if prev_path.endswith("/create") or prev_path.endswith("/add"):
                # Next request with the same base path might be an operation on created resource
                prev_base = prev_path.rsplit("/", 1)[0]
                if path.startswith(prev_base) and path != prev_path:
                    sequences.append({
                        "type": "crud_pair",
                        "module": module,
                        "flows": [
                            {"step": prev["step"], "method": prev["method"], "path": prev_path,
                             "description": "创建资源"},
                            {"step": len(current_chain), "method": method, "path": path,
                             "description": "操作新建资源"},
                        ],
                        "confidence": "medium",
                    })

    # Flush last chain
    if len(current_chain) >= 2:
        sequences.append({
            "type": "operation_chain",
            "module": current_module or "",
            "flows": list(current_chain),
            "confidence": "medium",
        })

    return sequences


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
    profiles: list[NormalizedRepoProfile] = []
    if profiles_path is not None:
        try:
            project_root = profiles_path.parent.parent if profiles_path.parent.name == ".tide" else profiles_path.parent
            profiles = load_repo_profiles(profiles_path, project_root)
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

    # -- 构建 endpoints --
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

    # --- 请求序列分析 ---
    sequences = analyze_request_sequences(endpoints, entries)

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
        sequences=sequences,
    )


def write_parsed_result(har_path: Path, profiles_path: Path | None, output_path: Path) -> ParsedResult:
    result = parse_har(har_path, profiles_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Parse HAR into Tide parsed.json")
    parser.add_argument("har_path", type=Path)
    parser.add_argument("--profiles", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = write_parsed_result(args.har_path, args.profiles, args.output)
    print(
        f"HAR parsed: raw={result.summary.total_raw}, "
        f"dedup={result.summary.after_dedup}, output={args.output}"
    )


if __name__ == "__main__":
    main()
