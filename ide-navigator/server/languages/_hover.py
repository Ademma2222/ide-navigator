from lsprotocol import types

class HoverMixin:
    _KIND_LABELS = {
        types.SymbolKind.Function: "function",
        types.SymbolKind.Method: "method",
        types.SymbolKind.Class: "class",
        types.SymbolKind.Interface: "interface",
        types.SymbolKind.Struct: "struct",
        types.SymbolKind.Namespace: "namespace",
        types.SymbolKind.Constructor: "constructor",
        types.SymbolKind.Variable: "variable",
        types.SymbolKind.Constant: "constant",
        types.SymbolKind.Enum: "enum",
        types.SymbolKind.TypeParameter: "type alias",
    }

    def get_hover(self, source: str, line: int, character: int, uri: str | None = None) -> types.Hover | None:
        tree = self._parse(source, uri)

        node = tree.root_node.descendant_for_point_range(
            (line, character), (line, character)
        )
        if node is None or "identifier" not in node.type:
            return None

        name = node.text.decode("utf-8")

        symbols = self._extract_symbols(tree.root_node)
        found = self._find_symbol_by_name(symbols, name)
        if not found:
            return None

        kind_label = self._KIND_LABELS.get(found.kind, "symbol")
        decl_line = found.range.start.line

        lines = source.splitlines()
        signature = lines[decl_line].strip() if decl_line < len(lines) else name

        complexity_str = ""
        if found.kind in (types.SymbolKind.Function, types.SymbolKind.Method,
                          types.SymbolKind.Constructor):
            func_node = self._find_func_node_at(
                tree.root_node,
                found.selection_range.start.line,
                found.selection_range.start.character,
            )
            if func_node is not None:
                cc = self._compute_complexity(func_node)
                complexity_str = f" · complexity {cc}"

        md = (
            f"```{self.LANGUAGE_ID}\n"
            f"{signature}\n"
            f"```\n"
            f"---\n"
            f"**{kind_label}** — line {decl_line + 1}{complexity_str}"
        )

        return types.Hover(
            contents=types.MarkupContent(
                kind=types.MarkupKind.Markdown,
                value=md,
            ),
            range=self._to_range(node),
        )
