# IDE Navigator

<p align="center">
  <img src="https://media1.tenor.com/m/mxhNvaln24cAAAAC/pox3d.gif" width="600"/>
</p>

## Демо

<p align="center">
  <a href="https://youtu.be/Rx4OKa3KbXw">
    <img src="https://img.youtube.com/vi/Rx4OKa3KbXw/maxresdefault.jpg" width="600" alt="IDE Navigator — обзор расширения"/>
  </a>
</p>

<p align="center">
  <a href="https://youtu.be/Rx4OKa3KbXw">▶ Смотреть обзор на YouTube</a>
</p>

## Возможности

| Функция | Описание |
|---------|----------|
| Document Outline | Иерархическое дерево классов, функций и методов в боковой панели |
| Go to Definition | Переход к определению по `Ctrl+Click` или `F12`, включая cross-file через импорты |
| Find All References | Кастомная панель всех вхождений символа, вызывается по `Shift+F12` |
| Hover Info | Тултип с типом символа, сигнатурой и цикломатической сложностью |
| Workspace Symbols | Поиск символов по всему проекту через `Ctrl+T` |
| CodeLens | Счётчики использований над каждой функцией и классом |
| Call Graph | Интерактивный граф вызовов с детекцией циклов и мёртвого кода |

## Установка

Скачайте `.vsix` для своей платформы со [страницы релизов](https://github.com/Ademma2222/ide--navigator/releases/latest):

- **Windows x64** — `ide-navigator-win32-x64-<версия>.vsix`
- **macOS Apple Silicon** — `ide-navigator-darwin-arm64-<версия>.vsix`

```bash
code --install-extension ide-navigator-<target>-<версия>.vsix
```

Или через VS Code: `Ctrl+Shift+P` → `Extensions: Install from VSIX...`.

Никаких внешних зависимостей (Python, Node) ставить не требуется — сервер собран PyInstaller-ом и упакован в `.vsix`.

## Настройки

| Параметр | Значения | Описание |
|----------|----------|----------|
| `ideNavigator.logLevel` | `debug` / `info` / `warning` / `error` | Уровень логирования сервера |
| `ideNavigator.cacheSize` | `1..256` (по умолчанию `32`) | Максимум AST-деревьев в кэше |
| `ideNavigator.enableCallGraph` | `true` / `false` | Включает команду `Show Call Graph` |
