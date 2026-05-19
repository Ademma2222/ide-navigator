import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

from pygls.lsp.server import LanguageServer
from lsprotocol import types

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

server = LanguageServer("ide-navigator", "v0.1")

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
}

def get_language(uri: str):
    path = urlparse(uri).path
    ext = os.path.splitext(path)[1].lower()
    return LANGUAGE_MAP.get(ext)

def _folder_uri_to_path(folder_uri: str) -> Path:
    folder_path = unquote(urlparse(folder_uri).path)
    if os.name == "nt" and folder_path.startswith("/"):
        folder_path = folder_path[1:]
    return Path(folder_path)

def _iter_folder_uris(folders) -> list[str]:
    if not folders:
        return []
    return list(folders.keys()) if isinstance(folders, dict) else [f.uri for f in folders]

def _get_workspace_roots(ls: LanguageServer) -> list[Path]:
    roots: list[Path] = []
    for folder_uri in _iter_folder_uris(ls.workspace.folders):
        root = _folder_uri_to_path(folder_uri)
        if root.exists():
            roots.append(root)
    return roots

_LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

def _apply_settings(opts: dict) -> None:
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
    opts = params.initialization_options
    if isinstance(opts, dict):
        _apply_settings(opts)

@server.feature(types.INITIALIZED)
def initialized(ls: LanguageServer, params: types.InitializedParams):
    logger.info("IDE Navigator server ready")

@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: types.DidOpenTextDocumentParams):
    logger.debug(f"Открыт: {params.text_document.uri}")

@server.feature(types.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(
    ls: LanguageServer,
    params: types.DocumentSymbolParams,
) -> list[types.DocumentSymbol]:
    uri = params.text_document.uri
    lang = get_language(uri)

    if lang is None:
        logger.debug(f"Язык не поддерживается: {uri}")
        return []

    try:
        doc = ls.workspace.get_text_document(uri)
        symbols = lang.get_symbols(doc.source, uri)
    except Exception as e:
        logger.exception(f"Outline: failed on {uri}: {e}")
        return []

    logger.debug(f"Outline: найдено {len(symbols)} символов в {uri}")
    return symbols

@server.feature(types.TEXT_DOCUMENT_DEFINITION)
def definition(
    ls: LanguageServer,
    params: types.DefinitionParams,
) -> types.Location | None:
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
        logger.debug(f"Definition: найдено в {uri}:{result.start.line + 1}")
        return types.Location(uri=uri, range=result)

    try:
        doc = ls.workspace.get_text_document(uri)
        cross = lang.find_cross_file_definition(
            doc.source, params.position.line, params.position.character,
            uri, LANGUAGE_MAP,
            workspace_roots=_get_workspace_roots(ls),
        )
        if cross:
            logger.debug(f"Definition: cross-file → {cross.uri}:{cross.range.start.line + 1}")
            return cross
    except Exception as e:
        logger.exception(f"Definition: cross-file failed on {uri}: {e}")

    logger.debug(f"Definition: не найдено для позиции {params.position.line}:{params.position.character}")
    return None

@server.feature(types.TEXT_DOCUMENT_REFERENCES)
def references(
    ls: LanguageServer,
    params: types.ReferenceParams,
) -> list[types.Location]:
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

    logger.debug(f"References: найдено {len(ranges)} в {uri}")
    return [types.Location(uri=uri, range=r) for r in ranges]

@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(
    ls: LanguageServer,
    params: types.HoverParams,
) -> types.Hover | None:
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
        logger.debug(f"Hover: {uri}:{params.position.line + 1}")
    return result

@server.feature(types.TEXT_DOCUMENT_CODE_LENS)
def code_lens(
    ls: LanguageServer,
    params: types.CodeLensParams,
) -> list[types.CodeLens]:
    uri = params.text_document.uri
    lang = get_language(uri)

    if lang is None:
        return []

    try:
        doc = ls.workspace.get_text_document(uri)
        source = doc.source
        symbols = lang.get_symbols(source, uri)
        ident_counts = lang.count_identifiers_by_name(source, uri)
    except Exception as e:
        logger.exception(f"CodeLens: failed on {uri}: {e}")
        return []

    lenses: list[types.CodeLens] = []
    _collect_code_lenses(symbols, ident_counts, uri, lenses)
    logger.debug(f"CodeLens: {len(lenses)} lenses in {uri}")
    return lenses

def _collect_code_lenses(
    symbols: list[types.DocumentSymbol],
    ident_counts: dict[str, int],
    uri: str,
    result: list[types.CodeLens],
) -> None:
    for s in symbols:
        line = s.selection_range.start.line
        character = s.selection_range.start.character
        total = ident_counts.get(s.name, 0)
        count = max(0, total - 1)
        title = f"{count} reference{'s' if count != 1 else ''}"

        result.append(types.CodeLens(
            range=s.selection_range,
            command=types.Command(
                title=title,
                command="ide-navigator.showReferences",
                arguments=[uri, line, character],
            ),
        ))

        if s.children:
            _collect_code_lenses(s.children, ident_counts, uri, result)

SUPPORTED_EXTENSIONS = set(LANGUAGE_MAP.keys())

def _flatten_symbols(
    symbols: list[types.DocumentSymbol], uri: str, container: str = "",
) -> list[types.SymbolInformation]:
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
    files = []
    for folder_uri in _iter_folder_uris(folders):
        root = _folder_uri_to_path(folder_uri)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
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

    if query:
        all_symbols = [s for s in all_symbols if query in s.name.lower()]

    logger.info(f"Workspace symbols: {len(all_symbols)} matches for '{params.query}'")
    return all_symbols

def _unwrap_args(args: tuple) -> list:
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        return list(args[0])
    return list(args)

def _validate_position_args(args: tuple) -> tuple[str, int, int, bool] | None:
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
    flat = _unwrap_args(args)
    if not flat:
        return None
    uri = flat[0]
    if not isinstance(uri, str) or not uri:
        return None
    return uri

@server.command("ide-navigator.references")
def references_command(ls: LanguageServer, *args):
    logger.debug(f"References command, args={args}")

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
        logger.debug(f"References panel: {len(result['refs'])} in {uri}")
    return result

@server.command("ide-navigator.callGraph")
def call_graph_command(ls: LanguageServer, *args):
    logger.debug(f"Call graph command, args={args}")
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

    logger.debug(f"Call graph: {len(result['nodes'])} nodes, {len(result['edges'])} edges in {uri}")
    return result

if __name__ == "__main__":
    server.start_io()
