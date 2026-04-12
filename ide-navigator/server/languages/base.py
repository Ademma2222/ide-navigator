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
