from tree_sitter import Language, Parser
import tree_sitter_swift as tsswift
from lsprotocol import types
from .base import BaseLanguage


class SwiftLanguage(BaseLanguage):

    def get_parser(self) -> Parser:
        return Parser(Language(tsswift.language()))

    def _extract_symbols(self, node, inside_class: bool = False) -> list[types.DocumentSymbol]:
        symbols = []

        for child in node.children:

            if child.type == "class_declaration":
                # tree-sitter-swift использует class_declaration для class, struct и enum
                keyword = self._child_of_types(child, ("class", "struct", "enum", "actor"))
                name_node = self._child_of_types(child, ("type_identifier",))
                if name_node:
                    if keyword and keyword.type == "struct":
                        kind = types.SymbolKind.Struct
                    elif keyword and keyword.type == "enum":
                        kind = types.SymbolKind.Enum
                    else:
                        kind = types.SymbolKind.Class
                    body = self._child_of_types(child, ("class_body", "enum_class_body"))
                    children = self._extract_symbols(body, inside_class=True) if body else []
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=kind,
                        node=child,
                        name_node=name_node,
                        children=children,
                    ))

            elif child.type == "function_declaration":
                name_node = self._child_of_types(child, ("simple_identifier",))
                if name_node:
                    kind = types.SymbolKind.Method if inside_class else types.SymbolKind.Function
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=kind,
                        node=child,
                        name_node=name_node,
                    ))

            elif child.type == "protocol_declaration":
                name_node = self._child_of_types(child, ("type_identifier",))
                if name_node:
                    body = self._child_of_types(child, ("protocol_body",))
                    children = self._extract_symbols(body, inside_class=True) if body else []
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=types.SymbolKind.Interface,
                        node=child,
                        name_node=name_node,
                        children=children,
                    ))

            elif child.type in ("source_file", "statements", "class_body", "enum_class_body", "protocol_body"):
                symbols.extend(self._extract_symbols(child, inside_class))

        return symbols

    def _child_of_types(self, node, type_names: tuple):
        for c in node.children:
            if c.type in type_names:
                return c
        return None
