"""
Тестирует Document Outline для каждого языка без запуска LSP-сервера.
Запуск: python test_outline.py  (из папки server/)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from lsprotocol import types

# ── Образцы кода для каждого языка ────────────────────────────────────────

SAMPLES = {
    "Python": (
        "languages.python_lang", "PythonLanguage",
        """\
MY_CONST = 42

class Animal:
    def speak(self):
        pass
    def move(self):
        pass

def greet(name):
    return f"Hello {name}"
"""
    ),

    "Java": (
        "languages.java_lang", "JavaLanguage",
        """\
public class Calculator {
    public Calculator() {}
    public int add(int a, int b) { return a + b; }
    public int sub(int a, int b) { return a - b; }
}
interface Shape {
    double area();
}
"""
    ),

    "C++": (
        "languages.cpp_lang", "CppLanguage",
        """\
namespace utils {
    struct Point {
        float length() { return 0; }
    };
    class Vector {
        float dot() { return 0; }
    };
    void helper() {}
}
"""
    ),

    "Go": (
        "languages.go_lang", "GoLanguage",
        """\
package main

const MaxSize = 100
var Debug = false

type Animal struct {
    Name string
}

type Runner interface {
    Run()
}

func Greet() {}

func (a Animal) Speak() {}
"""
    ),

    "JavaScript": (
        "languages.javascript_lang", "JavaScriptLanguage",
        """\
class Dog {
    constructor() {}
    bark() {}
}

function greet() {}

const hello = () => {}
const arrow = (x) => x * 2

let count = 0
var name = "test"
"""
    ),

    "TypeScript": (
        "languages.typescript_lang", "TypeScriptLanguage",
        """\
interface Animal {
    name: string;
}

type ID = string | number;

enum Color { Red, Green, Blue }

class Dog implements Animal {
    name: string = "";
    constructor() {}
    bark(): void {}
}

function greet(): void {}
const helper = () => {}
"""
    ),
}

# ── Ожидаемые символы для каждого языка ───────────────────────────────────

EXPECTED = {
    "Python":     ["MY_CONST", "Animal", "speak", "move", "greet"],
    "Java":       ["Calculator", "Calculator", "add", "sub", "Shape", "area"],
    "C++":        ["utils", "Point", "length", "Vector", "dot", "helper"],
    "Go":         ["MaxSize", "Debug", "Animal", "Runner", "Greet", "Speak"],
    "JavaScript": ["Dog", "constructor", "bark", "greet", "hello", "arrow", "count", "name"],
    "TypeScript": ["Animal", "ID", "Color", "Dog", "constructor", "bark", "greet", "helper"],
}

# ── Вспомогательные функции ────────────────────────────────────────────────

KIND_NAMES = {v: k for k, v in vars(types.SymbolKind).items() if isinstance(v, int)}

def flatten(symbols, indent=0):
    """Рекурсивно разворачиваем дерево символов в плоский список."""
    result = []
    for s in symbols:
        result.append((indent, s))
        if s.children:
            result.extend(flatten(s.children, indent + 1))
    return result

def run_test(lang_name, module_path, class_name, source):
    print(f"\n{'='*55}")
    print(f"  {lang_name}")
    print(f"{'='*55}")

    # Импортируем языковой класс
    try:
        module = __import__(module_path, fromlist=[class_name])
        lang_class = getattr(module, class_name)
        lang = lang_class()
    except Exception as e:
        print(f"  [ОШИБКА ИМПОРТА] {e}")
        return False

    # Парсим
    try:
        symbols = lang.get_symbols(source)
    except Exception as e:
        print(f"  [ОШИБКА ПАРСИНГА] {e}")
        return False

    if not symbols:
        print("  [ПУСТО] символы не найдены!")
        return False

    # Выводим найденные символы
    flat = flatten(symbols)
    found_names = [s.name for _, s in flat]
    for indent, s in flat:
        kind = KIND_NAMES.get(s.kind.value, "?")
        line = s.range.start.line + 1
        prefix = "  " * indent
        print(f"  {prefix}[{kind:12s}] {s.name}  (строка {line})")

    # Проверяем ожидаемые символы
    expected = EXPECTED.get(lang_name, [])
    missing = [n for n in expected if n not in found_names]
    extra   = [n for n in found_names if n not in expected]

    ok = True
    if missing:
        print(f"\n  ОТСУТСТВУЮТ: {missing}")
        ok = False
    if extra:
        print(f"  ЛИШНИЕ:      {extra}")
        ok = False
    if ok:
        print(f"\n  OK — все {len(expected)} символов на месте")

    return ok

# ── Запуск ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = {}
    for lang_name, (module_path, class_name, source) in SAMPLES.items():
        results[lang_name] = run_test(lang_name, module_path, class_name, source)

    print(f"\n{'='*55}")
    print("  ИТОГ")
    print(f"{'='*55}")
    for lang, ok in results.items():
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}] {lang}")

    failed = [l for l, ok in results.items() if not ok]
    sys.exit(1 if failed else 0)
