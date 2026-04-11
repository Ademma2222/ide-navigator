---
name: Coursework — IDE Navigation Plugin
description: Details of the main active project being developed
type: project
---

**Project:** IDE navigation plugin based on static analysis — VS Code extension + Python LSP server.

**Deadline:** End of April 2026 (accelerated schedule, ~19 days from 2026-04-11).

**Why:** 2nd year coursework at HSE Russia. Supervisor gave free rein on implementation.

**Tech stack:**
- Python (main language): pygls (LSP server), tree-sitter (multi-language parsing)
- TypeScript (minimal boilerplate): VS Code extension client, WebView panel host
- HTML + vis.js: interactive call graph visualization

**Languages to analyze:** Python, Java, C++, Go, JavaScript, Swift (via tree-sitter grammars)

**Features to implement:**
1. Document Outline — file structure in sidebar
2. Go to Definition — Ctrl+Click jump to definition
3. Find All References — all usages of a symbol
4. Hover Info — signature on hover
5. Workspace Symbols — search across entire project
6. Call Graph Panel — interactive WebView graph (vis.js), nodes colored by type (class/function/variable), sized by LOC + connection count

**Development phases:**
- Phase 1 (Apr 11–14): Foundation — project setup, extension boilerplate, pygls server, tree-sitter basics
- Phase 2 (Apr 15–21): Core navigation — Outline, Go to Definition, Find References, Hover
- Phase 3 (Apr 22–26): Multi-language + Workspace Symbols
- Phase 4 (Apr 27–30): Call Graph WebView panel + polish

**Project folder:** to be created (not yet initialized)

**Environment:** Python 3.14.3 installed, Git installed, VS Code installed, Node.js LTS just installed (not yet verified).

**How to apply:** When resuming work, check what phase we're in and pick up from the last completed task.
