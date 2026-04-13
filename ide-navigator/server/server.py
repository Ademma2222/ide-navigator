import logging
import os
from pathlib import Path
from urllib.parse import urlparse, unquote

from pygls.lsp.server import LanguageServer
from lsprotocol import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    doc = ls.workspace.get_text_document(uri)
    symbols = lang.get_symbols(doc.source)
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

    doc = ls.workspace.get_text_document(uri)
    result = lang.find_definition(doc.source, params.position.line, params.position.character)

    if result:
        logger.info(f"Definition: найдено в {uri}:{result.start.line + 1}")
        return types.Location(uri=uri, range=result)

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

    doc = ls.workspace.get_text_document(uri)
    include_decl = params.context.include_declaration
    ranges = lang.find_references(
        doc.source, params.position.line, params.position.character, include_decl,
    )

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

    doc = ls.workspace.get_text_document(uri)
    result = lang.get_hover(doc.source, params.position.line, params.position.character)

    if result:
        logger.info(f"Hover: {uri}:{params.position.line + 1}")
    return result


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

        symbols = lang.get_symbols(source)
        uri = path.as_uri()
        all_symbols.extend(_flatten_symbols(symbols, uri))

    # Фильтруем по запросу (пустой запрос = все символы)
    if query:
        all_symbols = [s for s in all_symbols if query in s.name.lower()]

    logger.info(f"Workspace symbols: {len(all_symbols)} matches for '{params.query}'")
    return all_symbols


# ── References panel (custom command) ────────────────────────────────

@server.command("ide-navigator.references")
def references_command(ls: LanguageServer, *args):
    """Вернуть референсы + сниппеты для кастомной WebView-панели."""
    logger.info(f"References command, args={args}")
    if len(args) < 3:
        return None

    uri, line, character = args[0], args[1], args[2]
    include_decl = args[3] if len(args) > 3 else True

    lang = get_language(uri)
    if lang is None:
        return None

    doc = ls.workspace.get_text_document(uri)
    result = lang.get_references_with_context(doc.source, line, character, include_decl)

    if result:
        result["uri"] = uri
        logger.info(f"References panel: {len(result['refs'])} in {uri}")
    return result


# ── Call Graph (custom command) ───────────────────────────────────────

@server.command("ide-navigator.callGraph")
def call_graph_command(ls: LanguageServer, *args):
    """Вернуть граф вызовов для файла."""
    logger.info(f"Call graph command, args={args}")
    if not args:
        return {"nodes": [], "edges": []}

    uri = args[0]
    lang = get_language(uri)
    if lang is None:
        return {"nodes": [], "edges": []}

    doc = ls.workspace.get_text_document(uri)
    result = lang.get_call_graph(doc.source)
    logger.info(f"Call graph: {len(result['nodes'])} nodes, {len(result['edges'])} edges in {uri}")
    return result


if __name__ == "__main__":
    server.start_io()
