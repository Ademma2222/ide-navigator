import os
import tempfile
from pathlib import Path

from languages._parse_cache import ParseCacheMixin
from languages._definition import DefinitionMixin
from languages._references import ReferencesMixin
from languages._hover import HoverMixin
from languages._call_graph import CallGraphMixin
from languages.base import BaseLanguage
from languages.python_lang import PythonLanguage

def test_base_inherits_all_mixins():
    mro = BaseLanguage.__mro__
    for mixin in (ParseCacheMixin, DefinitionMixin, ReferencesMixin,
                  HoverMixin, CallGraphMixin):
        assert mixin in mro, f"{mixin.__name__} пропал из MRO BaseLanguage"

def test_parse_cache_max_override_via_base():
    original = BaseLanguage._PARSE_CACHE_MAX
    try:
        BaseLanguage._PARSE_CACHE_MAX = 7
        p = PythonLanguage()
        assert p._PARSE_CACHE_MAX == 7
    finally:
        BaseLanguage._PARSE_CACHE_MAX = original

def test_is_path_within_workspace_accepts_inside():
    with tempfile.TemporaryDirectory() as root:
        root_path = Path(root)
        target = root_path / "sub" / "file.py"
        target.parent.mkdir()
        target.write_text("x = 1")
        assert DefinitionMixin._is_path_within_workspace(target, [root_path])

def test_is_path_within_workspace_rejects_outside():
    with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as other:
        outside = Path(other) / "secret.py"
        outside.write_text("x = 1")
        assert not DefinitionMixin._is_path_within_workspace(outside, [Path(root)])

def test_is_path_within_workspace_rejects_traversal():
    with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as other:
        outside = Path(other) / "secret.py"
        outside.write_text("x = 1")
        root_path = Path(root)
        traversal = root_path / ".." / os.path.basename(other) / "secret.py"
        assert not DefinitionMixin._is_path_within_workspace(traversal, [root_path])

def test_is_path_within_workspace_empty_roots_allows():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "file.py"
        target.write_text("x = 1")
        assert DefinitionMixin._is_path_within_workspace(target, None)
        assert DefinitionMixin._is_path_within_workspace(target, [])
