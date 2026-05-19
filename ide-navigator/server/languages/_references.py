from lsprotocol import types

class ReferencesMixin:
    def find_references(
        self, source: str, line: int, character: int, include_declaration: bool = True,
        uri: str | None = None,
    ) -> list[types.Range]:
        tree = self._parse(source, uri)

        node = tree.root_node.descendant_for_point_range(
            (line, character), (line, character)
        )
        if node is None or "identifier" not in node.type:
            return []

        name = node.text.decode("utf-8")

        matches: list[types.Range] = []
        self._collect_identifiers(tree.root_node, name, matches)

        if not include_declaration:
            symbols = self._extract_symbols(tree.root_node)
            decl = self._find_symbol_by_name(symbols, name)
            if decl:
                matches = [r for r in matches if r != decl.selection_range]

        return matches

    def _collect_identifiers(
        self, node, name: str, result: list[types.Range],
    ) -> None:
        if "identifier" in node.type and node.text.decode("utf-8") == name:
            result.append(self._to_range(node))
        for child in node.children:
            self._collect_identifiers(child, name, result)

    def count_identifiers_by_name(self, source: str, uri: str | None = None) -> dict[str, int]:
        tree = self._parse(source, uri)
        counts: dict[str, int] = {}
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if "identifier" in node.type:
                name = node.text.decode("utf-8")
                counts[name] = counts.get(name, 0) + 1
            for child in node.children:
                stack.append(child)
        return counts

    def get_references_with_context(
        self, source: str, line: int, character: int, include_declaration: bool = True,
        uri: str | None = None,
    ) -> dict | None:
        tree = self._parse(source, uri)

        node = tree.root_node.descendant_for_point_range(
            (line, character), (line, character)
        )
        if node is None or "identifier" not in node.type:
            return None

        name = node.text.decode("utf-8")

        ranges = self.find_references(source, line, character, include_declaration)
        if not ranges:
            return None

        src_lines = source.splitlines()
        refs = []
        for r in ranges:
            line_idx = r.start.line
            snippet = src_lines[line_idx] if line_idx < len(src_lines) else ""
            refs.append({
                "line": line_idx,
                "character": r.start.character,
                "endCharacter": r.end.character,
                "snippet": snippet,
            })

        refs.sort(key=lambda item: (item["line"], item["character"]))

        return {
            "name": name,
            "language": self.LANGUAGE_ID,
            "refs": refs,
        }
