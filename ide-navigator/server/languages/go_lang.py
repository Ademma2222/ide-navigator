from tree_sitter import Language, Parser
import tree_sitter_go as tsgo
from lsprotocol import types
from .base import BaseLanguage

class GoLanguage(BaseLanguage):

    LANGUAGE_ID = "go"

    def get_parser(self) -> Parser:
        return Parser(Language(tsgo.language()))

    def _extract_symbols(self, node, inside_class: bool = False) -> list[types.DocumentSymbol]:
        symbols = []

        for child in node.children:

            if child.type == "function_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=types.SymbolKind.Function,
                        node=child,
                        name_node=name_node,
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

            elif child.type == "type_declaration":
                for spec in child.children:
                    if spec.type == "type_spec":
                        name_node = spec.child_by_field_name("name")
                        type_node = spec.child_by_field_name("type")
                        if name_node and type_node:
                            if type_node.type == "struct_type":
                                kind = types.SymbolKind.Struct
                            elif type_node.type == "interface_type":
                                kind = types.SymbolKind.Interface
                            else:
                                kind = types.SymbolKind.TypeParameter
                            symbols.append(self._make_symbol(
                                name=name_node.text.decode("utf-8"),
                                kind=kind,
                                node=spec,
                                name_node=name_node,
                            ))

            elif child.type == "const_declaration":
                for spec in child.children:
                    if spec.type == "const_spec":
                        name_node = spec.child_by_field_name("name")
                        if name_node:
                            symbols.append(self._make_symbol(
                                name=name_node.text.decode("utf-8"),
                                kind=types.SymbolKind.Constant,
                                node=spec,
                                name_node=name_node,
                            ))

            elif child.type == "var_declaration":
                for spec in child.children:
                    if spec.type == "var_spec":
                        name_node = spec.child_by_field_name("name")
                        if name_node:
                            symbols.append(self._make_symbol(
                                name=name_node.text.decode("utf-8"),
                                kind=types.SymbolKind.Variable,
                                node=spec,
                                name_node=name_node,
                            ))

        return symbols
