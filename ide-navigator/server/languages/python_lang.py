from tree_sitter import Language, Parser
import tree_sitter_python as tspython
from lsprotocol import types
from .base import BaseLanguage


class PythonLanguage(BaseLanguage):

    def get_parser(self) -> Parser:
        return Parser(Language(tspython.language()))

    def _extract_symbols(self, node, inside_class: bool = False) -> list[types.DocumentSymbol]:
        symbols = []

        for child in node.children:

            if child.type == "function_definition":
                name_node = child.child_by_field_name("name")
                if name_node:
                    kind = types.SymbolKind.Method if inside_class else types.SymbolKind.Function
                    body = child.child_by_field_name("body")
                    children = self._extract_symbols(body, inside_class=False) if body else []
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=kind,
                        node=child,
                        name_node=name_node,
                        children=children,
                    ))

            elif child.type == "class_definition":
                name_node = child.child_by_field_name("name")
                if name_node:
                    body = child.child_by_field_name("body")
                    children = self._extract_symbols(body, inside_class=True) if body else []
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=types.SymbolKind.Class,
                        node=child,
                        name_node=name_node,
                        children=children,
                    ))

            elif child.type in ("module", "block"):
                symbols.extend(self._extract_symbols(child, inside_class))

        return symbols
