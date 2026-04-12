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
