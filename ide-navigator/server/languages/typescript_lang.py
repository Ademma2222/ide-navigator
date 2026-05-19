from tree_sitter import Language, Parser
import tree_sitter_typescript as tsts
from lsprotocol import types
from .javascript_lang import JavaScriptLanguage

class TypeScriptLanguage(JavaScriptLanguage):

    LANGUAGE_ID = "typescript"

    def get_parser(self) -> Parser:
        return Parser(Language(tsts.language_typescript()))

    def _extract_symbols(self, node, inside_class: bool = False) -> list[types.DocumentSymbol]:
        symbols = super()._extract_symbols(node, inside_class)

        for child in node.children:

            if child.type == "interface_declaration":
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

            elif child.type == "type_alias_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=types.SymbolKind.TypeParameter,
                        node=child,
                        name_node=name_node,
                    ))

            elif child.type == "enum_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=types.SymbolKind.Enum,
                        node=child,
                        name_node=name_node,
                    ))

        return symbols
