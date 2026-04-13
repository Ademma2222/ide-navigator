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

### Требования

- Python 3.11 или новее
- Node.js 18 или новее
- Visual Studio Code 1.85 или новее

### Шаги

```bash
# Клонирование репозитория
git clone https://github.com/Ademma2222/ide-navigator.git
cd ide-navigator

# Настройка Python-сервера
cd server
python -m venv venv
source venv/Scripts/activate    # Windows
source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt

# Настройка VS Code расширения
cd ../extension
npm install
npm run compile
```

### Запуск в режиме разработки

Откройте папку `ide-navigator/extension` в VS Code и нажмите `F5`. Откроется отдельное окно Extension Development Host с активным плагином — в нём можно проверять работу расширения на любом проекте.

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
