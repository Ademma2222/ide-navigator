"""
LRU-кэш разобранных деревьев tree-sitter + incremental parsing.
Выделено из BaseLanguage в отдельный миксин: ответственность одна — парсинг
и его кэширование. Все остальные миксины вызывают self._parse().
"""
import logging
import time
from collections import OrderedDict
from lsprotocol import types

logger = logging.getLogger(__name__)


class ParseCacheMixin:
    # Максимальное количество разобранных AST-деревьев в кэше.
    # Outline/Definition/References/Hover на одном файле парсят AST четырежды —
    # кэш даёт 4x ускорение без заметного расхода памяти.
    _PARSE_CACHE_MAX = 32

    # Идентификатор языка для подсветки синтаксиса в Markdown-код-блоках.
    # Переопределяется в каждом языковом наследнике.
    LANGUAGE_ID: str = "text"

    def __init__(self) -> None:
        # OrderedDict как простой LRU: ключ — сам source, значение — Tree.
        # Кэш привязан к экземпляру класса (в LANGUAGE_MAP они — синглтоны).
        self._parse_cache: OrderedDict[str, object] = OrderedDict()

        # Per-URI кэш последнего дерева для incremental parsing.
        # При cache miss передаём old_tree в parser.parse() — tree-sitter
        # переиспользует неизменившиеся узлы и парсит быстрее.
        self._uri_tree_cache: OrderedDict[str, object] = OrderedDict()

    def _parse(self, source: str, uri: str | None = None):
        """
        Разобрать исходник через tree-sitter с LRU-кэшем.
        Все методы класса (get_symbols, find_definition и т.д.) должны
        использовать этот метод вместо `self.get_parser().parse(...)`.

        uri — опциональный URI файла. Если указан, используется для
        incremental parsing: при cache miss берём old_tree из предыдущей
        версии этого файла и передаём в parser.parse() как hint.
        """
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
        """Конвертировать позицию tree-sitter → LSP Range."""
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
