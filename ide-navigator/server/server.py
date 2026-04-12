import logging
import os
from urllib.parse import urlparse

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


if __name__ == "__main__":
    server.start_io()
