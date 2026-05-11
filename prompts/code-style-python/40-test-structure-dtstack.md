# dtstack 风格测试结构

> 当 fingerprint.test_style.file_suffix == "*_test.py" 时加载

## 规则

1. 测试文件以 `_test.py` 结尾
2. 测试类使用 `def setup_method(self)` 实例方法（⚠️ **严禁** `@classmethod def setup_class(cls)`）
3. 类 docstring 格式：`"""测试-{序号} {描述}"""`
4. 使用项目已注册的 pytest markers（如 @pytest.mark.smoke）

## 示例

```python
# ✅ 正确模式：使用 def setup_method(self) 实例方法
class TestCreateProject:
    """测试-1 新建项目"""

    def setup_method(self):
        self.req = BaseRequests()

    def test_create_project(self):
        ...
```

## 常见错误

```python
# ❌ 错误模式1：@classmethod def setup_class(cls) — 本项目严禁使用
@classmethod
def setup_class(cls):
    cls.req = BaseRequests()

# ❌ 错误模式2：def setup_class(self) — 不会被 pytest 自动调用
def setup_class(self):
    self.req = BaseRequests()
```
