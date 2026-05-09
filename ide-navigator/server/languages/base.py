"""
Базовый класс для всех языковых модулей — фасад над миксинами.

Разделение ответственности:
  _parse_cache.py  — ParseCacheMixin: tree-sitter + LRU + incremental parsing
  _definition.py   — DefinitionMixin: go-to-definition + cross-file import-resolve
  _references.py   — ReferencesMixin: find-references + CodeLens-counts
  _hover.py        — HoverMixin: tooltip с сигнатурой + complexity
  _call_graph.py   — CallGraphMixin: call graph + McCabe complexity + AST-хелперы

Чтобы добавить новый язык — создай класс который наследует BaseLanguage
и реализует два метода: get_parser() и _extract_symbols().
Смотри python_lang.py как пример.
"""
from abc import ABC, abstractmethod
from tree_sitter import Parser
from lsprotocol import types

from languages._parse_cache import ParseCacheMixin
from languages._definition import DefinitionMixin
from languages._references import ReferencesMixin
from languages._hover import HoverMixin
from languages._call_graph import CallGraphMixin


class BaseLanguage(
    ParseCacheMixin,
    DefinitionMixin,
    ReferencesMixin,
    HoverMixin,
    CallGraphMixin,
    ABC,
):

    @abstractmethod
    def get_parser(self) -> Parser:
        """Вернуть настроенный парсер tree-sitter для этого языка."""
        pass

    @abstractmethod
    def _extract_symbols(self, node) -> list[types.DocumentSymbol]:
        """Обойти AST и собрать символы (функции, классы, методы)."""
        pass

    def get_symbols(self, source: str, uri: str | None = None) -> list[types.DocumentSymbol]:
        """Главный метод — извлечь все символы из исходного кода."""
        tree = self._parse(source, uri)
        return self._extract_symbols(tree.root_node)

    # ── Вспомогательный метод для наследников ─────────────────────────────

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
