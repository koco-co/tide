# HAR 解析规则

> 引用方：`agents/har-parser.md`
> 用途：`har-parser` Agent 的过滤、去重和仓库匹配规则。

---

## 1. 保留规则（仅保留以下条目）

一个条目仅在满足以下**全部**条件时才保留：

1. **响应 Content-Type 包含 `application/json`**
   - 优先检查响应的 `Content-Type` 请求头。
   - 若不存在，回退到 HAR 的 `content.mimeType` 字段。
   - 支持部分匹配：`application/json`、`application/json;charset=utf-8` 等。

2. **不是静态资源**（见第 2 节丢弃规则）

3. **不是 WebSocket 升级请求**（见第 3 节丢弃规则）

4. **不是噪音 URL**（见第 4 节丢弃规则）

实用说明：目标是 XHR 和 Fetch 请求中返回 JSON 的接口。如不确定某条目是否为 API 调用，判断标准为：它是否返回 `application/json`？如果是，则保留。

---

## 2. 丢弃规则 — 静态资源

丢弃请求 URL 路径以下列扩展名结尾的条目（不区分大小写）：

```
.js   .css  .png  .jpg  .jpeg  .gif  .svg  .ico
.woff .woff2 .ttf  .map
```

仅检查**路径部分**（匹配扩展名时忽略查询字符串）。

应丢弃的路径示例：
- `/static/main.bundle.js`
- `/assets/logo.png`
- `/fonts/roboto.woff2`
- `/dist/vendor.js.map`

---

## 3. 丢弃规则 — WebSocket 升级请求

丢弃 `response.status == 101` 的条目。

HTTP 101 Switching Protocols 始终是 WebSocket 或 SSE 升级，不是需要测试的 API 响应。

---

## 4. 丢弃规则 — 噪音 URL 模式

丢弃请求 URL 路径包含以下子字符串的条目（不区分大小写，对完整路径做子字符串匹配）：

| 模式 | 原因 |
|------|------|
| `hot-update` | Webpack HMR 热更新文件 |
| `sockjs` | SockJS WebSocket 握手 |
| `__webpack` | Webpack 内部资源 |
| `source-map` | Source map 请求 |

应丢弃的路径示例：
- `/static/main.8f3c2.hot-update.json`
- `/sockjs-node/info`
- `/__webpack_hmr`

---

## 5. 去重策略

在过滤**之后**执行去重。按时间顺序（HAR 顺序）处理条目，先出现的优先保留。

### 5.1 完全重复 — 合并（保留第一条）

以下四项全部匹配时，视为完全重复：
- `request.method`
- `request.path`（URL 路径，不含查询字符串）
- `response.status`
- `request.body`（JSON 请求体，按键名排序序列化；无请求体则为 `null`）

**处理方式**：保留第一条，丢弃所有后续重复项。

### 5.2 相同路径、不同参数 — 全部保留，作为参数化数据

若两条记录的 `method + path` 相同，但请求体或查询参数不同，将其视为**不同测试用例**（参数化变体）。

**处理方式**：两条都保留。用例生成 Agent 将从这些变体中生成 `@pytest.mark.parametrize` 或独立测试方法。

示例：
```
POST /dassets/v1/datamap/query  body={"page":1,"size":10}   → 保留
POST /dassets/v1/datamap/query  body={"page":2,"size":10}   → 保留（不同页码）
```

### 5.3 相同路径、不同状态码 — 分别保留

若两条记录的 `method + path` 相同，但 `response.status` 不同，它们代表不同场景（正常路径 + 错误路径）。

**处理方式**：两条都保留。

示例：
```
POST /dmetadata/v1/syncTask/add  status=200  → 保留（成功用例）
POST /dmetadata/v1/syncTask/add  status=400  → 保留（参数校验错误用例）
```

---

## 6. 敏感请求头过滤

在写入任何解析输出**之前**，从所有条目中去除以下请求头：

| 请求头名称（不区分大小写） | 原因 |
|--------------------------|------|
| `Cookie` | 会话令牌 / 认证 Cookie |
| `Authorization` | Bearer 令牌、Basic 认证 |
| `x-auth-token` | 自定义认证令牌 |

从解析输出中完全删除该请求头，不要用占位符替换。

响应头不做过滤（响应头极少包含敏感信息，且 `Set-Cookie` 值在认证流程分析中是必要的）。

---

## 7. URL 前缀 → 仓库匹配

使用 `repo-profiles.yaml` 将每个接口的 URL 路径匹配到对应的源码仓库。

**算法**（先匹配先用）：

```python
for profile in profiles:
    for prefix in profile["url_prefixes"]:
        if path.startswith(prefix):
            return profile["name"], profile["branch"]
return None, None
```

示例：
- 路径 `/dassets/v1/datamap/recentQuery` → 前缀 `/dassets/v1/` → 仓库 `dt-center-assets`，分支 `release_6.2.x`
- 路径 `/dmetadata/v1/syncTask/add` → 前缀 `/dmetadata/v1/` → 仓库 `dt-center-metadata`，分支 `release_6.2.x`
- 路径 `/unknown/v1/foo` → 无匹配 → `matched_repo: null`

**重要说明**：`matched_repo` 为 `null` 表示该接口没有可用的源码。场景分析 Agent 仍会仅基于 HAR 数据生成 L1-L2 断言（Assertion），但 L3-L5 断言将被跳过或标记为 SPECULATIVE（推测性）。

---

## 8. 服务名与模块名提取

从 URL 路径结构中提取 `service`（服务名）和 `module`（模块名）：

```
/dassets/v1/datamap/recentQuery
  └── service = "dassets"   (parts[0])
  └── module  = "datamap"   (parts[2])

/dmetadata/v1/syncTask/pageTask
  └── service = "dmetadata"
  └── module  = "syncTask"
```

规则：`parts = [p for p in path.split("/") if p]`
- `service = parts[0]`，若不存在则为 `"unknown"`
- `module  = parts[2]`，若不存在则取 `parts[1]`，若仍不存在则为 `"unknown"`

---

## 9. 输出：parsed.json 结构

将结果写入 `.autoflow/parsed.json`，结构如下：

```json
{
  "source_har": "<文件名>",
  "parsed_at": "<ISO8601 UTC>",
  "base_url": "http://<host>",
  "endpoints": [
    {
      "id": "ep_001",
      "method": "POST",
      "path": "/dassets/v1/datamap/recentQuery",
      "service": "dassets",
      "module": "datamap",
      "request": {
        "headers": { "<name>": "<value>" },
        "body": {}
      },
      "response": {
        "status": 200,
        "body": {},
        "time_ms": 45
      },
      "matched_repo": "dt-center-assets",
      "matched_branch": "release_6.2.x"
    }
  ],
  "summary": {
    "total_raw": 36,
    "after_filter": 29,
    "after_dedup": 27,
    "services": ["dassets", "dmetadata"],
    "modules": ["datamap", "dataTable", "syncTask"]
  }
}
```

**说明**：
- `id` 格式：`ep_001`、`ep_002`、…（零填充，3 位数字）
- `base_url`：取第一条原始条目 URL 的协议 + 主机部分
- `request` 中的 `headers`：`{name: value}` 键值对字典，敏感请求头已去除
- `time_ms`：来自 HAR `entry.time` 的整数毫秒数

---

## 10. 解析后续动作

写入 `parsed.json` 后，将源 HAR 文件移动到 `.trash/` 目录：

```
.trash/{YYYYMMDD_HHMMSS}_{原始文件名}
```

示例：`.trash/20260406_143022_172.16.115.247.har`

若 `.trash/` 目录不存在则创建。此操作保持工作目录整洁，防止同一 HAR 被意外重复处理。
