import logging
from pygls.lsp.server import LanguageServer
from lsprotocol import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = LanguageServer("ide-navigator", "v0.1")


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: types.DidOpenTextDocumentParams):
    logger.info(f"IDE Navigator: открыт {params.text_document.uri}")


if __name__ == "__main__":
    server.start_io()
