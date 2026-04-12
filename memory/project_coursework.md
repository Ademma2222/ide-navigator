---
name: Coursework — IDE Navigation Plugin
description: Details of the main active project being developed
type: project
---

**Project:** IDE navigation plugin based on static analysis — VS Code extension + Python LSP server.

**Deadline:** End of April 2026.

**Why:** 2nd year coursework at HSE Russia. Supervisor gave free rein on implementation.

---

## Tech Stack

| Компонент | Инструмент | Версия |
|-----------|-----------|--------|
| LSP сервер | pygls | 2.1.1 |
| Парсинг | tree-sitter | 0.25.2 |
| VS Code клиент | TypeScript + vscode-languageclient | 9.x |
| Граф вызовов (будущее) | vis.js (WebView) | — |

**Важно:** pygls 2.x — импорт из `pygls.lsp.server`, не `pygls.server`.

---

## Languages to analyze

Python, Java, C++, Go, JavaScript, TypeScript, Swift (опциональный — только Mac).
Каждый язык — отдельный модуль в `server/languages/`, наследует `BaseLanguage`.

---

## Features

| # | Фича | Статус |
|---|------|--------|
| 1 | Document Outline | ✅ ГОТОВО |
| 2 | Go to Definition (single-file) | ✅ ГОТОВО |
| 3 | Find All References | ⬜ TODO |
| 4 | Hover Info | ⬜ TODO |
| 5 | Workspace Symbols | ⬜ TODO |
| 6 | Call Graph WebView (vis.js) | ⬜ TODO |

---

## Phases

- **Phase 1 (Apr 11–14):** Foundation — setup, extension, pygls server, tree-sitter ✅
- **Phase 2 (Apr 15–21):** Core navigation — Outline ✅, Go to Definition ✅, Find References, Hover
- **Phase 3 (Apr 22–26):** Multi-language polish + Workspace Symbols
- **Phase 4 (Apr 27–30):** Call Graph WebView panel + final polish

---

## Repository

**URL:** https://github.com/Ademma2222/ide-navigator (приватный)
**Ветки:**
- `master` — стабильная, всегда рабочая
- `dev/andrey` — рабочая ветка Андрея
- `dev/dima` — рабочая ветка Димы

---

## Project Structure

```
ide-navigator/
├── extension/                  ← VS Code extension (TypeScript, ~80 строк)
│   ├── src/extension.ts        ← запускает Python сервер, регистрирует команды
│   ├── package.json            ← activationEvents, contributes
│   └── tsconfig.json           ← skipLibCheck: true (TS 6.0 workaround)
└── server/                     ← Python LSP сервер
    ├── server.py               ← pygls хендлеры: Outline, Go to Definition
    ├── requirements.txt        ← pygls, tree-sitter, все grammar пакеты
    └── languages/
        ├── base.py             ← BaseLanguage: get_symbols(), find_definition(), _make_symbol()
        ├── python_lang.py      ← function, class, module-level variables
        ├── java_lang.py        ← class, interface, method, constructor
        ├── cpp_lang.py         ← class, struct, namespace, function
        ├── go_lang.py          ← function, method, struct, interface, const, var
        ├── javascript_lang.py  ← class, function, arrow function, variable
        ├── typescript_lang.py  ← extends JS + interface, type alias, enum
        └── swift_lang.py       ← только Mac (tree_sitter_swift нет на PyPI для Windows)
```

---

## Key Implementation Details

### base.py — BaseLanguage
- `get_symbols(source)` → парсит, вызывает `_extract_symbols(root_node)`
- `find_definition(source, line, character)` → находит identifier под курсором через `descendant_for_point_range`, ищет совпадение в символах файла
- `_find_symbol_by_name(symbols, name)` → рекурсивный поиск по дереву символов
- `_make_symbol(name, kind, node, name_node, children)` → создаёт `DocumentSymbol`

### server.py — LSP handlers
- `textDocument/documentSymbol` → Document Outline
- `textDocument/definition` → Go to Definition
- `LANGUAGE_MAP` — dict расширение → экземпляр языкового класса
- Swift импортируется опционально (try/except), сервер работает без него

### Go to Definition — как работает
1. `descendant_for_point_range((line, char), (line, char))` — leaf node под курсором
2. Проверяем что тип содержит `"identifier"` (identifier, type_identifier, property_identifier, etc.)
3. Берём текст — это имя символа
4. Ищем в символах файла через `_find_symbol_by_name`
5. Возвращаем `Location(uri=uri, range=found.selection_range)`

### Python — важный нюанс
Переменные на уровне модуля в tree-sitter Python оборачиваются в `expression_statement → assignment`, НЕ `assignment` напрямую среди детей `module`.
Поэтому ищем `expression_statement`, внутри ищем `assignment`.

---

## Environment Setup

### Andrey (Windows)
```bash
git clone https://github.com/Ademma2222/ide-navigator
cd ide-navigator/server
python -m venv venv
venv/Scripts/pip install -r requirements.txt
cd ../extension
npm install
npm run compile
```
Запуск: F5 в VS Code (Extension Development Host)

### Dima (Mac)
```bash
git clone https://github.com/Ademma2222/ide-navigator
cd ide-navigator/server
python3 -m venv venv
venv/bin/pip install -r requirements.txt
# tree_sitter_swift установить отдельно если нужен Swift:
# venv/bin/pip install tree-sitter-swift
cd ../extension
npm install
npm run compile
```
Запуск: F5 в VS Code (Extension Development Host)

**Разница Windows/Mac:**
- Python path в venv: `Scripts/python.exe` (Win) vs `bin/python` (Mac)
- extension.ts определяет ОС через `process.platform === 'win32'` — автоматически
- Swift: только на Mac, на Windows сервер стартует без него (warning в логах)

---

## .gitignore Structure

- `2CourseWork/.gitignore` — OS-мусор для всего репо: `.DS_Store` (Mac), `Thumbs.db` (Win)
- `ide-navigator/.gitignore` — project-specific: `server/venv/`, `**/__pycache__/`, `**/*.pyc`, `extension/node_modules/`, `extension/out/`, `extension/*.vsix`
- `server/venv/.gitignore` — автогенерирован Python venv (`*`), не трогать

---

## Common Pitfalls

1. **pygls 2.x:** импорт `from pygls.lsp.server import LanguageServer`, не `pygls.server`
2. **TypeScript 6.0:** нужен `"skipLibCheck": true` в `tsconfig.json`
3. **TransportKind.stdio:** убрать из ServerOptions — только для Node.js модулей
4. **__pycache__:** никогда не коммитить — прописать в .gitignore ДО первого `git add`
5. **Ветки:** всегда коммитить перед `git checkout` — иначе несохранённые файлы исчезнут
6. **npm:** запускать только из `extension/`, не из `server/`
