from tree_sitter import Language, Parser
import tree_sitter_cpp as tscpp
from lsprotocol import types
from .base import BaseLanguage

class CppLanguage(BaseLanguage):

    LANGUAGE_ID = "cpp"

    def get_parser(self) -> Parser:
        return Parser(Language(tscpp.language()))

    def _extract_symbols(self, node, inside_class: bool = False) -> list[types.DocumentSymbol]:
        symbols = []

        for child in node.children:

            if child.type in ("class_specifier", "struct_specifier"):
                name_node = self._child_of_type(child, "type_identifier")
                if name_node:
                    kind = types.SymbolKind.Class if child.type == "class_specifier" else types.SymbolKind.Struct
                    body = child.child_by_field_name("body")
                    children = self._extract_symbols(body, inside_class=True) if body else []
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=kind,
                        node=child,
                        name_node=name_node,
                        children=children,
                    ))

            elif child.type == "namespace_definition":
                name_node = self._child_of_type(child, "namespace_identifier")
                body = child.child_by_field_name("body")
                inner = self._extract_symbols(body, inside_class=False) if body else []
                if name_node:
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=types.SymbolKind.Namespace,
                        node=child,
                        name_node=name_node,
                        children=inner,
                    ))

            elif child.type == "function_definition":
                name_node = self._func_name(child)
                if name_node:
                    kind = types.SymbolKind.Method if inside_class else types.SymbolKind.Function
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=kind,
                        node=child,
                        name_node=name_node,
                    ))

            elif child.type in ("translation_unit", "declaration_list", "field_declaration_list"):
                symbols.extend(self._extract_symbols(child, inside_class))

        return symbols

    def _get_func_def_name(self, node) -> str | None:
        if node.type == "function_definition":
            name_node = self._func_name(node)
            if name_node:
                return name_node.text.decode("utf-8")
        return None

    def _func_name(self, func_node):
        declarator = func_node.child_by_field_name("declarator")
        if declarator and declarator.type == "function_declarator":
            inner = declarator.child_by_field_name("declarator")
            if inner and inner.type in ("identifier", "field_identifier"):
                return inner
        return None

    def _child_of_type(self, node, type_name: str):
        for c in node.children:
            if c.type == type_name:
                return c
        return None
