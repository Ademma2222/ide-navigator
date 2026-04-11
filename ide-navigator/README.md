# IDE Navigator

> Плагин для VS Code на основе статического анализа кода.
> Поддерживает 6 языков. Не требует запуска кода — только анализ исходников.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat-square&logo=typescript&logoColor=white)
![VS Code](https://img.shields.io/badge/VS%20Code-Extension-007ACC?style=flat-square&logo=visualstudiocode&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## Возможности

| Функция | Статус | Описание |
|---------|--------|----------|
| Структура файла | 🚧 В разработке | Дерево классов и функций в боковой панели |
| Перейти к определению | 🚧 В разработке | Переход к месту где объявлен символ |
| Найти все использования | 🚧 В разработке | Все места где используется символ |
| Подсказка при наведении | 🚧 В разработке | Сигнатура функции при наведении курсора |
| Поиск по проекту | 🚧 В разработке | Поиск символов по всему проекту |
| Граф вызовов | 🚧 В разработке | Интерактивный граф связей между функциями |

## Поддерживаемые языки

🐍 Python · ☕ Java · ⚡ C++ · 🐹 Go · 🌐 JavaScript · 🍎 Swift

---

## Архитектура

```
VS Code Extension (TypeScript)
        │
        │  LSP (JSON-RPC через stdio)
        ▼
Python Language Server (pygls)
        │
        ├── Tree-sitter (парсер для всех языков)
        ├── Индексер (индекс символов всего проекта)
        └── WebView (граф вызовов на vis.js)
```

TypeScript расширение — тонкий клиент (~80 строк). Вся логика анализа в Python сервере.

---

## Установка

### Требования
- Python 3.11+
- Node.js 18+
- VS Code 1.85+

### Шаги

```bash
# Клонировать репозиторий
git clone https://github.com/Ademma2222/ide-navigator.git
cd ide-navigator

# Настроить Python сервер
cd server
python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt

# Настроить VS Code расширение
cd ../extension
npm install
npm run compile
```

### Запуск в режиме разработки

```bash
code --extensionDevelopmentPath=/путь/к/ide-navigator/extension
```

---

## Структура проекта

```
ide-navigator/
├── extension/          # VS Code расширение (TypeScript)
│   ├── src/
│   │   └── extension.ts
│   └── package.json
│
└── server/             # Language Server (Python)
    ├── server.py       # Точка входа LSP (pygls)
    ├── analyzer.py     # Логика статического анализа
    ├── indexer.py      # Индекс символов проекта
    └── languages/      # Запросы Tree-sitter по языкам
        ├── python_lang.py
        ├── java_lang.py
        ├── cpp_lang.py
        ├── go_lang.py
        ├── javascript_lang.py
        └── swift_lang.py
```

---

## Использованные технологии

- [pygls](https://github.com/openlawlibrary/pygls) — Python LSP фреймворк
- [tree-sitter](https://tree-sitter.github.io/) — Универсальный парсер
- [vis.js](https://visjs.org/) — Интерактивная визуализация графов
- [vscode-languageclient](https://github.com/microsoft/vscode-languageserver-node) — LSP клиент для VS Code

---

*Курсовая работа — НИУ ВШЭ, Компьютерные науки, 2026*
