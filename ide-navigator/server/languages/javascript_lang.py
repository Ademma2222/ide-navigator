from tree_sitter import Language, Parser
import tree_sitter_javascript as tsjs
from lsprotocol import types
from .base import BaseLanguage


class JavaScriptLanguage(BaseLanguage):

    def get_parser(self) -> Parser:
        return Parser(Language(tsjs.language()))

    def _extract_symbols(self, node, inside_class: bool = False) -> list[types.DocumentSymbol]:
        symbols = []

        for child in node.children:

            if child.type == "class_declaration":
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

            elif child.type == "function_declaration":
                name_node = child.child_by_field_name("name")
                if name_node:
                    symbols.append(self._make_symbol(
                        name=name_node.text.decode("utf-8"),
                        kind=types.SymbolKind.Function,
                        node=child,
                        name_node=name_node,
                    ))

            elif child.type == "method_definition":
                name_node = child.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode("utf-8")
                    kind = types.SymbolKind.Constructor if name == "constructor" else types.SymbolKind.Method
                    symbols.append(self._make_symbol(
                        name=name,
                        kind=kind,
                        node=child,
                        name_node=name_node,
                    ))

            elif child.type in ("lexical_declaration", "variable_declaration"):
                for decl in child.children:
                    if decl.type == "variable_declarator":
                        name_node = decl.child_by_field_name("name")
                        if name_node:
                            value = decl.child_by_field_name("value")
                            if value and value.type in ("arrow_function", "function_expression"):
                                kind = types.SymbolKind.Function
                            else:
                                kind = types.SymbolKind.Variable
                            symbols.append(self._make_symbol(
                                name=name_node.text.decode("utf-8"),
                                kind=kind,
                                node=decl,
                                name_node=name_node,
                            ))

            elif child.type in ("program", "class_body"):
                symbols.extend(self._extract_symbols(child, inside_class))

        return symbols

    def _get_func_def_name(self, node) -> str | None:
        """JS: дополнительно обрабатываем стрелочные функции (const foo = () => {})."""
        result = super()._get_func_def_name(node)
        if result:
            return result
        if node.type == "variable_declarator":
            value = node.child_by_field_name("value")
            if value and value.type in ("arrow_function", "function_expression"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode("utf-8")
        return None
