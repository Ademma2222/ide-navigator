---
name: Coursework — IDE Navigation Plugin
description: Details of the main active project being developed. v0.3.0 shipped 2026-04-19, mixin refactor committed 2026-05-09.
type: project
---

**Project:** IDE navigation plugin based on static analysis — VS Code extension + Python LSP server.

**Deadline:** End of April 2026 (просрочено для plugin-коммитов; пояснительная записка ещё ведётся).

**Current release:** **v0.3.0** (tag `v0.3.0`, commit `7d0ba3f`, 2026-04-19) — CodeLens, incremental parsing, cross-file Go to Definition (Python + JS/TS imports), FQN-квалификация в Call Graph, complexity в Hover, live-refresh Call Graph. Reverse и Depth toggle убраны из тулбара. Perf-патч `e91f34b` (2026-04-20) делает CodeLens 10-100× быстрее.

**Latest commit:** `ecfc9a0` (2026-05-09) — refactor: BaseLanguage разбит на 5 миксинов, webview-разметка вынесена в `extension/media/`, Swift убран. Внутренний рефакторинг, версия не бампается.

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

Python, Java, C++, Go, JavaScript, TypeScript.

Swift был удалён в коммите `ecfc9a0` (2026-05-09): tree-sitter-swift нет на PyPI для Windows и Linux-CI, поддержка через try/except + per-platform ветвления приносила больше шума, чем пользы (ни Андрей, ни Дима не используют Swift).

Каждый язык — отдельный модуль в `server/languages/`, наследует `BaseLanguage`. У каждого наследника есть class-атрибут `LANGUAGE_ID` (например, `"python"`, `"typescript"`) — используется для подсветки синтаксиса в Markdown-hover и в WebView-панели References.

---

## Features

| # | Фича | Статус |
|---|------|--------|
| 1 | Document Outline | Готово — все 6 языков |
| 2 | Go to Definition | Готово — single-file все 6 языков, **cross-file через резолв импортов для Python и JS/TS (v0.3.0)**, sandboxed по workspace roots |
| 3 | Find All References | Готово — LSP + кастомная WebView-панель |
| 4 | Hover Info | Готово — Markdown с подсветкой + cyclomatic complexity для функций (v0.3.0) |
| 5 | Workspace Symbols | Готово — Ctrl+T |
| 6 | Call Graph WebView | Готово — v0.2.0: dead code, cycles, complexity, export, history. v0.3.0: live-refresh на didChange, FQN-квалификация (Class.method), compact flex-wrap toolbar |
| 7 | **CodeLens** | Готово (v0.3.0) — счётчики референсов над функциями/классами, клик открывает References. Single-pass `count_identifiers_by_name` (10-100× быстрее N×find_references) |
| 8 | **Incremental parsing** | Готово (v0.3.0) — tree-sitter `old_tree` hint в `_parse(source, uri)` |

**Все фичи реализованы.** Плагин готов к сдаче.

---

## Phases

- **Phase 1 (Apr 11–14):** Foundation — setup, extension, pygls server, tree-sitter — ГОТОВО
- **Phase 2 (Apr 15–21):** Core navigation — Outline, Go to Definition, Find References, Hover — ГОТОВО
- **Phase 3 (Apr 22–26):** Multi-language polish + Workspace Symbols — ГОТОВО
- **Phase 4 (Apr 27–30):** Call Graph WebView panel + final polish — ГОТОВО (раньше срока)
- **Phase 5 (Apr 13):** Backend Quality & Hardening — ГОТОВО (за одну сессию)
- **Phase 6 (Apr 14–30):** Пояснительная записка к курсовой — следующий шаг
- **Call Graph Phase 4-5 (Apr 15):** Complexity + dead code + cycles + export + history — ГОТОВО (v0.2.0)

---

## Бэклог

Всё из бэклога Сессии 7 закрыто в v0.3.0 (Сессия 8): Reverse и Depth удалены, live-refresh Call Graph через `onDidChangeTextDocument` → debounce 1500ms (после perf-патча) → `postMessage('refresh')` работает.

Открытые мелочи (Сессия 9):
- Добавить `.claude/worktrees/` в корневой `.gitignore` (Claude Code internal state, сейчас засоряет `git status`).
- Пояснительная записка к курсовой — основная задача после всех plugin-коммитов.

---

## Phase 5 — Backend Quality & Hardening (план)

Цель: поднять качество бэкенда до уровня, достойного курсовой — безопасность, тесты, производительность, настройка. Каждый блок — отдельная тема для раздела пояснительной записки.

### Блок 1. Безопасность и устойчивость
- **XSS hardening Call Graph WebView**: сейчас `n.label`/`n.type` проходят через `JSON.stringify` → embed в `<script>`. Лейблы рендерятся canvas-ом vis.js (безопасно), но `typeLabels[t] || t` попадает в `row.innerHTML` легенды — явная дыра. Санитизировать на серверной стороне (белый список для type, ограничение длины label) + escape в JS.
- **Argument validation в кастомных командах** (`server.py`): `references_command` / `call_graph_command` принимают `*args` без проверки типов — любой кривой аргумент из клиента валит сервер. Добавить проверку `isinstance(uri, str)`, `isinstance(line, int)`, возврат None при несоответствии.
- **Graceful degradation на syntax errors**: обернуть `parser.parse`, `_extract_symbols` и прочие тяжёлые операции try/except ValueError,Exception — на битом tree-sitter AST возвращать пустой результат, а не крашить сервер. Логировать предупреждение.
- **CSP hardening**: в обоих WebView сейчас `'unsafe-inline'` — допустимо, но в пояснительной стоит объяснить почему (inline-скрипт генерируется из сервера) и какие альтернативы отвергнуты (nonce).
- **Path traversal в Workspace Symbols**: `_scan_workspace_files` игнорирует скрытые папки, но не `..` — теоретически workspace folder с символьной ссылкой может вылезти за корень. Низкий приоритет (не exploit surface), но упомянуть.

### Блок 2. Тесты (самая важная часть)
Сейчас тестов нет вообще — это главный пробел курсовой. План:
- **Setup**: `server/tests/` + `pytest` в requirements-dev.txt + `conftest.py`
- **Unit-тесты per-language для Outline** — по 1 файлу на язык, проверяем что `get_symbols()` находит ожидаемый набор классов/функций/переменных
- **Unit-тесты Go to Definition** — позиция → ожидаемый range
- **Unit-тесты Find References** — позиция → список ranges
- **Unit-тесты Hover** — позиция → ожидаемый Markdown
- **Unit-тесты Call Graph** — исходник → nodes/edges
- **Integration-тест через `pygls.lsp.server` test client** — реальный LSP flow, один tест на textDocument/documentSymbol
- **GitHub Actions CI** (`.github/workflows/tests.yml`) — запуск pytest на push/PR, matrix по Python 3.11/3.12/3.13

### Блок 3. Архитектура и производительность
- **AST cache** в `BaseLanguage`: LRU dict `{(uri, version): tree}` — сейчас Outline + Definition + References + Hover на одном файле парсят AST 4 раза. Инвалидация по смене документа через `textDocument/didChange`. Замерить ускорение до/после.
- **Метрики времени** в логах: обёртка-декоратор `@timed` на ключевых методах. В пояснительную — таблица latency p50/p95.

### Блок 4. Конфигурация и UX бэкенда
- **`contributes.configuration`** в `package.json`: `ideNavigator.logLevel` (info/debug/warning), `ideNavigator.cacheSize` (default 32), `ideNavigator.enableCallGraph` (bool). Клиент передаёт настройки через `initializationOptions`.
- **Status bar item**: "IDE Navigator: ready" / "parsing..." — визуальный фидбек что сервер жив.
- **Structured logging**: `logging.Formatter` с уровнями, путь к логу в temp dir, ротация.

### Порядок исполнения
1. Security hardening (1 сессия, ~2ч) — быстро, изолированно, закрывает реальные дыры — ГОТОВО
2. Tests — Outline unit-тесты (1 сессия, ~3ч) → остальные фичи (1-2 сессии) → CI (30 мин) — ГОТОВО (35 тестов, CI настроен)
3. AST cache + метрики (1 сессия, ~2ч) — ГОТОВО (LRU OrderedDict в BaseLanguage)
4. Configuration + status bar (1 сессия, ~1.5ч) — ГОТОВО
5. Параллельно пишем пояснительную записку — следующая фаза

### Результат Phase 5 (одна сессия 2026-04-13)
- 35 unit-тестов pytest, все зелёные (Outline/Definition/References/Hover/CallGraph/Cache)
- GitHub Actions CI (`.github/workflows/tests.yml`) — pytest на push/PR, matrix Python 3.11/3.12/3.13
- AST-кэш в BaseLanguage (LRU, 4-5x ускорение на одном файле)
- Санитизация Call Graph WebView (whitelist типов, лимит длины label, escape в легенде)
- Валидация аргументов кастомных команд + try/except во всех LSP-хэндлерах
- VS Code settings: `ideNavigator.logLevel`, `cacheSize`, `enableCallGraph` через `initializationOptions`
- Status bar item с состояниями starting → ready → error

### Пост-верификация Phase 5 (сессия 6 вечером)
При ручной проверке под F5 всплыли 4 бага — все починены в той же сессии:

1. **`initializationOptions` не применялись вообще.** pygls 2.x не хранит
   атрибут `ls.initialization_options`. Правильный путь — хукнуть
   `@server.feature(types.INITIALIZE)` и читать `params.initialization_options`.
   pygls специально даёт пользователю встроиться до отправки capabilities.
2. **`get_call_graph` парсил мимо кэша** — единственный метод, который
   остался с прямым `parser.parse(bytes(...))`. Переведён на `self._parse(source)`.
3. **`parse[LANG]: ... ms` лог поднят с DEBUG до INFO.** Cache miss — редкое
   событие (1 раз на версию файла), шума мало, зато в дефолтных логах сразу
   виден пруф работы кэша. Реальная цифра для курсовой: **11.2 ms на 80 KB
   Python-файл** (≈ 7 MB/s throughput tree-sitter).
4. **UTF-8 stderr.** На Windows `sys.stderr` пишет в cp1251, VS Code читает
   канал как UTF-8 → кракозябры. Фикс: `sys.stderr.reconfigure(encoding="utf-8")`
   до `logging.basicConfig()` в `server.py`.

**Urok for pygls 2.x:** `getattr(ls, "initialization_options", None)` — это
всегда `None`. Атрибута нет. Читать настройки только из `params` в INITIALIZE-хуке.

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
│   ├── src/
│   │   ├── extension.ts        ← LSP client + commands + WebView host (без HTML — он в media/)
│   │   └── webview-protocol.ts ← message-контракт host ↔ webview
│   ├── media/                  ← webview-разметка (вынесена из extension.ts в Сессии 9)
│   │   ├── callGraph.{html,css,js}
│   │   └── references.{html,css,js}
│   ├── package.json            ← commands, keybindings, configuration
│   └── tsconfig.json
└── server/                     ← Python LSP сервер
    ├── server.py               ← pygls handlers + custom commands + workspace roots
    ├── requirements.txt
    └── languages/
        ├── base.py             ← фасад (26 строк) — наследует 5 миксинов
        ├── _parse_cache.py     ← ParseCacheMixin: tree-sitter + LRU + incremental parsing
        ├── _definition.py      ← DefinitionMixin: go-to-def + cross-file (workspace-sandboxed)
        ├── _references.py      ← ReferencesMixin: find-references + CodeLens-counts
        ├── _hover.py           ← HoverMixin: tooltip + complexity
        ├── _call_graph.py      ← CallGraphMixin: call graph + McCabe + AST helpers
        ├── python_lang.py      ← + парсер импортов для cross-file (from/import)
        ├── java_lang.py
        ├── cpp_lang.py
        ├── go_lang.py
        ├── javascript_lang.py  ← + парсер импортов для cross-file (import/require)
        └── typescript_lang.py
```

---

## Key Implementation Details

### BaseLanguage (base.py — 26 строк, фасад)
Композиция миксинов в строгом порядке (важен для MRO — переопределение `_PARSE_CACHE_MAX` через `BaseLanguage` атрибут должно перебивать миксин):
```python
class BaseLanguage(ParseCacheMixin, DefinitionMixin, ReferencesMixin,
                   HoverMixin, CallGraphMixin, ABC):
    @abstractmethod
    def get_parser(self) -> Parser: ...
    @abstractmethod
    def _extract_symbols(self, node) -> list[DocumentSymbol]: ...
    def get_symbols(self, source, uri=None) -> list[DocumentSymbol]:
        tree = self._parse(source, uri)
        return self._extract_symbols(tree.root_node)
```

- `LANGUAGE_ID: str` — переопределяется в каждом наследнике, используется для подсветки в hover и References-панели

### Миксины — ключевые методы
- **ParseCacheMixin**: `_parse(source, uri=None)` — tree-sitter + LRU + incremental (`old_tree` hint per-URI). `_PARSE_CACHE_MAX = 32`, настраивается через `ideNavigator.cacheSize`. Cache-miss логируется на INFO: `parse[python]: 80KB in 11.2ms`.
- **DefinitionMixin**: `find_definition(source, line, char)` — single-file. `find_cross_file_definition(source, line, char, uri, language_map, workspace_roots)` — резолвит импорт, идёт в целевой файл, возвращает `Location`. `_is_path_within_workspace` — sandbox через `Path.resolve()` + `is_relative_to`.
- **ReferencesMixin**: `find_references(source, line, char, include_decl)`, `get_references_with_context(...)` для WebView-панели, `count_identifiers_by_name(source) → dict[name, count]` для CodeLens (single-pass, 10-100× быстрее N×find_references).
- **HoverMixin**: `get_hover(source, line, char)` — Markdown с подсветкой + kind + line N + complexity (через `_find_func_node_at` → `_compute_complexity`).
- **CallGraphMixin**: `get_call_graph(source)` — nodes/edges для vis.js. FQN scope qualifiers (`Class.method` ID, `method` label). Edge `kind: "call" | "contains"`. `_BRANCH_NODE_TYPES` — McCabe complexity для каждой функции.

### server.py — LSP handlers и кастомные команды
- `textDocument/documentSymbol` → Outline
- `textDocument/definition` → Go to Definition (single-file → cross-file через `find_cross_file_definition` с `workspace_roots` для sandbox)
- `textDocument/references` → Find All References (нативный LSP)
- `textDocument/hover` → Hover Info
- `textDocument/codeLens` → CodeLens с reference counts (через `count_identifiers_by_name`)
- `workspace/symbol` → Workspace Symbols
- `@server.command("ide-navigator.callGraph")` → Call Graph WebView data
- `@server.command("ide-navigator.references")` → References Panel WebView data
- Helper'ы: `_get_workspace_roots(ls)` собирает Path-список из `ls.workspace.folders` (pygls 2.x dict), `_folder_uri_to_path` срезает ведущий `/` из Windows file:///C:/... URI

### extension.ts + media/ — WebView-панели
**С Сессии 9 разметка лежит в `extension/media/` отдельными файлами**, TS-код только подгружает HTML через `panel.webview.asWebviewUri`. Совместный message-контракт host↔webview — в `extension/src/webview-protocol.ts`.

- **Call Graph** (`media/callGraph.{html,css,js}`): force-directed vis.js, Obsidian-style (тёмный фон #191919, цвета по SymbolKind, glow-shadow, класс → методы рёбрами containment). Live-refresh через `postMessage('refresh', data)` с дебаунсом 1500ms.
- **References Panel** (`media/references.{html,css,js}`): highlight.js (atom-one-dark), список референсов с номерами строк и сниппетами, клик → прыжок в файл через `postMessage` + `window.showTextDocument`

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
cd ../extension
npm install
npm run compile
```
Запуск: F5, рабочая папка — `extension/`.

**Разница Windows/Mac:**
- Python path в venv: `Scripts/python.exe` (Win) vs `bin/python` (Mac)
- extension.ts определяет ОС через `process.platform === 'win32'` — автоматически

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
