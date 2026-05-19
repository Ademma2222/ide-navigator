from languages.python_lang import PythonLanguage
from languages.java_lang import JavaLanguage

PY_SRC = '''\
def helper():
    return 1

def user_one():
    return helper()

def user_two():
    x = helper()
    return x
'''

def test_python_references_all():
    lang = PythonLanguage()
    ranges = lang.find_references(PY_SRC, 0, 4, include_declaration=True)
    assert len(ranges) == 3

def test_python_references_excluding_declaration():
    lang = PythonLanguage()
    ranges = lang.find_references(PY_SRC, 0, 4, include_declaration=False)
    assert len(ranges) == 2

def test_python_references_none_when_not_identifier():
    lang = PythonLanguage()
    ranges = lang.find_references(PY_SRC, 0, 0, include_declaration=True)
    assert ranges == []

def test_python_references_with_context_snippets():
    lang = PythonLanguage()
    data = lang.get_references_with_context(PY_SRC, 0, 4, include_declaration=True)

    assert data is not None
    assert data["name"] == "helper"
    assert data["language"] == "python"
    assert len(data["refs"]) == 3

    for ref in data["refs"]:
        assert "line" in ref
        assert "character" in ref
        assert "endCharacter" in ref
        assert "snippet" in ref
        assert "helper" in ref["snippet"]

    lines = [r["line"] for r in data["refs"]]
    assert lines == sorted(lines)

def test_python_references_with_context_no_match():
    lang = PythonLanguage()
    data = lang.get_references_with_context(PY_SRC, 1, 0, include_declaration=True)
    assert data is None

JAVA_SRC = '''\
class App {
    int compute() { return 1; }
    int run() {
        int a = compute();
        int b = compute();
        return a + b;
    }
}
'''

def test_java_references():
    lang = JavaLanguage()
    ranges = lang.find_references(JAVA_SRC, 1, 9, include_declaration=True)
    assert len(ranges) == 3
