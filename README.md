# IDE Navigator

> Плагин для Visual Studio Code на основе статического анализа исходного кода.
> Реализует навигацию, поиск и визуализацию структуры проекта без запуска программы — только через разбор AST.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat-square&logo=typescript&logoColor=white)
![VS Code](https://img.shields.io/badge/VS%20Code-Extension-007ACC?style=flat-square&logo=visualstudiocode&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

<p align="center">
  <img src="https://media1.tenor.com/m/mxhNvaln24cAAAAC/pox3d.gif" width="600"/>
</p>

---

## Возможности

| Функция | Описание |
|---------|----------|
| Document Outline | Иерархическое дерево классов, функций и методов в боковой панели VS Code |
| Go to Definition | Переход к месту объявления символа по `Ctrl+Click` |
| Find All References | Кастомная панель всех вхождений символа с подсветкой синтаксиса, вызывается по `Shift+F12` |
| Hover Info | Тултип с типом символа, первой строкой определения и номером строки |
| Workspace Symbols | Поиск символов по всему проекту через `Ctrl+T` |
| Call Graph | Интерактивный граф вызовов в стиле Obsidian, открывается через Command Palette |

## Поддерживаемые языки

Python, Java, C++, Go, JavaScript, TypeScript, Swift (опционально, только на macOS).

Каждый язык реализован как отдельный модуль, наследующий общий базовый класс `BaseLanguage`.

---

## Архитектура

```
VS Code Extension (TypeScript)
        │
        │  Language Server Protocol (JSON-RPC через stdio)
        ▼
Python Language Server (pygls)
        │
        ├── tree-sitter — построение AST для каждого из поддерживаемых языков
        ├── languages/  — модули анализа, по одному на язык
        └── WebView    — панели Call Graph и References (vis.js, highlight.js)
```

Клиент на TypeScript представляет собой тонкий адаптер: запускает Python-процесс, регистрирует команды и управляет WebView-панелями. Вся логика статического анализа реализована на стороне сервера.

---

## Установка

Расширение поставляется как самодостаточный `.vsix` со встроенным Python-сервером, собранным через PyInstaller. Никаких локальных зависимостей (Python, Node, tree-sitter) для конечного пользователя не требуется.

### Быстрый старт

1. Скачайте `.vsix` для своей платформы со [страницы релизов](https://github.com/Ademma2222/ide-navigator/releases/latest):
   - **Windows x64** — `ide-navigator-win32-x64-<версия>.vsix`
   - **macOS Apple Silicon** — `ide-navigator-darwin-arm64-<версия>.vsix`
2. Установите одной командой:
   ```bash
   code --install-extension ide-navigator-<target>-<версия>.vsix
   ```
   Либо через интерфейс VS Code: `Ctrl+Shift+P` → `Extensions: Install from VSIX...`.
3. Перезапустите редактор и откройте любой поддерживаемый файл.

### Настройки расширения

| Параметр | Значения | Описание |
|----------|----------|----------|
| `ideNavigator.logLevel` | `debug` / `info` / `warning` / `error` | Уровень логирования сервера |
| `ideNavigator.cacheSize` | `1..256` (по умолчанию `32`) | Максимум AST-деревьев в кэше парсера |
| `ideNavigator.enableCallGraph` | `true` / `false` | Включает команду `Show Call Graph` |

### Сборка из исходников (для разработчиков)

```bash
git clone https://github.com/Ademma2222/ide-navigator.git
cd ide-navigator

# Python-сервер
cd server
python -m venv venv
source venv/Scripts/activate    # Windows (git-bash)
source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt

# VS Code расширение
cd ../extension
npm install
npm run compile
```

Откройте папку `ide-navigator/extension` в VS Code и нажмите `F5` — откроется окно Extension Development Host, в котором расширение запустится с локальным Python-сервером из `../server`.

### CI и релизы

Пайплайн [`.github/workflows/release.yml`](.github/workflows/release.yml) на каждый тэг `v*` собирает PyInstaller-бинарь сервера на Windows и macOS Apple Silicon, упаковывает platform-specific `.vsix` и публикует их в GitHub Release.

---

## Структура проекта

```
ide-navigator/
├── extension/                  — VS Code расширение (TypeScript)
│   ├── src/
│   │   └── extension.ts        — LSP-клиент, регистрация команд, WebView-панели
│   ├── package.json            — contributes: commands, keybindings
│   └── tsconfig.json
│
└── server/                     — Language Server (Python)
    ├── server.py               — pygls: LSP-обработчики и кастомные команды
    ├── requirements.txt
    └── languages/
        ├── base.py             — BaseLanguage: общая логика для всех языков
        ├── python_lang.py
        ├── java_lang.py
        ├── cpp_lang.py
        ├── go_lang.py
        ├── javascript_lang.py
        ├── typescript_lang.py
        └── swift_lang.py       — опциональный модуль, активен только на macOS
```

---

## Использованные технологии

- [pygls](https://github.com/openlawlibrary/pygls) — реализация Language Server Protocol на Python
- [tree-sitter](https://tree-sitter.github.io/) — универсальный инкрементальный парсер исходного кода
- [vis.js](https://visjs.org/) — библиотека интерактивной визуализации графов
- [highlight.js](https://highlightjs.org/) — подсветка синтаксиса в WebView-панелях
- [vscode-languageclient](https://github.com/microsoft/vscode-languageserver-node) — LSP-клиент для VS Code

---

*Курсовая работа. Национальный исследовательский университет «Высшая школа экономики», факультет компьютерных наук, 2026.*
