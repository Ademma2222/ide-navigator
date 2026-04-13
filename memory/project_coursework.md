---
name: Coursework — IDE Navigation Plugin
description: Details of the main active project being developed
type: project
---

**Project:** IDE navigation plugin based on static analysis — VS Code extension + Python LSP server.

**Deadline:** End of April 2026. Today: 2026-04-13.

**Why:** 2nd year coursework at HSE Russia. Supervisor gave free rein on implementation.

---

## Tech Stack

| Компонент | Инструмент | Версия |
|-----------|-----------|--------|
| LSP сервер | pygls | 2.1.1 |
| Парсинг | tree-sitter | 0.25.2 |
| VS Code клиент | TypeScript + vscode-languageclient | 9.x |
| Call Graph (WebView) | vis.js | via unpkg CDN |
| References panel (WebView) | highlight.js | @highlightjs/cdn-assets 11.9.0 via unpkg |

**Важно:** pygls 2.x — импорт из `pygls.lsp.server`, не `pygls.server`.

---

## Languages

Python, Java, C++, Go, JavaScript, TypeScript, Swift (опциональный — только Mac).

Каждый язык — отдельный модуль в `server/languages/`, наследует `BaseLanguage`. У каждого наследника есть class-атрибут `LANGUAGE_ID` (например, `"python"`, `"typescript"`) — используется для подсветки синтаксиса в Markdown-hover и в WebView-панели References.

---

## Features

| # | Фича | Статус |
|---|------|--------|
| 1 | Document Outline | Готово — все 6 языков |
| 2 | Go to Definition (single-file) | Готово — все 6 языков |
| 3 | Find All References | Готово — все 6 языков, LSP + кастомная WebView-панель |
| 4 | Hover Info | Готово — Markdown с подсветкой синтаксиса |
| 5 | Workspace Symbols | Готово — Ctrl+T |
| 6 | Call Graph WebView | Готово — Obsidian-style force-directed граф, vis.js |

**Все фичи реализованы.** Плагин готов к сдаче.

---

## Phases

- **Phase 1 (Apr 11–14):** Foundation — setup, extension, pygls server, tree-sitter — ГОТОВО
- **Phase 2 (Apr 15–21):** Core navigation — Outline, Go to Definition, Find References, Hover — ГОТОВО
- **Phase 3 (Apr 22–26):** Multi-language polish + Workspace Symbols — ГОТОВО
- **Phase 4 (Apr 27–30):** Call Graph WebView panel + final polish — ГОТОВО (раньше срока)

Оставшееся время до дедлайна — доработка UX и написание пояснительной записки.

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
├── extension/                  ← VS Code extension (TypeScript)
│   ├── src/extension.ts        ← LSP client + commands + WebView-генераторы
│   ├── package.json            ← commands, keybindings (shift+f12 → наша панель)
│   └── tsconfig.json           ← skipLibCheck: true (TS 6.0 workaround)
└── server/                     ← Python LSP сервер
    ├── server.py               ← pygls handlers + custom commands (callGraph, references)
    ├── requirements.txt
    └── languages/
        ├── base.py             ← BaseLanguage: общий интерфейс + LANGUAGE_ID атрибут
        ├── python_lang.py
        ├── java_lang.py
        ├── cpp_lang.py
        ├── go_lang.py
        ├── javascript_lang.py
        ├── typescript_lang.py
        └── swift_lang.py       ← Mac-only (tree_sitter_swift нет на PyPI для Windows)
```

---

## Key Implementation Details

### BaseLanguage (base.py)
- `LANGUAGE_ID: str` — переопределяется в каждом наследнике, используется для подсветки синтаксиса в hover и в References-панели
- `get_symbols(source)` → AST → `_extract_symbols()` (переопределяется)
- `find_definition(source, line, char)` → leaf node → identifier → рекурсивный поиск в символах файла
- `find_references(source, line, char, include_decl)` → обход AST, сбор identifier-узлов с нужным именем
- `get_hover(source, line, char)` → Markdown-блок с подсветкой (через `LANGUAGE_ID`) + жирный kind + em-dash + line N
- `get_references_with_context(source, line, char, include_decl)` → dict с `name`, `language`, `refs: [{line, character, endCharacter, snippet}]` для WebView-панели
- `get_call_graph(source)` → nodes/edges для vis.js, включая класс-методы как hub-узлы

### server.py — LSP handlers и кастомные команды
- `textDocument/documentSymbol` → Outline
- `textDocument/definition` → Go to Definition
- `textDocument/references` → Find All References (нативный LSP)
- `textDocument/hover` → Hover Info
- `workspace/symbol` → Workspace Symbols
- `@server.command("ide-navigator.callGraph")` → Call Graph WebView data
- `@server.command("ide-navigator.references")` → References Panel WebView data

### extension.ts — WebView-панели
- **Call Graph**: force-directed vis.js, Obsidian-style (тёмный фон #191919, цвета по SymbolKind, glow-shadow, класс → методы рёбрами containment)
- **References Panel**: highlight.js (atom-one-dark), список референсов с номерами строк и сниппетами, клик → прыжок в файл через `postMessage` + `window.showTextDocument`

### Keybindings
- `Shift+F12` перебинжен на `ide-navigator.showReferences` в `package.json` → нашa панель открывается вместо встроенного Peek-виджета. Встроенный Peek как fallback при Ctrl+Click на определение остаётся (перехватить нельзя).

### Важные нюансы
- pygls 2.x: `folders` в workspace — это dict `{uri: WorkspaceFolder}`, а не list
- Python variables в Outline: оборачиваются в `expression_statement → assignment`
- C++ function name: вложено как `declarator → function_declarator → declarator`
- JS arrow functions: `variable_declarator` со значением `arrow_function`/`function_expression`
- Swift: весь импорт в try/except → сервер работает на Windows без него
- extension.ts documentSelector: включает `typescript` и `typescriptreact`

---

## Environment Setup

### Andrey (Windows, Python 3.14.3, Node 24)
```bash
git clone https://github.com/Ademma2222/ide-navigator
cd ide-navigator/server
python -m venv venv
venv/Scripts/pip install -r requirements.txt
cd ../extension
npm install
npm run compile
```
Запуск: F5 в VS Code (Extension Development Host), рабочая папка — `extension/`.

### Dima (Mac, Python 3.13.7, Node 25)
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
Запуск: F5, рабочая папка — `extension/`.

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

1. pygls 2.x: импорт `from pygls.lsp.server import LanguageServer`, не `pygls.server`
2. TypeScript 6.0: нужен `"skipLibCheck": true` в `tsconfig.json`
3. `TransportKind.stdio` убрать из ServerOptions — только для Node.js модулей
4. `__pycache__` никогда не коммитить — прописать в .gitignore ДО первого `git add`
5. Всегда коммитить перед `git checkout` — иначе несохранённые файлы исчезнут
6. npm запускать только из `extension/`, не из `server/`
7. После правок `package.json` — нужен полный перезапуск Extension Development Host (не Reload Window), VS Code читает его только при старте
8. WebView из unpkg CDN: CSP должен разрешать `script-src https://unpkg.com` и, для highlight.js, `style-src https://unpkg.com`
