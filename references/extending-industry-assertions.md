# 扩展行业断言规则指南

## 概述

tide 支持为特定行业添加定制化断言规则。当前内置行业：Finance、Healthcare、E-commerce、SaaS。

## 添加新行业

### 步骤 1：定义行业规则

在 `prompts/industry-assertions.md` 中添加新的行业节：

```yaml
## 新行业名称

### 核心断言规则
| 规则 | 描述 | 适用层 |
|------|------|-------|
| 规则名称 | 详细描述 | L3/L4/L5 |
```

### 步骤 2：注册行业

在 `scripts/preferences.py` 的 `TidePreferences.industry` 字段注释中添加新行业名称。

### 步骤 3：添加 Hook（可选）

使用 Hook 系统注入自定义断言逻辑：

```yaml
# tide-hooks.yaml
hooks:
  - point: wave3:generate:after
    name: industry-custom-assertions
    command: python scripts/custom_assertions.py
    description: 注入行业特定断言
```

## 行业规则编写原则

1. **可观测性**：每条规则必须可以通过 API 响应或数据库状态验证
2. **分层映射**：明确规则属于 L3（数据）、L4（业务）还是 L5（推断）
3. **误报控制**：L5 规则标记 `confidence: SPECULATIVE`，审查时可跳过
4. **合规驱动**：优先覆盖法规/合规要求（如 GDPR、HIPAA、PCI-DSS）
