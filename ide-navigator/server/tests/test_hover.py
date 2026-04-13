"""
Unit tests for Hover Info.
Проверяем что `get_hover()` возвращает Markdown с подсветкой синтаксиса,
kind label и номером строки определения.
"""
from lsprotocol import types

from languages.python_lang import PythonLanguage
from languages.go_lang import GoLanguage
from languages.typescript_lang import TypeScriptLanguage


def test_python_hover_on_function():
    src = (
        "def compute(x):\n"
        "    return x * 2\n"
        "\n"
        "def main():\n"
        "    y = compute(5)\n"
    )
    lang = PythonLanguage()
    # Курсор на "compute" в вызове (строка 4)
    hover = lang.get_hover(src, 4, 10)

    assert hover is not None
    assert isinstance(hover.contents, types.MarkupContent)
    assert hover.contents.kind == types.MarkupKind.Markdown

    md = hover.contents.value
    assert "```python" in md
    assert "def compute(x):" in md
    assert "**function**" in md
    assert "line 1" in md


def test_python_hover_on_class():
    src = (
        "class Widget:\n"
        "    pass\n"
        "\n"
        "w = Widget()\n"
    )
    lang = PythonLanguage()
    # Курсор на Widget в строке 3
    hover = lang.get_hover(src, 3, 5)

    assert hover is not None
    md = hover.contents.value
    assert "**class**" in md
    assert "line 1" in md


def test_python_hover_not_identifier():
    src = "x = 1 + 2\n"
    lang = PythonLanguage()
    hover = lang.get_hover(src, 0, 6)  # на "+"
    assert hover is None


def test_go_hover_language_id():
    src = (
        "package main\n"
        "\n"
        "func greet() string { return \"hi\" }\n"
        "\n"
        "func main() { greet() }\n"
    )
    lang = GoLanguage()
    hover = lang.get_hover(src, 4, 14)  # на greet()
    assert hover is not None
    assert "```go" in hover.contents.value


def test_typescript_hover_language_id():
    src = (
        "function compute(): number { return 42; }\n"
        "\n"
        "const x = compute();\n"
    )
    lang = TypeScriptLanguage()
    hover = lang.get_hover(src, 2, 11)  # на compute()
    assert hover is not None
    assert "```typescript" in hover.contents.value
