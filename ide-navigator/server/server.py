import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

from pygls.lsp.server import LanguageServer
from lsprotocol import types

# Windows: stderr по умолчанию использует консольную кодировку (cp1251 для RU),
# а VS Code читает LSP-канал как UTF-8 → кириллица превращается в ��.
# reconfigure должен идти ДО basicConfig, чтобы StreamHandler подхватил новый поток.
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from languages.base import BaseLanguage
from languages.python_lang import PythonLanguage
from languages.java_lang import JavaLanguage
from languages.cpp_lang import CppLanguage
from languages.go_lang import GoLanguage
from languages.javascript_lang import JavaScriptLanguage
from languages.typescript_lang import TypeScriptLanguage

try:
    from languages.swift_lang import SwiftLanguage
    _swift_available = True
except ModuleNotFoundError:
    _swift_available = False
    logger.warning("tree_sitter_swift не установлен — Swift не поддерживается")

server = LanguageServer("ide-navigator", "v0.1")

# ── Реестр языков: расширение файла → языковой модуль ─────────────────────
LANGUAGE_MAP = {
    ".py":    PythonLanguage(),
    ".java":  JavaLanguage(),
    ".cpp":   CppLanguage(),
    ".cc":    CppLanguage(),
    ".cxx":   CppLanguage(),
    ".h":     CppLanguage(),
    ".hpp":   CppLanguage(),
    ".go":    GoLanguage(),
    ".js":    JavaScriptLanguage(),
    ".ts":    TypeScriptLanguage(),
    ".tsx":   TypeScriptLanguage(),
    **({".swift": SwiftLanguage()} if _swift_available else {}),
}


def get_language(uri: str):
    """Определить язык по URI файла."""
    path = urlparse(uri).path
    ext = os.path.splitext(path)[1].lower()
    return LANGUAGE_MAP.get(ext)


# ── Обработчики LSP ────────────────────────────────────────────────────────

_LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def _apply_settings(opts: dict) -> None:
    """Применить настройки из initializationOptions клиента."""
    if not isinstance(opts, dict):
        return

    log_level = opts.get("logLevel")
    if isinstance(log_level, str) and log_level in _LOG_LEVELS:
        level = _LOG_LEVELS[log_level]
        root = logging.getLogger()
        root.setLevel(level)
        for h in root.handlers:
            h.setLevel(level)
        logger.info(f"Log level set to {log_level}")

    cache_size = opts.get("cacheSize")
    if isinstance(cache_size, int) and 1 <= cache_size <= 256:
        BaseLanguage._PARSE_CACHE_MAX = cache_size
        logger.info(f"Parse cache size set to {cache_size}")


@server.feature(types.INITIALIZE)
def on_initialize(ls: LanguageServer, params: types.InitializeParams):
    """Читаем initializationOptions напрямую из initialize-запроса.

    pygls 2.x даёт встроиться в свой lsp_initialize через user_handler:
    наши настройки успевают примениться до того, как сервер начнёт
    отвечать на textDocument/*-запросы.
    """
    opts = params.initialization_options
    if isinstance(opts, dict):
        _apply_settings(opts)


@server.feature(types.INITIALIZED)
def initialized(ls: LanguageServer, params: types.InitializedParams):
    logger.info("IDE Navigator server ready")


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: types.DidOpenTextDocumentParams):
    # Сейчас только логируем. В будущем — триггер для индексации файла
    # (нужно для Go to Definition и Find References через project indexer)
    logger.info(f"Открыт: {params.text_document.uri}")


@server.feature(types.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(
    ls: LanguageServer,
    params: types.DocumentSymbolParams,
) -> list[types.DocumentSymbol]:
    """Document Outline — структура файла в боковой панели VS Code."""
    uri = params.text_document.uri
    lang = get_language(uri)

    if lang is None:
        logger.info(f"Язык не поддерживается: {uri}")
        return []

    try:
        doc = ls.workspace.get_text_document(uri)
        symbols = lang.get_symbols(doc.source, uri)
    except Exception as e:
        logger.exception(f"Outline: failed on {uri}: {e}")
        return []

    logger.info(f"Outline: найдено {len(symbols)} символов в {uri}")
    return symbols


@server.feature(types.TEXT_DOCUMENT_DEFINITION)
def definition(
    ls: LanguageServer,
    params: types.DefinitionParams,
) -> types.Location | None:
    """Go to Definition — Ctrl+Click прыжок к определению символа."""
    uri = params.text_document.uri
    lang = get_language(uri)

    if lang is None:
        return None

    try:
        doc = ls.workspace.get_text_document(uri)
        result = lang.find_definition(doc.source, params.position.line, params.position.character, uri)
    except Exception as e:
        logger.exception(f"Definition: failed on {uri}: {e}")
        return None

    if result:
        logger.info(f"Definition: найдено в {uri}:{result.start.line + 1}")
        return types.Location(uri=uri, range=result)

    # Cross-file: ищем определение через import-tracking
    try:
        doc = ls.workspace.get_text_document(uri)
        cross = lang.find_cross_file_definition(
            doc.source, params.position.line, params.position.character,
            uri, LANGUAGE_MAP,
        )
        if cross:
            logger.info(f"Definition: cross-file → {cross.uri}:{cross.range.start.line + 1}")
            return cross
    except Exception as e:
        logger.exception(f"Definition: cross-file failed on {uri}: {e}")

    logger.info(f"Definition: не найдено для позиции {params.position.line}:{params.position.character}")
    return None


@server.feature(types.TEXT_DOCUMENT_REFERENCES)
def references(
    ls: LanguageServer,
    params: types.ReferenceParams,
) -> list[types.Location]:
    """Find All References — все вхождения символа в файле."""
    uri = params.text_document.uri
    lang = get_language(uri)

    if lang is None:
        return []

    try:
        doc = ls.workspace.get_text_document(uri)
        include_decl = params.context.include_declaration
        ranges = lang.find_references(
            doc.source, params.position.line, params.position.character, include_decl, uri,
        )
    except Exception as e:
        logger.exception(f"References: failed on {uri}: {e}")
        return []

    logger.info(f"References: найдено {len(ranges)} в {uri}")
    return [types.Location(uri=uri, range=r) for r in ranges]


@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(
    ls: LanguageServer,
    params: types.HoverParams,
) -> types.Hover | None:
    """Hover Info — информация о символе при наведении курсора."""
    uri = params.text_document.uri
    lang = get_language(uri)

    if lang is None:
        return None

    try:
        doc = ls.workspace.get_text_document(uri)
        result = lang.get_hover(doc.source, params.position.line, params.position.character, uri)
    except Exception as e:
        logger.exception(f"Hover: failed on {uri}: {e}")
        return None

    if result:
        logger.info(f"Hover: {uri}:{params.position.line + 1}")
    return result


# ── CodeLens (reference counts) ──────────────────────────────────────────

@server.feature(types.TEXT_DOCUMENT_CODE_LENS)
def code_lens(
    ls: LanguageServer,
    params: types.CodeLensParams,
) -> list[types.CodeLens]:
    """CodeLens — показать количество ссылок над каждой функцией/классом."""
    uri = params.text_document.uri
    lang = get_language(uri)

    if lang is None:
        return []

    try:
        doc = ls.workspace.get_text_document(uri)
        source = doc.source
        symbols = lang.get_symbols(source, uri)
    except Exception as e:
        logger.exception(f"CodeLens: failed on {uri}: {e}")
        return []

    lenses: list[types.CodeLens] = []
    _collect_code_lenses(lang, source, symbols, uri, lenses)
    logger.info(f"CodeLens: {len(lenses)} lenses in {uri}")
    return lenses


def _collect_code_lenses(
    lang: BaseLanguage,
    source: str,
    symbols: list[types.DocumentSymbol],
    uri: str,
    result: list[types.CodeLens],
) -> None:
    """Рекурсивно собрать CodeLens для каждого символа."""
    for s in symbols:
        # Считаем ссылки на этот символ (без объявления)
        refs = lang.find_references(
            source,
            s.selection_range.start.line,
            s.selection_range.start.character,
            include_declaration=False,
        )
        count = len(refs)
        title = f"{count} reference{'s' if count != 1 else ''}"

        result.append(types.CodeLens(
            range=s.selection_range,
            command=types.Command(
                title=title,
                command="ide-navigator.showReferences",
            ),
        ))

        if s.children:
            _collect_code_lenses(lang, source, s.children, uri, result)


# ── Workspace Symbols ─────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = set(LANGUAGE_MAP.keys())


def _flatten_symbols(
    symbols: list[types.DocumentSymbol], uri: str, container: str = "",
) -> list[types.SymbolInformation]:
    """Превратить дерево DocumentSymbol в плоский список SymbolInformation."""
    result = []
    for s in symbols:
        result.append(types.SymbolInformation(
            name=s.name,
            kind=s.kind,
            location=types.Location(uri=uri, range=s.selection_range),
            container_name=container or None,
        ))
        if s.children:
            result.extend(_flatten_symbols(s.children, uri, container=s.name))
    return result


def _scan_workspace_files(folders) -> list[Path]:
    """Найти все файлы с поддерживаемыми расширениями в workspace."""
    files = []
    # pygls 2.x: folders — dict {uri_string: WorkspaceFolder}
    uris = folders.keys() if isinstance(folders, dict) else [f.uri for f in folders]
    for folder_uri in uris:
        folder_path = unquote(urlparse(folder_uri).path)
        # На Windows путь может начинаться с /C:/... — убираем лишний /
        if os.name == "nt" and folder_path.startswith("/"):
            folder_path = folder_path[1:]
        root = Path(folder_path)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                # Пропускаем venv, node_modules и скрытые папки
                parts = path.relative_to(root).parts
                if any(p.startswith(".") or p in ("venv", "node_modules", "__pycache__") for p in parts):
                    continue
                files.append(path)
    return files


@server.feature(types.WORKSPACE_SYMBOL)
def workspace_symbol(
    ls: LanguageServer,
    params: types.WorkspaceSymbolParams,
) -> list[types.SymbolInformation]:
    """Workspace Symbols — Ctrl+T поиск символа по всем файлам проекта."""
    query = params.query.lower()
    all_symbols: list[types.SymbolInformation] = []

    folders = ls.workspace.folders
    if not folders:
        return []

    for path in _scan_workspace_files(folders):
        ext = path.suffix.lower()
        lang = LANGUAGE_MAP.get(ext)
        if lang is None:
            continue

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        try:
            symbols = lang.get_symbols(source)
        except Exception as e:
            logger.warning(f"Workspace symbols: skip {path}: {e}")
            continue

        uri = path.as_uri()
        all_symbols.extend(_flatten_symbols(symbols, uri))

    # Фильтруем по запросу (пустой запрос = все символы)
    if query:
        all_symbols = [s for s in all_symbols if query in s.name.lower()]

    logger.info(f"Workspace symbols: {len(all_symbols)} matches for '{params.query}'")
    return all_symbols


# ── Валидация аргументов кастомных команд ────────────────────────────

def _unwrap_args(args: tuple) -> list:
    """
    pygls 2.x может прислать команду как позиционные *args или как один
    список в args[0]. Нормализуем к плоскому списку.
    """
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        return list(args[0])
    return list(args)


def _validate_position_args(args: tuple) -> tuple[str, int, int, bool] | None:
    """
    Проверить что args = (uri: str, line: int, character: int, [include_decl: bool]).
    Возвращает нормализованный кортеж или None при любой ошибке.
    """
    flat = _unwrap_args(args)
    if len(flat) < 3:
        return None
    uri, line, character = flat[0], flat[1], flat[2]
    if not isinstance(uri, str) or not isinstance(line, int) or not isinstance(character, int):
        return None
    if line < 0 or character < 0:
        return None
    include_decl = flat[3] if len(flat) > 3 else True
    if not isinstance(include_decl, bool):
        include_decl = bool(include_decl)
    return uri, line, character, include_decl


def _validate_uri_arg(args: tuple) -> str | None:
    """Проверить что первый аргумент — непустая строка (URI)."""
    flat = _unwrap_args(args)
    if not flat:
        return None
    uri = flat[0]
    if not isinstance(uri, str) or not uri:
        return None
    return uri


# ── References panel (custom command) ────────────────────────────────

@server.command("ide-navigator.references")
def references_command(ls: LanguageServer, *args):
    """Вернуть референсы + сниппеты для кастомной WebView-панели."""
    logger.info(f"References command, args={args}")

    validated = _validate_position_args(args)
    if validated is None:
        logger.warning(f"References: invalid args {args}")
        return None
    uri, line, character, include_decl = validated

    lang = get_language(uri)
    if lang is None:
        return None

    try:
        doc = ls.workspace.get_text_document(uri)
        result = lang.get_references_with_context(doc.source, line, character, include_decl, uri)
    except Exception as e:
        logger.exception(f"References: failed on {uri}: {e}")
        return None

    if result:
        result["uri"] = uri
        logger.info(f"References panel: {len(result['refs'])} in {uri}")
    return result


# ── Call Graph (custom command) ───────────────────────────────────────

@server.command("ide-navigator.callGraph")
def call_graph_command(ls: LanguageServer, *args):
    """Вернуть граф вызовов для файла."""
    logger.info(f"Call graph command, args={args}")
    empty = {"nodes": [], "edges": []}

    uri = _validate_uri_arg(args)
    if uri is None:
        logger.warning(f"Call graph: invalid args {args}")
        return empty

    lang = get_language(uri)
    if lang is None:
        return empty

    try:
        doc = ls.workspace.get_text_document(uri)
        result = lang.get_call_graph(doc.source, uri)
    except Exception as e:
        logger.exception(f"Call graph: failed on {uri}: {e}")
        return empty

    logger.info(f"Call graph: {len(result['nodes'])} nodes, {len(result['edges'])} edges in {uri}")
    return result


if __name__ == "__main__":
    server.start_io()
