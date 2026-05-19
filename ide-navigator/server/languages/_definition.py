import logging
import os
from pathlib import Path
from urllib.parse import urlparse, unquote
from lsprotocol import types

logger = logging.getLogger(__name__)

class DefinitionMixin:
    def find_definition(self, source: str, line: int, character: int, uri: str | None = None) -> types.Range | None:
        tree = self._parse(source, uri)

        node = tree.root_node.descendant_for_point_range(
            (line, character), (line, character)
        )
        if node is None or "identifier" not in node.type:
            return None

        name = node.text.decode("utf-8")

        symbols = self._extract_symbols(tree.root_node)
        found = self._find_symbol_by_name(symbols, name)
        if found:
            return found.selection_range
        return None

    def find_cross_file_definition(
        self, source: str, line: int, character: int, uri: str,
        language_map: dict,
        workspace_roots: list[Path] | None = None,
    ) -> types.Location | None:
        tree = self._parse(source, uri)
        node = tree.root_node.descendant_for_point_range(
            (line, character), (line, character)
        )
        if node is None or "identifier" not in node.type:
            return None

        name = node.text.decode("utf-8")

        imports = self._extract_imports(tree.root_node, uri)
        if name not in imports:
            return None

        target_path, original_name = imports[name]
        if target_path is None or not target_path.exists():
            return None

        if not self._is_path_within_workspace(target_path, workspace_roots):
            logger.debug("cross-file reject %s: outside workspace", target_path)
            return None

        ext = target_path.suffix.lower()
        target_lang = language_map.get(ext)
        if target_lang is None:
            return None

        try:
            target_source = target_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        target_uri = target_path.as_uri()
        symbols = target_lang.get_symbols(target_source, target_uri)
        found = self._find_symbol_by_name(symbols, original_name)
        if found:
            return types.Location(uri=target_uri, range=found.selection_range)
        return None

    @staticmethod
    def _is_path_within_workspace(
        target: Path, workspace_roots: list[Path] | None,
    ) -> bool:
        if not workspace_roots:
            return True
        try:
            resolved = target.resolve()
        except OSError:
            return False
        for root in workspace_roots:
            try:
                resolved.relative_to(root.resolve())
                return True
            except ValueError:
                continue
        return False

    def _extract_imports(self, root_node, uri: str) -> dict[str, tuple[Path | None, str]]:
        return {}

    @staticmethod
    def _uri_to_path(uri: str) -> Path:
        parsed = urlparse(uri).path
        path = unquote(parsed)
        if os.name == "nt" and path.startswith("/"):
            path = path[1:]
        return Path(path)

    def _find_symbol_by_name(
        self, symbols: list[types.DocumentSymbol], name: str,
    ) -> types.DocumentSymbol | None:
        for s in symbols:
            if s.name == name:
                return s
            if s.children:
                found = self._find_symbol_by_name(s.children, name)
                if found:
                    return found
        return None

    def _find_symbol_fqn(
        self, symbols: list[types.DocumentSymbol], name: str, prefix: str = "",
    ) -> str | None:
        for s in symbols:
            fqn = f"{prefix}.{s.name}" if prefix else s.name
            if s.name == name:
                return fqn
            if s.children:
                found = self._find_symbol_fqn(s.children, name, fqn)
                if found:
                    return found
        return None
