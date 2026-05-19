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
        pass

    @abstractmethod
    def _extract_symbols(self, node) -> list[types.DocumentSymbol]:
        pass

    def get_symbols(self, source: str, uri: str | None = None) -> list[types.DocumentSymbol]:
        tree = self._parse(source, uri)
        return self._extract_symbols(tree.root_node)

    def _make_symbol(
        self,
        name: str,
        kind: types.SymbolKind,
        node,
        name_node=None,
        children: list | None = None,
    ) -> types.DocumentSymbol:
        selection = name_node if name_node is not None else node
        return types.DocumentSymbol(
            name=name,
            kind=kind,
            range=self._to_range(node),
            selection_range=self._to_range(selection),
            children=children or [],
        )
