"""
Базовый класс для всех языковых модулей.

Дима: чтобы добавить новый язык — создай класс который наследует BaseLanguage
и реализует два метода: get_parser() и _extract_symbols().
Смотри python_lang.py как пример.
"""
import logging
import os
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse, unquote
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

        # Per-URI кэш последнего дерева для incremental parsing.
        # При cache miss передаём old_tree в parser.parse() — tree-sitter
        # переиспользует неизменившиеся узлы и парсит быстрее.
        self._uri_tree_cache: OrderedDict[str, object] = OrderedDict()

    @abstractmethod
    def get_parser(self) -> Parser:
        """Вернуть настроенный парсер tree-sitter для этого языка."""
        pass

    def _parse(self, source: str, uri: str | None = None):
        """
        Разобрать исходник через tree-sitter с LRU-кэшем.
        Все методы класса (get_symbols, find_definition и т.д.) должны
        использовать этот метод вместо `self.get_parser().parse(...)`.

        uri — опциональный URI файла. Если указан, используется для
        incremental parsing: при cache miss берём old_tree из предыдущей
        версии этого файла и передаём в parser.parse() как hint.
        """
        cached = self._parse_cache.get(source)
        if cached is not None:
            self._parse_cache.move_to_end(source)
            return cached

        # Incremental parsing: ищем old_tree для этого URI
        old_tree = self._uri_tree_cache.get(uri) if uri else None

        start = time.perf_counter()
        source_bytes = bytes(source, "utf-8")
        if old_tree is not None:
            tree = self.get_parser().parse(source_bytes, old_tree=old_tree)
        else:
            tree = self.get_parser().parse(source_bytes)
        elapsed_ms = (time.perf_counter() - start) * 1000

        mode = "incremental" if old_tree else "full"
        logger.info(
            f"parse[{self.LANGUAGE_ID}]: {len(source)} bytes in {elapsed_ms:.1f}ms ({mode})"
        )

        self._parse_cache[source] = tree
        if len(self._parse_cache) > self._PARSE_CACHE_MAX:
            self._parse_cache.popitem(last=False)

        # Обновить per-URI кэш
        if uri:
            self._uri_tree_cache[uri] = tree
            if len(self._uri_tree_cache) > self._PARSE_CACHE_MAX:
                self._uri_tree_cache.popitem(last=False)

        return tree

    def get_symbols(self, source: str, uri: str | None = None) -> list[types.DocumentSymbol]:
        """Главный метод — извлечь все символы из исходного кода."""
        tree = self._parse(source, uri)
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

    def find_definition(self, source: str, line: int, character: int, uri: str | None = None) -> types.Range | None:
        """Найти определение символа под курсором (внутри одного файла)."""
        tree = self._parse(source, uri)

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

    def find_cross_file_definition(
        self, source: str, line: int, character: int, uri: str,
        language_map: dict,
    ) -> types.Location | None:
        """Найти определение символа в другом файле через import-tracking.

        Реализация:
        1. Находим идентификатор под курсором.
        2. Ищем import-statement, из которого он импортирован.
        3. Резолвим путь целевого файла.
        4. Парсим целевой файл и ищем определение символа.
        """
        tree = self._parse(source, uri)
        node = tree.root_node.descendant_for_point_range(
            (line, character), (line, character)
        )
        if node is None or "identifier" not in node.type:
            return None

        name = node.text.decode("utf-8")

        # Ищем импорт-отображение: {imported_name: (module_path, original_name)}
        imports = self._extract_imports(tree.root_node, uri)
        if name not in imports:
            return None

        target_path, original_name = imports[name]
        if target_path is None or not target_path.exists():
            return None

        ext = target_path.suffix.lower()
        target_lang = language_map.get(ext)
        if target_lang is None:
            return None

        try:
            target_source = target_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        target_uri = target_path.as_uri()
        symbols = target_lang.get_symbols(target_source, target_uri)
        found = self._find_symbol_by_name(symbols, original_name)
        if found:
            return types.Location(uri=target_uri, range=found.selection_range)
        return None

    def _extract_imports(self, root_node, uri: str) -> dict[str, tuple[Path | None, str]]:
        """Извлечь импорты из AST. Возвращает {local_name: (resolved_path, original_name)}.

        По умолчанию — пустой словарь. Языковые модули переопределяют для
        Python, JS/TS и т.д.
        """
        return {}

    @staticmethod
    def _uri_to_path(uri: str) -> Path:
        """Конвертировать file:// URI в Path."""
        parsed = urlparse(uri).path
        path = unquote(parsed)
        if os.name == "nt" and path.startswith("/"):
            path = path[1:]
        return Path(path)

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

    def _find_symbol_fqn(
        self, symbols: list[types.DocumentSymbol], name: str, prefix: str = "",
    ) -> str | None:
        """Найти FQN символа по короткому имени (для complexity lookup)."""
        for s in symbols:
            fqn = f"{prefix}.{s.name}" if prefix else s.name
            if s.name == name:
                return fqn
            if s.children:
                found = self._find_symbol_fqn(s.children, name, fqn)
                if found:
                    return found
        return None

    # ── Find All References ───────────────────────────────────────────────

    def find_references(
        self, source: str, line: int, character: int, include_declaration: bool = True,
        uri: str | None = None,
    ) -> list[types.Range]:
        """Найти все вхождения идентификатора под курсором в файле."""
        tree = self._parse(source, uri)

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

    def get_hover(self, source: str, line: int, character: int, uri: str | None = None) -> types.Hover | None:
        """Информация о символе при наведении курсора."""
        tree = self._parse(source, uri)

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

        # Цикломатическая сложность (для функций/методов/конструкторов)
        complexity_str = ""
        if found.kind in (types.SymbolKind.Function, types.SymbolKind.Method,
                          types.SymbolKind.Constructor):
            complexity_map: dict[str, int] = {}
            self._collect_complexity(tree.root_node, complexity_map)
            fqn = self._find_symbol_fqn(symbols, name) or name
            cc = complexity_map.get(fqn)
            if cc is not None:
                complexity_str = f" · complexity {cc}"

        # Markdown hover:
        #   1. Код-блок с подсветкой синтаксиса (через LANGUAGE_ID наследника)
        #   2. Горизонтальный разделитель
        #   3. Kind (жирным) — line N — complexity (em-dash как разделитель)
        md = (
            f"```{self.LANGUAGE_ID}\n"
            f"{signature}\n"
            f"```\n"
            f"---\n"
            f"**{kind_label}** — line {decl_line + 1}{complexity_str}"
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
        uri: str | None = None,
    ) -> dict | None:
        """
        Найти все референсы символа под курсором + извлечь строку-сниппет из
        исходника для каждого вхождения. Используется кастомной командой
        ide-navigator.references → Obsidian-style WebView-панель.
        """
        tree = self._parse(source, uri)

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

    def get_call_graph(self, source: str, uri: str | None = None) -> dict:
        """Построить граф вызовов: какие функции вызывают какие.

        Возвращает:
          nodes: [{id, label, type, line, character, endLine, endCharacter, complexity}]
            — id = FQN (Class.method), label = short name для отображения.
            — координаты указывают на идентификатор (selection_range),
              чтобы клик в webview открывал файл ровно на имени символа.
            — complexity: cyclomatic complexity по McCabe (1 + число ветвлений).
          edges: [{from, to, kind}]
            — kind="call" (вызов функции/метода) или "contains"
              (класс → его метод/конструктор).
        """
        tree = self._parse(source, uri)
        root = tree.root_node

        # Собираем все символы (включая классы) с их типами и позициями
        symbols = self._extract_symbols(root)

        # FQN → {"type": str, "range": lsp Range, "label": short_name}
        symbol_info: dict[str, dict] = {}
        self._collect_symbol_info(symbols, symbol_info)

        # FQN функций/методов для отслеживания вызовов
        known_funcs: set[str] = set()
        self._collect_callable_names(symbols, known_funcs)

        # short_name → list of FQNs (для резолва вызовов)
        short_to_fqn: dict[str, list[str]] = {}
        for fqn in known_funcs:
            short = fqn.rsplit(".", 1)[-1]
            short_to_fqn.setdefault(short, []).append(fqn)

        # Связи класс → его методы (теперь с FQN)
        contain_edges: set[tuple[str, str]] = set()
        self._collect_class_edges(symbols, contain_edges)

        # Обходим AST, отслеживая текущую функцию (FQN), собираем рёбра вызовов
        call_edges: set[tuple[str, str]] = set()
        self._walk_calls(root, None, known_funcs, call_edges, short_to_fqn)

        # Цикломатическая сложность по FQN
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
                "label": safe_label(info.get("label", n)),
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
        prefix: str = "",
    ) -> None:
        """Добавить рёбра класс → его методы/конструкторы (FQN)."""
        for s in symbols:
            fqn = f"{prefix}.{s.name}" if prefix else s.name
            if s.kind in (types.SymbolKind.Class, types.SymbolKind.Interface,
                          types.SymbolKind.Struct) and s.children:
                for child in s.children:
                    child_fqn = f"{fqn}.{child.name}"
                    if child.kind in (types.SymbolKind.Function, types.SymbolKind.Method,
                                      types.SymbolKind.Constructor):
                        edges.add((fqn, child_fqn))
            if s.children:
                self._collect_class_edges(s.children, edges, fqn)

    def _collect_symbol_info(
        self, symbols: list[types.DocumentSymbol], result: dict[str, dict],
        prefix: str = "",
    ) -> None:
        """Собрать все символы с FQN-ключами, типами и позициями."""
        for s in symbols:
            fqn = f"{prefix}.{s.name}" if prefix else s.name
            kind_str = self._GRAPH_KIND_MAP.get(s.kind)
            if kind_str and fqn not in result:
                result[fqn] = {
                    "type": kind_str,
                    "range": s.selection_range,
                    "label": s.name,
                }
            if s.children:
                self._collect_symbol_info(s.children, result, fqn)

    def _collect_callable_names(
        self, symbols: list[types.DocumentSymbol], result: set[str],
        prefix: str = "",
    ) -> None:
        """Собрать FQN функций и методов из дерева символов."""
        for s in symbols:
            fqn = f"{prefix}.{s.name}" if prefix else s.name
            if s.kind in (types.SymbolKind.Function, types.SymbolKind.Method,
                          types.SymbolKind.Constructor):
                result.add(fqn)
            if s.children:
                self._collect_callable_names(s.children, result, fqn)

    def _collect_complexity(self, root, result: dict[str, int],
                            scope: str = "") -> None:
        """
        Обход AST: для каждого определения функции/метода/конструктора считаем
        цикломатическую сложность по McCabe = 1 + число узлов-ветвлений в теле.
        Результат — mapping FQN → сложность.
        """
        stack: list[tuple] = [(root, scope)]
        while stack:
            node, cur_scope = stack.pop()
            name = self._get_func_def_name(node)
            if name is not None:
                fqn = f"{cur_scope}.{name}" if cur_scope else name
                result[fqn] = self._compute_complexity(node)
                # Дети наследуют scope
                for child in node.children:
                    stack.append((child, fqn))
            else:
                # Классы тоже формируют scope
                cls_name = self._get_class_def_name(node)
                if cls_name:
                    child_scope = f"{cur_scope}.{cls_name}" if cur_scope else cls_name
                else:
                    child_scope = cur_scope
                for child in node.children:
                    stack.append((child, child_scope))

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
        short_to_fqn: dict[str, list[str]] | None = None,
        scope: str = "",
    ) -> None:
        """Рекурсивный обход AST: отслеживать текущую функцию (FQN), собирать вызовы."""
        func_name = self._get_func_def_name(node)
        cls_name = self._get_class_def_name(node) if func_name is None else None

        if func_name is not None:
            current_func = f"{scope}.{func_name}" if scope else func_name
            scope = current_func
        elif cls_name is not None:
            scope = f"{scope}.{cls_name}" if scope else cls_name

        if current_func is not None:
            callee = self._get_call_name(node)
            if callee:
                # Пробуем найти FQN callee
                resolved = False
                if short_to_fqn and callee in short_to_fqn:
                    for fqn in short_to_fqn[callee]:
                        edges.add((current_func, fqn))
                        resolved = True
                if not resolved and callee in known:
                    edges.add((current_func, callee))

        for child in node.children:
            self._walk_calls(child, current_func, known, edges, short_to_fqn, scope)

    def _get_class_def_name(self, node) -> str | None:
        """Если узел — определение класса/интерфейса/структуры, вернуть имя."""
        if node.type in (
            "class_definition", "class_declaration",
            "interface_declaration", "struct_specifier",
            "type_spec",  # Go struct
        ):
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8")
        return None

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
