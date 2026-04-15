"""
Базовый класс для всех языковых модулей.

Дима: чтобы добавить новый язык — создай класс который наследует BaseLanguage
и реализует два метода: get_parser() и _extract_symbols().
Смотри python_lang.py как пример.
"""
import logging
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from tree_sitter import Parser
from lsprotocol import types


logger = logging.getLogger(__name__)


class BaseLanguage(ABC):

    # Идентификатор языка для подсветки синтаксиса в Markdown-код-блоках.
    # Переопределяется в каждом языковом наследнике.
    LANGUAGE_ID: str = "text"

    # Максимальное количество разобранных AST-деревьев в кэше.
    # Outline/Definition/References/Hover на одном файле парсят AST четырежды —
    # кэш даёт 4x ускорение без заметного расхода памяти.
    _PARSE_CACHE_MAX = 32

    def __init__(self) -> None:
        # OrderedDict как простой LRU: ключ — сам source, значение — Tree.
        # Кэш привязан к экземпляру класса (в LANGUAGE_MAP они — синглтоны).
        self._parse_cache: OrderedDict[str, object] = OrderedDict()

    @abstractmethod
    def get_parser(self) -> Parser:
        """Вернуть настроенный парсер tree-sitter для этого языка."""
        pass

    def _parse(self, source: str):
        """
        Разобрать исходник через tree-sitter с LRU-кэшем.
        Все методы класса (get_symbols, find_definition и т.д.) должны
        использовать этот метод вместо `self.get_parser().parse(...)`.
        """
        cached = self._parse_cache.get(source)
        if cached is not None:
            self._parse_cache.move_to_end(source)
            return cached

        start = time.perf_counter()
        tree = self.get_parser().parse(bytes(source, "utf-8"))
        elapsed_ms = (time.perf_counter() - start) * 1000
        # INFO, а не DEBUG: cache miss — редкое событие (один раз на версию файла),
        # а наглядное доказательство что кэш работает важно для курсовой.
        logger.info(f"parse[{self.LANGUAGE_ID}]: {len(source)} bytes in {elapsed_ms:.1f}ms")

        self._parse_cache[source] = tree
        if len(self._parse_cache) > self._PARSE_CACHE_MAX:
            self._parse_cache.popitem(last=False)
        return tree

    def get_symbols(self, source: str) -> list[types.DocumentSymbol]:
        """Главный метод — извлечь все символы из исходного кода."""
        tree = self._parse(source)
        return self._extract_symbols(tree.root_node)

    @abstractmethod
    def _extract_symbols(self, node) -> list[types.DocumentSymbol]:
        """Обойти AST и собрать символы (функции, классы, методы)."""
        pass

    # ── Вспомогательные методы (доступны всем наследникам) ────────────────

    def _to_range(self, node) -> types.Range:
        """Конвертировать позицию tree-sitter → LSP Range."""
        return types.Range(
            start=types.Position(
                line=node.start_point[0],
                character=node.start_point[1],
            ),
            end=types.Position(
                line=node.end_point[0],
                character=node.end_point[1],
            ),
        )

    # ── Go to Definition ────────────────────────────────────────────────

    def find_definition(self, source: str, line: int, character: int) -> types.Range | None:
        """Найти определение символа под курсором (внутри одного файла)."""
        tree = self._parse(source)

        # Находим самый глубокий узел в позиции курсора
        node = tree.root_node.descendant_for_point_range(
            (line, character), (line, character)
        )
        if node is None or "identifier" not in node.type:
            return None

        name = node.text.decode("utf-8")

        # Ищем определение среди символов файла
        symbols = self._extract_symbols(tree.root_node)
        found = self._find_symbol_by_name(symbols, name)
        if found:
            return found.selection_range
        return None

    def _find_symbol_by_name(
        self, symbols: list[types.DocumentSymbol], name: str,
    ) -> types.DocumentSymbol | None:
        """Рекурсивный поиск символа по имени в дереве."""
        for s in symbols:
            if s.name == name:
                return s
            if s.children:
                found = self._find_symbol_by_name(s.children, name)
                if found:
                    return found
        return None

    # ── Find All References ───────────────────────────────────────────────

    def find_references(
        self, source: str, line: int, character: int, include_declaration: bool = True,
    ) -> list[types.Range]:
        """Найти все вхождения идентификатора под курсором в файле."""
        tree = self._parse(source)

        node = tree.root_node.descendant_for_point_range(
            (line, character), (line, character)
        )
        if node is None or "identifier" not in node.type:
            return []

        name = node.text.decode("utf-8")

        # Собираем все identifier-узлы с таким же текстом
        matches: list[types.Range] = []
        self._collect_identifiers(tree.root_node, name, matches)

        if not include_declaration:
            # Убираем позицию определения (если есть)
            symbols = self._extract_symbols(tree.root_node)
            decl = self._find_symbol_by_name(symbols, name)
            if decl:
                matches = [r for r in matches if r != decl.selection_range]

        return matches

    def _collect_identifiers(
        self, node, name: str, result: list[types.Range],
    ) -> None:
        """Рекурсивный обход AST — собрать все узлы-идентификаторы с данным именем."""
        if "identifier" in node.type and node.text.decode("utf-8") == name:
            result.append(self._to_range(node))
        for child in node.children:
            self._collect_identifiers(child, name, result)

    # ── Hover Info ─────────────────────────────────────────────────────────

    # Маппинг SymbolKind → человекочитаемое название
    _KIND_LABELS = {
        types.SymbolKind.Function: "function",
        types.SymbolKind.Method: "method",
        types.SymbolKind.Class: "class",
        types.SymbolKind.Interface: "interface",
        types.SymbolKind.Struct: "struct",
        types.SymbolKind.Namespace: "namespace",
        types.SymbolKind.Constructor: "constructor",
        types.SymbolKind.Variable: "variable",
        types.SymbolKind.Constant: "constant",
        types.SymbolKind.Enum: "enum",
        types.SymbolKind.TypeParameter: "type alias",
    }

    def get_hover(self, source: str, line: int, character: int) -> types.Hover | None:
        """Информация о символе при наведении курсора."""
        tree = self._parse(source)

        node = tree.root_node.descendant_for_point_range(
            (line, character), (line, character)
        )
        if node is None or "identifier" not in node.type:
            return None

        name = node.text.decode("utf-8")

        symbols = self._extract_symbols(tree.root_node)
        found = self._find_symbol_by_name(symbols, name)
        if not found:
            return None

        kind_label = self._KIND_LABELS.get(found.kind, "symbol")
        decl_line = found.range.start.line

        # Извлекаем первую строку определения из исходного кода
        lines = source.splitlines()
        signature = lines[decl_line].strip() if decl_line < len(lines) else name

        # Markdown hover:
        #   1. Код-блок с подсветкой синтаксиса (через LANGUAGE_ID наследника)
        #   2. Горизонтальный разделитель
        #   3. Kind (жирным) — line N (em-dash как разделитель)
        md = (
            f"```{self.LANGUAGE_ID}\n"
            f"{signature}\n"
            f"```\n"
            f"---\n"
            f"**{kind_label}** — line {decl_line + 1}"
        )

        return types.Hover(
            contents=types.MarkupContent(
                kind=types.MarkupKind.Markdown,
                value=md,
            ),
            range=self._to_range(node),
        )

    # ── References with context (для кастомной WebView-панели) ───────────

    def get_references_with_context(
        self, source: str, line: int, character: int, include_declaration: bool = True,
    ) -> dict | None:
        """
        Найти все референсы символа под курсором + извлечь строку-сниппет из
        исходника для каждого вхождения. Используется кастомной командой
        ide-navigator.references → Obsidian-style WebView-панель.
        """
        tree = self._parse(source)

        node = tree.root_node.descendant_for_point_range(
            (line, character), (line, character)
        )
        if node is None or "identifier" not in node.type:
            return None

        name = node.text.decode("utf-8")

        # Переиспользуем существующую find_references
        ranges = self.find_references(source, line, character, include_declaration)
        if not ranges:
            return None

        src_lines = source.splitlines()
        refs = []
        for r in ranges:
            line_idx = r.start.line
            snippet = src_lines[line_idx] if line_idx < len(src_lines) else ""
            refs.append({
                "line": line_idx,
                "character": r.start.character,
                "endCharacter": r.end.character,
                "snippet": snippet,
            })

        refs.sort(key=lambda item: (item["line"], item["character"]))

        return {
            "name": name,
            "language": self.LANGUAGE_ID,
            "refs": refs,
        }

    # ── Call Graph ─────────────────────────────────────────────────────────

    # Маппинг SymbolKind → строковый тип для графа
    _GRAPH_KIND_MAP = {
        types.SymbolKind.Function: "function",
        types.SymbolKind.Method: "method",
        types.SymbolKind.Constructor: "constructor",
        types.SymbolKind.Class: "class",
        types.SymbolKind.Interface: "interface",
        types.SymbolKind.Struct: "struct",
    }

    # Белый список допустимых типов в графе — всё что не в списке → "function".
    # Защищает WebView от инъекций: даже если tree-sitter выдаст экзотический
    # node.type, в JSON попадёт только безопасное значение.
    _GRAPH_ALLOWED_TYPES = frozenset({
        "function", "method", "constructor", "class", "interface", "struct",
    })

    # Максимальная длина идентификатора — защита от DoS и мусора в UI.
    _GRAPH_MAX_LABEL_LEN = 120

    # Узлы tree-sitter, считающиеся точками ветвления для цикломатической
    # сложности по McCabe (упрощённая формула: 1 + число branch points).
    #
    # Ключевые слова-токены (if, for, while и т.п.) НЕ включаем — tree-sitter
    # кладёт их как детей statement-узла и мы бы двойным счётом ловили каждое
    # ветвление. Считаем только структурные узлы: *_statement / *_clause /
    # *_expression (для тернарников). else_clause не считается — это
    # fallthrough-ветка, она не добавляет путь по McCabe.
    _BRANCH_NODE_TYPES = frozenset({
        # if / elif
        "if_statement", "elif_clause",
        # Циклы
        "for_statement", "for_in_statement", "for_of_statement",
        "for_range_loop",
        "while_statement", "do_statement", "do_while_statement",
        "repeat_while_statement",
        # switch / case — считаем ТОЛЬКО cases, сам switch не добавляет путь
        # если в нём нет альтернатив (default без case = 1 путь).
        "case_statement", "case_clause", "switch_case",
        "switch_block_statement_group",  # Java: обёртка над каждым case-блоком
        "expression_case", "type_case", "communication_case",
        # Исключения (сам try/except не считаем — только handler-clause)
        "except_clause", "catch_clause",
        # Тернарник
        "conditional_expression", "ternary_expression",
        # Go select / Swift guard
        "select_statement", "guard_statement",
    })

    def get_call_graph(self, source: str) -> dict:
        """Построить граф вызовов: какие функции вызывают какие.

        Возвращает:
          nodes: [{id, label, type, line, character, endLine, endCharacter, complexity}]
            — координаты указывают на идентификатор (selection_range),
              чтобы клик в webview открывал файл ровно на имени символа.
            — complexity: cyclomatic complexity по McCabe (1 + число ветвлений).
          edges: [{from, to, kind}]
            — kind="call" (вызов функции/метода) или "contains"
              (класс → его метод/конструктор).
        """
        tree = self._parse(source)
        root = tree.root_node

        # Собираем все символы (включая классы) с их типами и позициями
        symbols = self._extract_symbols(root)
        # name → {"type": str, "range": lsp Range (selection_range)}
        symbol_info: dict[str, dict] = {}
        self._collect_symbol_info(symbols, symbol_info)

        # Имена функций/методов для отслеживания вызовов
        known_funcs: set[str] = set()
        self._collect_callable_names(symbols, known_funcs)

        # Связи класс → его методы
        contain_edges: set[tuple[str, str]] = set()
        self._collect_class_edges(symbols, contain_edges)

        # Обходим AST, отслеживая текущую функцию, собираем рёбра вызовов
        call_edges: set[tuple[str, str]] = set()
        self._walk_calls(root, None, known_funcs, call_edges)

        # Цикломатическая сложность по имени функции (один проход по AST)
        complexity_map: dict[str, int] = {}
        self._collect_complexity(root, complexity_map)

        # Все участники графа: функции + классы (у которых есть методы)
        container_types = ("class", "interface", "struct")
        all_ids = known_funcs | {
            n for n, info in symbol_info.items() if info["type"] in container_types
        }

        def safe_label(name: str) -> str:
            return name[:self._GRAPH_MAX_LABEL_LEN]

        def safe_type(raw_type: str) -> str:
            return raw_type if raw_type in self._GRAPH_ALLOWED_TYPES else "function"

        nodes = []
        for n in sorted(all_ids):
            info = symbol_info.get(n, {})
            node = {
                "id": safe_label(n),
                "label": safe_label(n),
                "type": safe_type(info.get("type", "function")),
            }
            rng = info.get("range")
            if rng is not None:
                node["line"] = rng.start.line
                node["character"] = rng.start.character
                node["endLine"] = rng.end.line
                node["endCharacter"] = rng.end.character
            if n in complexity_map:
                node["complexity"] = complexity_map[n]
            nodes.append(node)

        edge_list: list[dict] = []
        for a, b in sorted(call_edges):
            edge_list.append({
                "from": safe_label(a), "to": safe_label(b), "kind": "call",
            })
        for a, b in sorted(contain_edges):
            edge_list.append({
                "from": safe_label(a), "to": safe_label(b), "kind": "contains",
            })

        return {"nodes": nodes, "edges": edge_list}

    def _collect_class_edges(
        self, symbols: list[types.DocumentSymbol], edges: set[tuple[str, str]],
    ) -> None:
        """Добавить рёбра класс → его методы/конструкторы."""
        for s in symbols:
            if s.kind in (types.SymbolKind.Class, types.SymbolKind.Interface,
                          types.SymbolKind.Struct) and s.children:
                for child in s.children:
                    if child.kind in (types.SymbolKind.Function, types.SymbolKind.Method,
                                      types.SymbolKind.Constructor):
                        edges.add((s.name, child.name))

    def _collect_symbol_info(
        self, symbols: list[types.DocumentSymbol], result: dict[str, dict],
    ) -> None:
        """Собрать все символы с типами и позициями идентификатора (selection_range).

        Если одно имя встречается несколько раз (перегрузка/коллизия), остаётся
        первая встреченная позиция — клик-навигация прыгнет к ней. Полноценная
        дизамбигуация имён вида Class.method — отдельная задача из бэклога.
        """
        for s in symbols:
            kind_str = self._GRAPH_KIND_MAP.get(s.kind)
            if kind_str and s.name not in result:
                result[s.name] = {
                    "type": kind_str,
                    "range": s.selection_range,
                }
            if s.children:
                self._collect_symbol_info(s.children, result)

    def _collect_callable_names(
        self, symbols: list[types.DocumentSymbol], result: set[str],
    ) -> None:
        """Собрать имена функций и методов из дерева символов."""
        for s in symbols:
            if s.kind in (types.SymbolKind.Function, types.SymbolKind.Method,
                          types.SymbolKind.Constructor):
                result.add(s.name)
            if s.children:
                self._collect_callable_names(s.children, result)

    def _collect_complexity(self, root, result: dict[str, int]) -> None:
        """
        Обход AST: для каждого определения функции/метода/конструктора считаем
        цикломатическую сложность по McCabe = 1 + число узлов-ветвлений в теле.
        Результат — mapping имя → сложность.

        При коллизии имён (как и везде в графе) остаётся последнее значение —
        это согласуется с поведением остальных частей Call Graph. Полное
        разделение перегрузок решается Class.method-квалификацией (отдельная
        задача из бэклога).
        """
        stack = [root]
        while stack:
            node = stack.pop()
            name = self._get_func_def_name(node)
            if name is not None:
                result[name] = self._compute_complexity(node)
            for child in node.children:
                stack.append(child)

    def _compute_complexity(self, func_node) -> int:
        """Посчитать цикломатическую сложность одного узла-функции."""
        count = 1
        stack = [func_node]
        while stack:
            node = stack.pop()
            if node.type in self._BRANCH_NODE_TYPES:
                count += 1
            for child in node.children:
                stack.append(child)
        return count

    def _walk_calls(
        self, node, current_func: str | None,
        known: set[str], edges: set[tuple[str, str]],
    ) -> None:
        """Рекурсивный обход AST: отслеживать текущую функцию, собирать вызовы."""
        func_name = self._get_func_def_name(node)
        if func_name is not None:
            current_func = func_name

        if current_func is not None:
            callee = self._get_call_name(node)
            if callee and callee in known:
                edges.add((current_func, callee))

        for child in node.children:
            self._walk_calls(child, current_func, known, edges)

    def _get_func_def_name(self, node) -> str | None:
        """Если узел — определение функции/метода, вернуть имя. Иначе None."""
        if node.type in (
            "function_definition", "function_declaration",
            "method_definition", "method_declaration",
            "constructor_declaration",
        ):
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8")
        return None

    def _get_call_name(self, node) -> str | None:
        """Если узел — вызов функции, вернуть имя вызываемой функции."""
        if node.type not in ("call", "call_expression", "method_invocation"):
            return None

        func_node = (
            node.child_by_field_name("function")
            or node.child_by_field_name("name")
        )
        if func_node is None:
            return None

        # Простой вызов: foo()
        if func_node.type in ("identifier", "field_identifier", "property_identifier"):
            return func_node.text.decode("utf-8")

        # Вызов метода: obj.foo() → извлекаем "foo"
        if func_node.type in ("attribute", "member_expression",
                              "selector_expression", "field_expression"):
            attr = (
                func_node.child_by_field_name("attribute")
                or func_node.child_by_field_name("property")
                or func_node.child_by_field_name("field")
            )
            if attr:
                return attr.text.decode("utf-8")

        return None

    # ── Вспомогательные методы (доступны всем наследникам) ────────────────

    def _make_symbol(
        self,
        name: str,
        kind: types.SymbolKind,
        node,
        name_node=None,
        children: list | None = None,
    ) -> types.DocumentSymbol:
        """Создать DocumentSymbol из узла AST."""
        selection = name_node if name_node is not None else node
        return types.DocumentSymbol(
            name=name,
            kind=kind,
            range=self._to_range(node),
            selection_range=self._to_range(selection),
            children=children or [],
        )
