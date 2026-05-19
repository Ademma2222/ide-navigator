from languages.python_lang import PythonLanguage

def test_parse_cache_returns_same_tree():
    lang = PythonLanguage()
    src = "def foo(): pass\n"
    tree1 = lang._parse(src)
    tree2 = lang._parse(src)
    assert tree1 is tree2

def test_parse_cache_different_sources():
    lang = PythonLanguage()
    src_a = "def a(): pass\n"
    src_b = "def b(): pass\n"
    tree_a = lang._parse(src_a)
    tree_b = lang._parse(src_b)
    assert tree_a is not tree_b

def test_parse_cache_lru_eviction():
    lang = PythonLanguage()
    lang._parse_cache.clear()

    sources = [f"x_{i} = {i}\n" for i in range(lang._PARSE_CACHE_MAX + 1)]
    for s in sources:
        lang._parse(s)

    assert len(lang._parse_cache) == lang._PARSE_CACHE_MAX
    assert sources[0] not in lang._parse_cache
    assert sources[-1] in lang._parse_cache

def test_get_symbols_uses_cache():
    lang = PythonLanguage()
    lang._parse_cache.clear()

    src = "def foo():\n    return 1\n\ndef bar():\n    return foo()\n"
    lang.get_symbols(src)
    lang.find_definition(src, 4, 12)
    lang.find_references(src, 0, 4, include_declaration=True)
    lang.get_hover(src, 0, 4)

    assert len(lang._parse_cache) == 1
