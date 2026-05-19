import pytest
from lsprotocol import types

from languages.python_lang import PythonLanguage
from languages.java_lang import JavaLanguage
from languages.cpp_lang import CppLanguage
from languages.go_lang import GoLanguage
from languages.javascript_lang import JavaScriptLanguage
from languages.typescript_lang import TypeScriptLanguage

def _names(symbols) -> set[str]:
    out = set()
    for s in symbols:
        out.add(s.name)
        if s.children:
            out.update(_names(s.children))
    return out

def _find(symbols, name):
    for s in symbols:
        if s.name == name:
            return s
        if s.children:
            found = _find(s.children, name)
            if found:
                return found
    return None

PYTHON_SRC = '''\
MY_CONST = 42

def top_level_func():
    pass

class Greeter:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}"
'''

def test_python_outline():
    lang = PythonLanguage()
    symbols = lang.get_symbols(PYTHON_SRC)
    names = _names(symbols)

    assert "MY_CONST" in names
    assert "top_level_func" in names
    assert "Greeter" in names
    assert "__init__" in names
    assert "greet" in names

    greeter = _find(symbols, "Greeter")
    assert greeter is not None
    assert greeter.kind == types.SymbolKind.Class
    greet = _find(greeter.children, "greet")
    assert greet is not None
    assert greet.kind == types.SymbolKind.Method

JAVA_SRC = '''\
public class Calculator {
    private int value;

    public Calculator(int start) {
        this.value = start;
    }

    public int add(int x) {
        return value + x;
    }
}
'''

def test_java_outline():
    lang = JavaLanguage()
    symbols = lang.get_symbols(JAVA_SRC)
    names = _names(symbols)

    assert "Calculator" in names
    assert "add" in names

    cls = _find(symbols, "Calculator")
    assert cls is not None
    assert cls.kind == types.SymbolKind.Class

CPP_SRC = '''\
#include <string>

int add(int a, int b) {
    return a + b;
}

class Point {
public:
    Point(int x, int y) : x_(x), y_(y) {}
    int x() const { return x_; }
private:
    int x_, y_;
};
'''

def test_cpp_outline():
    lang = CppLanguage()
    symbols = lang.get_symbols(CPP_SRC)
    names = _names(symbols)

    assert "add" in names
    assert "Point" in names

GO_SRC = '''\
package main

const MaxSize = 100

var counter int

type User struct {
    Name string
    Age  int
}

func (u *User) Greet() string {
    return "Hello " + u.Name
}

func main() {
    counter = 0
}
'''

def test_go_outline():
    lang = GoLanguage()
    symbols = lang.get_symbols(GO_SRC)
    names = _names(symbols)

    assert "main" in names
    assert "User" in names
    assert "Greet" in names
    assert "MaxSize" in names
    assert "counter" in names

JS_SRC = '''\
const PI = 3.14;
let count = 0;

function hello(name) {
    return "Hi " + name;
}

const add = (a, b) => a + b;

class Animal {
    constructor(name) {
        this.name = name;
    }
    speak() {
        return this.name;
    }
}
'''

def test_javascript_outline():
    lang = JavaScriptLanguage()
    symbols = lang.get_symbols(JS_SRC)
    names = _names(symbols)

    assert "hello" in names
    assert "add" in names
    assert "Animal" in names
    assert "speak" in names
    assert "PI" in names
    assert "count" in names

TS_SRC = '''\
interface Shape {
    area(): number;
}

type Point = { x: number; y: number };

enum Color {
    Red,
    Green,
    Blue,
}

class Circle implements Shape {
    constructor(private radius: number) {}
    area(): number {
        return Math.PI * this.radius ** 2;
    }
}

function compute(): number {
    return 42;
}
'''

def test_typescript_outline():
    lang = TypeScriptLanguage()
    symbols = lang.get_symbols(TS_SRC)
    names = _names(symbols)

    assert "Shape" in names
    assert "Color" in names
    assert "Circle" in names
    assert "area" in names
    assert "compute" in names

def test_empty_source_returns_empty():
    lang = PythonLanguage()
    assert lang.get_symbols("") == []

def test_broken_python_does_not_crash():
    lang = PythonLanguage()
    src = "def broken(\nclass X\n    pass"
    symbols = lang.get_symbols(src)
    assert isinstance(symbols, list)
