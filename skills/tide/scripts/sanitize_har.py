#!/usr/bin/env python3
"""在本地把 HAR 转换为不含原始值的结构摘要。"""

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

FORMAT_VERSION = 1
DEFAULT_MAX_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_ENTRIES = 5000
MAX_SCHEMA_FIELDS = 400
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
ALIAS_PATTERN = re.compile(r"(?:host|segment|field|query|header|sensitive)_[0-9]{6}")
SAFE_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}")
MIME_PATTERN = re.compile(r"(?:unknown|[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+)")
SENSITIVE_MARKERS = (
    "authorization",
    "authentication",
    "cookie",
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "session",
    "credential",
    "private_key",
    "access_key",
    "refresh_key",
)


class SanitizationError(Exception):
    pass


class AliasRegistry:
    """按首次出现顺序分配不可反推原值的稳定别名。"""

    def __init__(self):
        self.values = {}
        self.counts = {}

    def alias(self, prefix, value):
        key = (prefix, value)
        existing = self.values.get(key)
        if existing is not None:
            return existing
        count = self.counts.get(prefix, 0) + 1
        self.counts[prefix] = count
        alias = "%s_%06d" % (prefix, count)
        self.values[key] = alias
        return alias


def _reject_duplicate_keys(pairs):
    value = {}
    for key, child in pairs:
        if key in value:
            raise SanitizationError("JSON 包含重复字段：%s" % key)
        value[key] = child
    return value


def _string_list(value, label, pattern=None, alternatives=()):
    if not isinstance(value, list):
        raise SanitizationError("%s 必须是数组。" % label)
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item or "\x00" in item:
            raise SanitizationError("%s[%d] 必须是安全字符串。" % (label, index))
        if (
            pattern is not None
            and pattern.fullmatch(item) is None
            and item not in alternatives
        ):
            raise SanitizationError("%s[%d] 格式无效。" % (label, index))


def _validate_schema(value, label, budget, depth=0):
    if not isinstance(value, dict) or "type" not in value:
        raise SanitizationError("%s 缺少结构类型。" % label)
    allowed_types = {
        "null",
        "boolean",
        "integer",
        "number",
        "array",
        "object",
        "string",
        "missing",
        "invalid_json",
    }
    if value["type"] not in allowed_types:
        raise SanitizationError("%s 包含未知结构类型。" % label)
    allowed = {"type", "truncated", "fields", "length", "items"}
    if not set(value).issubset(allowed):
        raise SanitizationError("%s 包含未知字段。" % label)
    if "truncated" in value and value["truncated"] is not True:
        raise SanitizationError("%s.truncated 只能为 true。" % label)
    if depth > 6:
        raise SanitizationError("%s 超过最大结构深度。" % label)
    fields = value.get("fields")
    if fields is not None:
        if value["type"] != "object" or not isinstance(fields, dict):
            raise SanitizationError("%s.fields 与结构类型不一致。" % label)
        for name, child in fields.items():
            budget[0] -= 1
            if (
                budget[0] < 0
                or not isinstance(name, str)
                or not (
                    SAFE_NAME_PATTERN.fullmatch(name) or ALIAS_PATTERN.fullmatch(name)
                )
            ):
                raise SanitizationError("%s.fields 超过限制或名称无效。" % label)
            _validate_schema(child, "%s.fields.%s" % (label, name), budget, depth + 1)
    if "length" in value and (
        value["type"] != "array"
        or type(value["length"]) is not int
        or value["length"] < 0
    ):
        raise SanitizationError("%s.length 无效。" % label)
    if "items" in value:
        if value["type"] != "array":
            raise SanitizationError("%s.items 与结构类型不一致。" % label)
        _validate_schema(value["items"], "%s.items" % label, budget, depth + 1)


def _validate_body(value, label):
    if not isinstance(value, dict) or set(value) - {
        "mime_type",
        "declared_size",
        "schema",
    }:
        raise SanitizationError("%s 字段无效。" % label)
    if (
        not isinstance(value.get("mime_type"), str)
        or MIME_PATTERN.fullmatch(value["mime_type"]) is None
        or not isinstance(value.get("schema"), dict)
    ):
        raise SanitizationError("%s 缺少内容类型或结构。" % label)
    if "declared_size" in value and (
        type(value["declared_size"]) is not int or value["declared_size"] < 0
    ):
        raise SanitizationError("%s.declared_size 无效。" % label)
    _validate_schema(value["schema"], "%s.schema" % label, [MAX_SCHEMA_FIELDS])


def validate_summary_value(summary):
    expected = {"format_version", "source_sha256", "entry_count", "entries"}
    if not isinstance(summary, dict) or set(summary) != expected:
        raise SanitizationError("脱敏摘要字段不完整或包含未知字段。")
    if (
        type(summary["format_version"]) is not int
        or summary["format_version"] != FORMAT_VERSION
    ):
        raise SanitizationError("脱敏摘要格式版本无效。")
    if (
        not isinstance(summary["source_sha256"], str)
        or HASH_PATTERN.fullmatch(summary["source_sha256"]) is None
    ):
        raise SanitizationError("脱敏摘要缺少有效来源散列。")
    if (
        not isinstance(summary["entries"], list)
        or type(summary["entry_count"]) is not int
        or summary["entry_count"] != len(summary["entries"])
    ):
        raise SanitizationError("脱敏摘要条目数量不一致。")
    if len(summary["entries"]) > DEFAULT_MAX_ENTRIES:
        raise SanitizationError("脱敏摘要条目超过上限。")
    expected_entry = {
        "entry_id",
        "method",
        "url",
        "query_names",
        "request_header_names",
        "request_cookie_count",
        "request_body",
        "response_status",
        "response_header_names",
        "response_cookie_count",
        "response_body",
    }
    seen = set()
    for index, entry in enumerate(summary["entries"]):
        if not isinstance(entry, dict) or set(entry) != expected_entry:
            raise SanitizationError("脱敏摘要第 %d 条字段无效。" % index)
        expected_id = "entry-%06d" % (index + 1)
        if entry["entry_id"] != expected_id or entry["entry_id"] in seen:
            raise SanitizationError("脱敏摘要 entry_id 无效或重复。")
        seen.add(entry["entry_id"])
        if (
            not isinstance(entry["method"], str)
            or re.fullmatch(r"[A-Z]{1,16}", entry["method"]) is None
        ):
            raise SanitizationError("脱敏摘要请求方法无效。")
        url = entry["url"]
        if not isinstance(url, dict) or set(url) != {
            "scheme",
            "host_alias",
            "path_aliases",
        }:
            raise SanitizationError("脱敏摘要 URL 结构无效。")
        if url["scheme"] not in {"http", "https", "unknown"}:
            raise SanitizationError("脱敏摘要 URL scheme 无效。")
        if not isinstance(url["host_alias"], str) or not (
            ALIAS_PATTERN.fullmatch(url["host_alias"])
            or url["host_alias"] in {"host_invalid", "host_missing"}
        ):
            raise SanitizationError("脱敏摘要主机别名无效。")
        _string_list(
            url["path_aliases"],
            "path_aliases",
            re.compile(r"segment_[0-9]{6}"),
            ("<integer>", "<uuid>"),
        )
        for field in (
            "query_names",
            "request_header_names",
            "response_header_names",
        ):
            names = entry[field]
            _string_list(names, field)
            if any(
                not (SAFE_NAME_PATTERN.fullmatch(name) or ALIAS_PATTERN.fullmatch(name))
                for name in names
            ):
                raise SanitizationError("脱敏摘要 %s 包含无效名称。" % field)
        for field in ("request_cookie_count", "response_cookie_count"):
            if type(entry[field]) is not int or entry[field] < 0:
                raise SanitizationError("脱敏摘要 %s 无效。" % field)
        if (
            type(entry["response_status"]) is not int
            or not 0 <= entry["response_status"] <= 599
        ):
            raise SanitizationError("脱敏摘要响应状态无效。")
        _validate_body(entry["request_body"], "request_body")
        _validate_body(entry["response_body"], "response_body")
    return summary


def load_summary(path):
    raw = _read_regular_file(path, DEFAULT_MAX_BYTES)
    try:
        summary = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise SanitizationError("脱敏摘要不是有效 JSON：%s" % exc)
    return validate_summary_value(summary), raw


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _is_sensitive_name(name):
    normalized = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    return any(marker in normalized for marker in SENSITIVE_MARKERS)


def _safe_name(name, aliases, prefix="field"):
    text = str(name)
    if _is_sensitive_name(text):
        return aliases.alias("sensitive", text)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}", text):
        return text
    return aliases.alias(prefix, text)


def _safe_mime(value):
    mime = str(value or "").split(";", 1)[0].strip().lower()
    if re.fullmatch(r"[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+", mime):
        return mime
    return "unknown"


def _value_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def _schema(value, budget, aliases, depth=0):
    result = {"type": _value_type(value)}  # type: dict
    if depth >= 6 or budget[0] <= 0:
        result["truncated"] = True
        return result
    if isinstance(value, dict):
        fields = {}
        for key in sorted(value, key=lambda item: str(item)):
            if budget[0] <= 0:
                result["truncated"] = True
                break
            budget[0] -= 1
            fields[_safe_name(key, aliases)] = _schema(
                value[key], budget, aliases, depth + 1
            )
        result["fields"] = fields
    elif isinstance(value, list):
        result["length"] = len(value)
        if value:
            result["items"] = _schema(value[0], budget, aliases, depth + 1)
    return result


def _body_schema(content, aliases):
    if not isinstance(content, dict):
        return {"mime_type": "unknown", "schema": {"type": "missing"}}
    mime = _safe_mime(content.get("mimeType"))
    text = content.get("text")
    result = {"mime_type": mime}  # type: dict
    declared_size = content.get("size")
    if isinstance(declared_size, int) and declared_size >= 0:
        result["declared_size"] = declared_size
    if isinstance(text, str) and (mime == "application/json" or mime.endswith("+json")):
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError):
            result["schema"] = {"type": "invalid_json"}
        else:
            result["schema"] = _schema(parsed, [MAX_SCHEMA_FIELDS], aliases)
    elif isinstance(text, str):
        result["schema"] = {"type": "string"}
    else:
        result["schema"] = {"type": "missing"}
    return result


def _named_items(items, prefix, aliases):
    names = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and "name" in item:
                names.append(_safe_name(item["name"], aliases, prefix))
    return sorted(set(names))


def _safe_url(url, aliases):
    try:
        parsed = urlsplit(str(url))
    except ValueError:
        return {"scheme": "unknown", "host_alias": "host_invalid", "path_aliases": []}
    scheme = (
        parsed.scheme.lower()
        if parsed.scheme.lower() in ("http", "https")
        else "unknown"
    )
    hostname = parsed.hostname or ""
    host_alias = aliases.alias("host", hostname.lower()) if hostname else "host_missing"
    path_aliases = []
    for segment in parsed.path.split("/"):
        if not segment:
            continue
        if re.fullmatch(r"[0-9]+", segment):
            path_aliases.append("<integer>")
        elif re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}", segment):
            path_aliases.append("<uuid>")
        else:
            path_aliases.append(aliases.alias("segment", segment))
    query_names = [
        _safe_name(name, aliases, "query")
        for name, _ in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return {
        "scheme": scheme,
        "host_alias": host_alias,
        "path_aliases": path_aliases,
        "query_names": sorted(set(query_names)),
    }


def _entry_summary(entry, index, aliases):
    if not isinstance(entry, dict):
        raise SanitizationError("HAR 条目 %d 不是对象。" % index)
    request = entry.get("request")
    response = entry.get("response")
    if not isinstance(request, dict) or not isinstance(response, dict):
        raise SanitizationError("HAR 条目 %d 缺少请求或响应对象。" % index)
    method = str(request.get("method", "")).upper()
    if not re.fullmatch(r"[A-Z]{1,16}", method):
        method = "OTHER"
    status_code = response.get("status")
    if not isinstance(status_code, int) or status_code < 0 or status_code > 599:
        status_code = 0
    safe_url = _safe_url(request.get("url", ""), aliases)
    query_names = set(safe_url.pop("query_names"))
    query_names.update(_named_items(request.get("queryString"), "query", aliases))
    result = {
        "entry_id": "entry-%06d" % (index + 1),
        "method": method,
        "url": safe_url,
        "query_names": sorted(query_names),
        "request_header_names": _named_items(request.get("headers"), "header", aliases),
        "request_cookie_count": len(request.get("cookies", []))
        if isinstance(request.get("cookies"), list)
        else 0,
        "request_body": _body_schema(request.get("postData"), aliases),
        "response_status": status_code,
        "response_header_names": _named_items(
            response.get("headers"), "header", aliases
        ),
        "response_cookie_count": len(response.get("cookies", []))
        if isinstance(response.get("cookies"), list)
        else 0,
        "response_body": _body_schema(response.get("content"), aliases),
    }
    return result


def _read_regular_file(path, max_bytes):
    parent_fd = None
    descriptor = None
    try:
        parent_fd, name, _ = _open_parent_no_symlink(path)
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise SanitizationError(
                "HAR 输入必须是普通文件，不能是软链接或其他文件类型。"
            )
        if info.st_size > max_bytes:
            raise SanitizationError("HAR 文件超过允许大小 %d 字节。" % max_bytes)
        chunks = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
    except OSError as exc:
        raise SanitizationError("读取 HAR 文件失败：%s" % exc)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent_fd is not None:
            os.close(parent_fd)
    if len(data) > max_bytes:
        raise SanitizationError("HAR 文件读取结果超过允许大小。")
    return data


def _is_within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _directory_flags():
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise SanitizationError("当前系统不支持安全目录文件描述符操作。")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _open_parent_no_symlink(path):
    lexical = Path(os.path.abspath(os.path.expanduser(str(path))))
    if lexical.is_symlink():
        raise SanitizationError("文件路径不能是符号链接。")
    absolute = lexical.parent.resolve(strict=True) / lexical.name
    if absolute.parent == absolute:
        raise SanitizationError("文件路径无效。")
    descriptor = os.open(os.path.sep, _directory_flags())
    try:
        for part in absolute.parts[1:-1]:
            next_descriptor = os.open(part, _directory_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor, absolute.name, absolute
    except Exception:
        os.close(descriptor)
        raise


def _atomic_create(path, data):
    lexical = Path(os.path.abspath(os.path.expanduser(str(path))))
    absolute = lexical.parent.resolve(strict=True) / lexical.name
    parent = absolute.parent
    temp_root = Path(tempfile.gettempdir()).resolve()
    if not _is_within(parent, temp_root):
        raise SanitizationError("脱敏摘要只能写入系统临时目录。")
    parent_fd = None
    file_descriptor = None
    temporary_name = ".tide-summary-%s" % secrets.token_hex(12)
    try:
        parent_fd, target_name, opened_absolute = _open_parent_no_symlink(absolute)
        if opened_absolute != absolute:
            raise SanitizationError("脱敏摘要路径发生变化。")
        file_descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        with os.fdopen(file_descriptor, "wb") as handle:
            file_descriptor = None
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(
            temporary_name,
            target_name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
            follow_symlinks=False,
        )
        os.unlink(temporary_name, dir_fd=parent_fd)
        temporary_name = None
        os.fsync(parent_fd)
    except (OSError, ValueError) as exc:
        raise SanitizationError("写入脱敏摘要失败：%s" % exc)
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        if temporary_name and parent_fd is not None:
            try:
                os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        if parent_fd is not None:
            os.close(parent_fd)


def sanitize(input_path, output_path, max_bytes, max_entries):
    raw = _read_regular_file(input_path, max_bytes)
    try:
        document = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise SanitizationError("HAR 不是有效的 UTF-8 JSON：%s" % exc)
    log = document.get("log") if isinstance(document, dict) else None
    entries = log.get("entries") if isinstance(log, dict) else None
    if not isinstance(entries, list):
        raise SanitizationError("HAR 缺少 log.entries 数组。")
    if len(entries) > max_entries:
        raise SanitizationError("HAR 条目数超过限制 %d。" % max_entries)
    aliases = AliasRegistry()
    summary = {
        "format_version": FORMAT_VERSION,
        "source_sha256": _sha256_bytes(raw),
        "entry_count": len(entries),
        "entries": [
            _entry_summary(entry, index, aliases) for index, entry in enumerate(entries)
        ],
    }
    validate_summary_value(summary)
    encoded = (
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    _atomic_create(output_path, encoded)
    return summary


def self_test():
    with tempfile.TemporaryDirectory(prefix="tide-sanitize-test-") as directory:
        root = Path(directory)
        har_path = root / "input.har"
        output_path = root / "summary.json"
        second_output_path = root / "summary-second.json"
        sample = {
            "log": {
                "entries": [
                    {
                        "request": {
                            "method": "POST",
                            "url": "https://private.example.test/users/alice?token=super-secret",
                            "headers": [
                                {
                                    "name": "Authorization",
                                    "value": "Bearer super-secret",
                                }
                            ],
                            "queryString": [{"name": "token", "value": "super-secret"}],
                            "cookies": [{"name": "session", "value": "super-secret"}],
                            "postData": {
                                "mimeType": "application/json",
                                "text": json.dumps(
                                    {"name": "Alice", "password": "super-secret"}
                                ),
                            },
                        },
                        "response": {
                            "status": 200,
                            "headers": [
                                {"name": "Content-Type", "value": "application/json"}
                            ],
                            "cookies": [],
                            "content": {
                                "mimeType": "application/json",
                                "text": json.dumps({"id": 42}),
                            },
                        },
                    }
                ]
            }
        }
        har_path.write_text(json.dumps(sample), encoding="utf-8")
        sanitize(har_path, output_path, DEFAULT_MAX_BYTES, DEFAULT_MAX_ENTRIES)
        sanitize(har_path, second_output_path, DEFAULT_MAX_BYTES, DEFAULT_MAX_ENTRIES)
        output = output_path.read_text(encoding="utf-8")
        if output != second_output_path.read_text(encoding="utf-8"):
            raise SanitizationError("自检发现相同 HAR 没有生成稳定摘要。")
        forbidden = ("super-secret", "private.example.test", "/users/alice", "Alice")
        if any(value in output for value in forbidden):
            raise SanitizationError("自检发现脱敏摘要包含原始值。")
        parsed = json.loads(output)
        if parsed["entry_count"] != 1 or parsed["entries"][0]["method"] != "POST":
            raise SanitizationError("自检发现摘要结构错误。")
        if parsed["entries"][0]["url"]["host_alias"] != "host_000001":
            raise SanitizationError("自检发现别名不是顺序分配的不可逆编号。")
        validate_summary_value(parsed)
        invalid = dict(parsed)
        invalid["entry_count"] = 2
        try:
            validate_summary_value(invalid)
        except SanitizationError:
            pass
        else:
            raise SanitizationError("自检未阻断条目数量漂移。")


def build_parser():
    parser = argparse.ArgumentParser(
        description="在本地把 HAR 转换为不含原始值的结构摘要。"
    )
    parser.add_argument("input", nargs="?", help="本地 HAR 文件")
    parser.add_argument("--output", help="系统临时目录中的新 JSON 文件")
    parser.add_argument(
        "--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="最大输入字节数"
    )
    parser.add_argument(
        "--max-entries", type=int, default=DEFAULT_MAX_ENTRIES, help="最大 HAR 条目数"
    )
    parser.add_argument("--self-test", action="store_true", help="运行内置自检后退出")
    parser.add_argument(
        "--validate-summary", action="store_true", help="严格校验已有脱敏摘要"
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print("sanitize_har.py 自检通过。")
            return 0
        if args.validate_summary:
            if not args.input:
                raise SanitizationError("校验脱敏摘要必须提供输入文件。")
            summary, _ = load_summary(Path(args.input))
            print("脱敏摘要校验通过：%d 个条目。" % summary["entry_count"])
            return 0
        if not args.input or not args.output:
            raise SanitizationError("必须同时提供 HAR 输入和 --output。")
        if args.max_bytes <= 0 or args.max_entries <= 0:
            raise SanitizationError("大小和条目限制必须为正整数。")
        summary = sanitize(
            Path(args.input), Path(args.output), args.max_bytes, args.max_entries
        )
        print("脱敏摘要已创建：%d 个条目。" % summary["entry_count"])
        return 0
    except SanitizationError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
