from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_python as tspython
from lsprotocol import types
from .base import BaseLanguage

class PythonLanguage(BaseLanguage):

    LANGUAGE_ID = "python"

    def get_parser(self) -> Parser:
        return Parser(Language(tspython.language()))

    def _extract_imports(self, root_node, uri: str) -> dict[str, tuple[Path | None, str]]:
        current_path = self._uri_to_path(uri)
        current_dir = current_path.parent
        result: dict[str, tuple[Path | None, str]] = {}

        for child in root_node.children:
            if child.type == "import_statement":
                for name_node in child.children:
                    if name_node.type == "dotted_name":
                        module_name = name_node.text.decode("utf-8")
                        parts = module_name.split(".")
                        resolved = self._resolve_python_module(current_dir, parts)
                        local_name = parts[-1]
                        result[local_name] = (resolved, local_name)
                    elif name_node.type == "aliased_import":
                        name_child = name_node.child_by_field_name("name")
                        alias_child = name_node.child_by_field_name("alias")
                        if name_child and alias_child:
                            module_name = name_child.text.decode("utf-8")
                            parts = module_name.split(".")
                            resolved = self._resolve_python_module(current_dir, parts)
                            local = alias_child.text.decode("utf-8")
                            result[local] = (resolved, parts[-1])

            elif child.type == "import_from_statement":
                module_node = child.child_by_field_name("module_name")
                module_text = module_node.text.decode("utf-8") if module_node else ""

                dots = 0
                for c in child.children:
                    if c.type == "." or (c.type == "import_prefix" and c.text):
                        text = c.text.decode("utf-8") if isinstance(c.text, bytes) else c.text
                        dots += text.count(".")

                if dots > 0:
                    base = current_dir
                    for _ in range(dots - 1):
                        base = base.parent
                    if module_text:
                        parts = module_text.split(".")
                        resolved = self._resolve_python_module(base, parts)
                    else:
                        resolved = self._resolve_python_module(base, [])
                else:
                    parts = module_text.split(".") if module_text else []
                    resolved = self._resolve_python_module(current_dir, parts)

                for c in child.children:
                    if c.type == "dotted_name" and c != module_node:
                        name = c.text.decode("utf-8")
                        result[name] = (resolved, name)
                    elif c.type == "aliased_import":
                        name_child = c.child_by_field_name("name")
                        alias_child = c.child_by_field_name("alias")
                        if name_child:
                            orig = name_child.text.decode("utf-8")
                            local = alias_child.text.decode("utf-8") if alias_child else orig
                            result[local] = (resolved, orig)

        return result

    @staticmethod
    def _resolve_python_module(base_dir: Path, parts: list[str]) -> Path | None:
        if not parts:
            init = base_dir / "__init__.py"
            return init if init.exists() else None

        file_path = base_dir / "/".join(parts[:-1]) / (parts[-1] + ".py") if len(parts) > 1 else base_dir / (parts[0] + ".py")
        if file_path.exists():
            return file_path

        pkg_path = base_dir / "/".join(parts) / "__init__.py"
        if pkg_path.exists():
            return pkg_path

        return None

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

            elif child.type == "expression_statement" and not inside_class:
                assign = next((c for c in child.children if c.type == "assignment"), None)
                if assign:
                    left = assign.child_by_field_name("left")
                    if left and left.type == "identifier":
                        symbols.append(self._make_symbol(
                            name=left.text.decode("utf-8"),
                            kind=types.SymbolKind.Variable,
                            node=assign,
                            name_node=left,
                        ))

            elif child.type in ("module", "block", "decorated_definition"):
                symbols.extend(self._extract_symbols(child, inside_class))

        return symbols
