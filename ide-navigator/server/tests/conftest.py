"""
Pytest configuration: adds `server/` to sys.path so tests can import
`languages.python_lang` etc. without installing the server as a package.
"""
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parent.parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
