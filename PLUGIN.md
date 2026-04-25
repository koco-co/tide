---
name: tide
description: "基于 HAR 文件驱动、结合后端源码感知的 API 自动化测试工具。从 HAR 文件与后端源码生成带有 L1-L5 分层断言的 pytest 测试套件。"
version: "1.3.0"
author: "koco-co"
license: MIT
repository: "https://github.com/koco-co/tide"
keywords: ["api-testing", "har", "pytest", "automation", "ai"]
requires:
  bins: ["python3", "uv", "git"]
---

# tide

基于 HAR 文件驱动、具备源码感知能力的 API 自动化测试 Claude Code 插件。

## Skills

- `/using-tide` — 初始化项目环境，配置代码仓库、技术栈与连接信息
- `/tide <har-file>` — 从 HAR 文件生成 pytest 测试套件，借助 AI 对后端源码进行深度分析
