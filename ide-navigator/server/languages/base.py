"""
Базовый класс для всех языковых модулей.

Дима: чтобы добавить новый язык — создай класс который наследует BaseLanguage
и реализует два метода: get_parser() и _extract_symbols().
Смотри python_lang.py как пример.
"""
from abc import ABC, abstractmethod
from tree_sitter import Parser
from lsprotocol import types


class BaseLanguage(ABC):

    @abstractmethod
    def get_parser(self) -> Parser:
        """Вернуть настроенный парсер tree-sitter для этого языка."""
        pass

    def get_symbols(self, source: str) -> list[types.DocumentSymbol]:
        """Главный метод — извлечь все символы из исходного кода."""
        parser = self.get_parser()
        tree = parser.parse(bytes(source, "utf-8"))
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
        parser = self.get_parser()
        tree = parser.parse(bytes(source, "utf-8"))

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
        parser = self.get_parser()
        tree = parser.parse(bytes(source, "utf-8"))

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
        parser = self.get_parser()
        tree = parser.parse(bytes(source, "utf-8"))

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

        md = f"```\n({kind_label}) {signature}\n```\n---\nDefined on line {decl_line + 1}"

        return types.Hover(
            contents=types.MarkupContent(
                kind=types.MarkupKind.Markdown,
                value=md,
            ),
            range=self._to_range(node),
        )

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

    def get_call_graph(self, source: str) -> dict:
        """Построить граф вызовов: какие функции вызывают какие."""
        parser = self.get_parser()
        tree = parser.parse(bytes(source, "utf-8"))
        root = tree.root_node

        # Собираем все символы (включая классы) с их типами
        symbols = self._extract_symbols(root)
        symbol_map: dict[str, str] = {}  # name → type string
        self._collect_all_symbol_types(symbols, symbol_map)

        # Имена функций/методов для отслеживания вызовов
        known_funcs: set[str] = set()
        self._collect_callable_names(symbols, known_funcs)

        # Связи класс → его методы
        edges: set[tuple[str, str]] = set()
        self._collect_class_edges(symbols, edges)

        # Обходим AST, отслеживая текущую функцию, собираем рёбра вызовов
        self._walk_calls(root, None, known_funcs, edges)

        # Все участники графа: функции + классы (у которых есть методы)
        all_ids = known_funcs | {n for n in symbol_map if symbol_map[n] in ("class", "interface", "struct")}
        nodes = [
            {"id": n, "label": n, "type": symbol_map.get(n, "function")}
            for n in sorted(all_ids)
        ]
        edge_list = [{"from": a, "to": b} for a, b in sorted(edges)]

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

    def _collect_all_symbol_types(
        self, symbols: list[types.DocumentSymbol], result: dict[str, str],
    ) -> None:
        """Собрать все символы с их типами для графа."""
        for s in symbols:
            kind_str = self._GRAPH_KIND_MAP.get(s.kind)
            if kind_str:
                result[s.name] = kind_str
            if s.children:
                self._collect_all_symbol_types(s.children, result)

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
