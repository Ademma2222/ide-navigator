import logging
import time
from collections import OrderedDict
from lsprotocol import types

logger = logging.getLogger(__name__)

class ParseCacheMixin:
    _PARSE_CACHE_MAX = 32

    LANGUAGE_ID: str = "text"

    def __init__(self) -> None:
        self._parse_cache: OrderedDict[str, object] = OrderedDict()

        self._uri_tree_cache: OrderedDict[str, object] = OrderedDict()

    def _parse(self, source: str, uri: str | None = None):
        cached = self._parse_cache.get(source)
        if cached is not None:
            self._parse_cache.move_to_end(source)
            return cached

        old_tree = self._uri_tree_cache.get(uri) if uri else None

        start = time.perf_counter()
        source_bytes = bytes(source, "utf-8")
        if old_tree is not None:
            tree = self.get_parser().parse(source_bytes, old_tree=old_tree)
        else:
            tree = self.get_parser().parse(source_bytes)
        elapsed_ms = (time.perf_counter() - start) * 1000

        mode = "incremental" if old_tree else "full"
        logger.info(
            f"parse[{self.LANGUAGE_ID}]: {len(source)} bytes in {elapsed_ms:.1f}ms ({mode})"
        )

        self._parse_cache[source] = tree
        if len(self._parse_cache) > self._PARSE_CACHE_MAX:
            self._parse_cache.popitem(last=False)

        if uri:
            self._uri_tree_cache[uri] = tree
            if len(self._uri_tree_cache) > self._PARSE_CACHE_MAX:
                self._uri_tree_cache.popitem(last=False)

        return tree

    def _to_range(self, node) -> types.Range:
        return types.Range(
            start=types.Position(
                line=node.start_point[0],
                character=node.start_point[1],
            ),
            end=types.Position(
                line=node.end_point[0],
                character=node.end_point[1],
            ),
        )
