from tree_sitter import Language, Parser
import tree_sitter_java as tsjava
from lsprotocol import types
from .base import BaseLanguage

class JavaLanguage(BaseLanguage):

    LANGUAGE_ID = "java"

    def get_parser(self) -> Parser:
        return Parser(Language(tsjava.language()))

    def _extract_symbols(self, node, inside_class: bool = False) -> list[types.DocumentSymbol]:
        symbols = []

        for child in node.children:

            if child.type in ("class_declaration", "enum_declaration"):
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

            elif child.type == "interface_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    body = child.child_by_field_name("body")
                    children = self._extract_symbols(body, inside_class=True) if body else []
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=types.SymbolKind.Interface,
                        node=child,
                        name_node=name_node,
                        children=children,
                    ))

            elif child.type == "method_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=types.SymbolKind.Method,
                        node=child,
                        name_node=name_node,
                    ))

            elif child.type == "constructor_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=types.SymbolKind.Constructor,
                        node=child,
                        name_node=name_node,
                    ))

            else:
                symbols.extend(self._extract_symbols(child, inside_class))

        return symbols
