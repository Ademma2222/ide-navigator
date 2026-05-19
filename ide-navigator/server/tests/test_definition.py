from lsprotocol import types

from languages.python_lang import PythonLanguage
from languages.java_lang import JavaLanguage
from languages.go_lang import GoLanguage
from languages.typescript_lang import TypeScriptLanguage

def _find_position(source: str, token: str, occurrence: int = 0) -> tuple[int, int]:
    seen = 0
    for line_idx, line in enumerate(source.splitlines()):
        start = 0
        while True:
            idx = line.find(token, start)
            if idx == -1:
                break
            if seen == occurrence:
                return line_idx, idx
            seen += 1
            start = idx + 1
    raise AssertionError(f"token {token!r} occurrence #{occurrence} not found")

def test_python_definition_function():
    src = (
        "def helper():\n"
        "    return 42\n"
        "\n"
        "def main():\n"
        "    x = helper()\n"
    )
    lang = PythonLanguage()
    call_line, call_char = _find_position(src, "helper", occurrence=1)
    result = lang.find_definition(src, call_line, call_char + 1)

    assert result is not None
    assert result.start.line == 0

def test_python_definition_class():
    src = (
        "class Thing:\n"
        "    pass\n"
        "\n"
        "def make():\n"
        "    return Thing()\n"
    )
    lang = PythonLanguage()
    call_line, call_char = _find_position(src, "Thing", occurrence=1)
    result = lang.find_definition(src, call_line, call_char + 1)

    assert result is not None
    assert result.start.line == 0

def test_python_definition_not_found():
    src = "x = 1 + 2\n"
    lang = PythonLanguage()
    result = lang.find_definition(src, 0, 6)
    assert result is None

def test_java_definition_method():
    src = (
        "class App {\n"
        "    int compute() { return 42; }\n"
        "    int run() { return compute(); }\n"
        "}\n"
    )
    lang = JavaLanguage()
    call_line, call_char = _find_position(src, "compute", occurrence=1)
    result = lang.find_definition(src, call_line, call_char + 1)
    assert result is not None
    assert result.start.line == 1

def test_go_definition_type():
    src = (
        "package main\n"
        "\n"
        "type User struct {\n"
        "    Name string\n"
        "}\n"
        "\n"
        "func make() User {\n"
        "    return User{}\n"
        "}\n"
    )
    lang = GoLanguage()
    call_line, call_char = _find_position(src, "User", occurrence=1)
    result = lang.find_definition(src, call_line, call_char + 1)
    assert result is not None
    assert result.start.line == 2

def test_typescript_definition_interface():
    src = (
        "interface Shape {\n"
        "    area(): number;\n"
        "}\n"
        "\n"
        "function render(s: Shape): void {}\n"
    )
    lang = TypeScriptLanguage()
    call_line, call_char = _find_position(src, "Shape", occurrence=1)
    result = lang.find_definition(src, call_line, call_char + 1)
    assert result is not None
    assert result.start.line == 0
