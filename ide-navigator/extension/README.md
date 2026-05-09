# IDE Navigator

Lightweight static-analysis navigation for **Python, Java, C/C++, Go, JavaScript, TypeScript**. Powered by tree-sitter — no language server runtimes, no extra installs.

## Features

- **Document Outline** — symbol tree in the Outline view
- **Go to Definition** (`F12` / `Ctrl+Click`) — single-file, instant
- **Find All References** (`Shift+F12`) — includes a syntax-highlighted References panel
- **Hover Info** — symbol kind, signature, location
- **Workspace Symbols** (`Ctrl+T`) — fuzzy search across the whole project
- **Call Graph** — interactive vis.js graph of function calls (`IDE Navigator: Show Call Graph`)

## Zero setup

The extension bundles a standalone LSP server — **no Python required**. Install and it works.

## Installation

Download the `.vsix` file for your platform from the [latest release](https://github.com/Ademma2222/ide-navigator/releases/latest):

- **Windows x64:** `ide-navigator-win32-x64-*.vsix`
- **macOS Apple Silicon:** `ide-navigator-darwin-arm64-*.vsix`

Then install it:

```bash
code --install-extension ide-navigator-<target>-<version>.vsix
```

Or in VS Code UI: `Ctrl+Shift+P` → `Extensions: Install from VSIX...` → pick the file.

## Settings

- `ideNavigator.logLevel` — `debug` / `info` / `warning` / `error`
- `ideNavigator.cacheSize` — max AST trees cached (default 32)
- `ideNavigator.enableCallGraph` — toggle the Call Graph command

## How it works

IDE Navigator uses [tree-sitter](https://tree-sitter.github.io/) to parse source files into ASTs, then walks them to locate symbols, references, and call edges. Unlike heavyweight language servers, this means:

- **Fast** — parse trees are cached, incremental updates are cheap
- **Portable** — no JDK, no gopls, no clangd, no Node toolchain required
- **Single-file scope** — works even on loose files outside a project

## License

MIT
