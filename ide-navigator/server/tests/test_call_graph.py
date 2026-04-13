"""
Unit tests for Call Graph.
Проверяем что `get_call_graph()` возвращает корректные nodes/edges
и что санитизация ограничивает длину label / whitelist типов.
"""
from languages.python_lang import PythonLanguage
from languages.java_lang import JavaLanguage
from languages.base import BaseLanguage


def test_python_call_graph_basic():
    src = (
        "def leaf():\n"
        "    return 1\n"
        "\n"
        "def mid():\n"
        "    return leaf()\n"
        "\n"
        "def top():\n"
        "    return mid() + leaf()\n"
    )
    lang = PythonLanguage()
    graph = lang.get_call_graph(src)

    names = {n["label"] for n in graph["nodes"]}
    assert "leaf" in names
    assert "mid" in names
    assert "top" in names

    # Все edges — пары существующих имён
    edge_pairs = {(e["from"], e["to"]) for e in graph["edges"]}
    assert ("mid", "leaf") in edge_pairs
    assert ("top", "mid") in edge_pairs
    assert ("top", "leaf") in edge_pairs


def test_python_call_graph_class_containment():
    src = (
        "class Service:\n"
        "    def start(self):\n"
        "        self.init()\n"
        "    def init(self):\n"
        "        pass\n"
    )
    lang = PythonLanguage()
    graph = lang.get_call_graph(src)

    names = {n["label"] for n in graph["nodes"]}
    assert "Service" in names
    assert "start" in names
    assert "init" in names

    # Class → methods containment edges
    edge_pairs = {(e["from"], e["to"]) for e in graph["edges"]}
    assert ("Service", "start") in edge_pairs
    assert ("Service", "init") in edge_pairs


def test_call_graph_empty_source():
    lang = PythonLanguage()
    graph = lang.get_call_graph("")
    assert graph == {"nodes": [], "edges": []}


def test_call_graph_type_whitelist():
    """
    Тип каждого узла должен быть из белого списка.
    Это гарантирует безопасность WebView — никакие неожиданные значения
    из tree-sitter не попадут в HTML клиента.
    """
    src = "def foo(): pass\nclass Bar: pass\n"
    lang = PythonLanguage()
    graph = lang.get_call_graph(src)

    allowed = BaseLanguage._GRAPH_ALLOWED_TYPES
    for node in graph["nodes"]:
        assert node["type"] in allowed, f"unexpected type: {node['type']!r}"


def test_call_graph_label_length_limit():
    """Имена длиннее лимита должны быть обрезаны."""
    # Генерим файл с функцией, имя которой длиннее лимита
    long_name = "x" * (BaseLanguage._GRAPH_MAX_LABEL_LEN + 50)
    src = f"def {long_name}(): pass\n"
    lang = PythonLanguage()
    graph = lang.get_call_graph(src)

    for node in graph["nodes"]:
        assert len(node["label"]) <= BaseLanguage._GRAPH_MAX_LABEL_LEN


def test_java_call_graph():
    src = (
        "class App {\n"
        "    int compute() { return 1; }\n"
        "    int run() { return compute(); }\n"
        "}\n"
    )
    lang = JavaLanguage()
    graph = lang.get_call_graph(src)

    names = {n["label"] for n in graph["nodes"]}
    assert "App" in names
    assert "compute" in names
    assert "run" in names

    edge_pairs = {(e["from"], e["to"]) for e in graph["edges"]}
    assert ("run", "compute") in edge_pairs
