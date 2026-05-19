from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_javascript as tsjs
from lsprotocol import types
from .base import BaseLanguage

class JavaScriptLanguage(BaseLanguage):

    LANGUAGE_ID = "javascript"

    _JS_EXTENSIONS = [".js", ".ts", ".tsx", ".jsx"]

    def get_parser(self) -> Parser:
        return Parser(Language(tsjs.language()))

    def _extract_imports(self, root_node, uri: str) -> dict[str, tuple[Path | None, str]]:
        current_path = self._uri_to_path(uri)
        current_dir = current_path.parent
        result: dict[str, tuple[Path | None, str]] = {}

        for child in root_node.children:
            if child.type == "import_statement":
                source_node = child.child_by_field_name("source")
                if not source_node:
                    continue
                module_path = source_node.text.decode("utf-8").strip("'\"")
                resolved = self._resolve_js_module(current_dir, module_path)

                for c in child.children:
                    if c.type == "import_clause":
                        for ic in c.children:
                            if ic.type == "identifier":
                                name = ic.text.decode("utf-8")
                                result[name] = (resolved, name)
                            elif ic.type == "named_imports":
                                for spec in ic.children:
                                    if spec.type == "import_specifier":
                                        name_node = spec.child_by_field_name("name")
                                        alias_node = spec.child_by_field_name("alias")
                                        if name_node:
                                            orig = name_node.text.decode("utf-8")
                                            local = alias_node.text.decode("utf-8") if alias_node else orig
                                            result[local] = (resolved, orig)
                            elif ic.type == "namespace_import":
                                for ns in ic.children:
                                    if ns.type == "identifier":
                                        name = ns.text.decode("utf-8")
                                        result[name] = (resolved, name)

            elif child.type in ("lexical_declaration", "variable_declaration"):
                for decl in child.children:
                    if decl.type != "variable_declarator":
                        continue
                    name_node = decl.child_by_field_name("name")
                    value_node = decl.child_by_field_name("value")
                    if not name_node or not value_node:
                        continue
                    if value_node.type == "call_expression":
                        func = value_node.child_by_field_name("function")
                        if func and func.text == b"require":
                            args = value_node.child_by_field_name("arguments")
                            if args and args.child_count > 1:
                                arg = args.children[1]
                                if arg.type == "string":
                                    mod = arg.text.decode("utf-8").strip("'\"")
                                    resolved = self._resolve_js_module(current_dir, mod)
                                    name = name_node.text.decode("utf-8")
                                    result[name] = (resolved, name)

        return result

    def _resolve_js_module(self, base_dir: Path, module_path: str) -> Path | None:
        if not module_path.startswith("."):
            return None

        target = base_dir / module_path

        if target.is_file():
            return target

        for ext in self._JS_EXTENSIONS:
            candidate = target.with_suffix(ext)
            if candidate.is_file():
                return candidate

        if target.is_dir():
            for ext in self._JS_EXTENSIONS:
                idx = target / f"index{ext}"
                if idx.is_file():
                    return idx

        return None

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
