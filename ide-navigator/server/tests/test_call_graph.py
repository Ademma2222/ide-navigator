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

    # Рёбра вызовов: kind="call"
    call_pairs = {(e["from"], e["to"]) for e in graph["edges"] if e["kind"] == "call"}
    assert ("mid", "leaf") in call_pairs
    assert ("top", "mid") in call_pairs
    assert ("top", "leaf") in call_pairs


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

    # Класс → методы помечены kind="contains"
    contain_pairs = {(e["from"], e["to"]) for e in graph["edges"] if e["kind"] == "contains"}
    assert ("Service", "start") in contain_pairs
    assert ("Service", "init") in contain_pairs

    # start() → init() — это вызов, не containment
    call_pairs = {(e["from"], e["to"]) for e in graph["edges"] if e["kind"] == "call"}
    assert ("start", "init") in call_pairs


def test_python_call_graph_node_locations():
    """Каждый узел должен нести координаты идентификатора для клик-навигации."""
    src = (
        "def leaf():\n"
        "    return 1\n"
        "\n"
        "class Box:\n"
        "    def open(self):\n"
        "        pass\n"
    )
    lang = PythonLanguage()
    graph = lang.get_call_graph(src)

    by_name = {n["label"]: n for n in graph["nodes"]}
    for name in ("leaf", "Box", "open"):
        node = by_name[name]
        for field in ("line", "character", "endLine", "endCharacter"):
            assert field in node, f"{name} missing {field}"
        assert isinstance(node["line"], int) and node["line"] >= 0

    # leaf объявлен на строке 0, Box — на строке 3, open — на строке 4
    assert by_name["leaf"]["line"] == 0
    assert by_name["Box"]["line"] == 3
    assert by_name["open"]["line"] == 4


def test_python_call_graph_decorated_methods():
    """
    @property / @staticmethod / любые декораторы в tree-sitter-python
    оборачиваются в decorated_definition. Без явной рекурсии мы теряли
    декорированные методы и из Outline, и из Call Graph.
    """
    src = (
        "class StateMachine:\n"
        "    def __init__(self):\n"
        "        pass\n"
        "    @property\n"
        "    def current_state(self):\n"
        "        return self._state\n"
        "    @staticmethod\n"
        "    def factory():\n"
        "        pass\n"
    )
    lang = PythonLanguage()
    graph = lang.get_call_graph(src)

    labels = {n["label"] for n in graph["nodes"]}
    assert "StateMachine" in labels
    assert "__init__" in labels
    assert "current_state" in labels, "@property-метод должен попадать в граф"
    assert "factory" in labels, "@staticmethod-метод должен попадать в граф"

    contain_pairs = {
        (e["from"], e["to"]) for e in graph["edges"] if e["kind"] == "contains"
    }
    assert ("StateMachine", "current_state") in contain_pairs
    assert ("StateMachine", "factory") in contain_pairs


def test_python_call_graph_cyclomatic_complexity():
    """
    Цикломатическая сложность по McCabe: 1 + число branch points.
    Считаем структурные узлы AST (if_statement, for_statement, except_clause,
    case_clause, ternary, etc.) — else_clause и сам try не добавляют путь.
    """
    src = (
        "def trivial():\n"
        "    return 1\n"
        "\n"
        "def branching(x):\n"
        "    if x > 0:\n"
        "        return 1\n"
        "    elif x < 0:\n"
        "        return -1\n"
        "    else:\n"
        "        return 0\n"
        "\n"
        "def loopy(xs):\n"
        "    result = 0\n"
        "    for x in xs:\n"
        "        if x > 0:\n"
        "            result += x\n"
        "        else:\n"
        "            try:\n"
        "                result -= x\n"
        "            except Exception:\n"
        "                pass\n"
        "    while result > 100:\n"
        "        result -= 1\n"
        "    return result\n"
    )
    lang = PythonLanguage()
    graph = lang.get_call_graph(src)
    by_name = {n["label"]: n for n in graph["nodes"]}

    assert by_name["trivial"]["complexity"] == 1
    # if + elif (else не считается)
    assert by_name["branching"]["complexity"] == 3
    # for + if + except + while
    assert by_name["loopy"]["complexity"] == 5


def test_java_call_graph_cyclomatic_complexity():
    """Java switch считается по cases, сам switch_expression не добавляет путь."""
    src = (
        "class App {\n"
        "    int simple() { return 1; }\n"
        "    int complex(int x) {\n"
        "        if (x > 0) {\n"
        "            for (int i = 0; i < 10; i++) {\n"
        "                switch (i % 3) {\n"
        "                    case 0: return 1;\n"
        "                    case 1: return 2;\n"
        "                    default: return 3;\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "        return 0;\n"
        "    }\n"
        "}\n"
    )
    graph = JavaLanguage().get_call_graph(src)
    by_name = {n["label"]: n for n in graph["nodes"]}

    assert by_name["simple"]["complexity"] == 1
    # if + for + 3 cases (0, 1, default)
    assert by_name["complex"]["complexity"] == 6


def test_python_call_graph_edge_kinds():
    """Каждое ребро должно иметь kind ∈ {call, contains}."""
    src = (
        "class A:\n"
        "    def a(self):\n"
        "        pass\n"
        "def top():\n"
        "    return 1\n"
    )
    lang = PythonLanguage()
    graph = lang.get_call_graph(src)

    allowed_kinds = {"call", "contains"}
    for edge in graph["edges"]:
        assert edge["kind"] in allowed_kinds, f"bad edge kind: {edge}"


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
