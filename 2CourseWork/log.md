# Wiki Log
Append-only. Most recent entries at the top.
Format: `## [YYYY-MM-DD] <operation> | <title>`

---

## [2026-04-15] coursework | IDE Navigator v0.2.0 shipped — Call Graph Phase 4-5
User request: "давай сделаем все, что связано с графом" → phased plan, "A" chosen (phases 1-3 this session), then "давай обе сделаем" (phases 4+5 too).

Server ([base.py](../ide-navigator/server/languages/base.py)): McCabe cyclomatic complexity via `_BRANCH_NODE_TYPES` (structural AST nodes only; raw `if`/`for`/`while` tokens dropped to avoid double-count; Java switch counted by `switch_block_statement_group` per-case). One-line fix in [python_lang.py](../ide-navigator/server/languages/python_lang.py) to recurse into `decorated_definition` — before this, `@property`/`@staticmethod` methods were silently dropped from Outline and Call Graph.

Client ([extension.ts](../ide-navigator/extension/src/extension.ts)): toolbar grew 7 controls — back/forward history arrows (Alt+←/Alt+→), Unused toggle (gray + 0.4 opacity for 0-incoming-calls nodes, classes excluded), Cycles toggle (iterative Tarjan SCC, red thick edges), Export dropdown (PNG via canvas.toDataURL, SVG built from network.getPositions, Mermaid/DOT copied to clipboard). Cyclomatic complexity shown in node tooltip.

Fixed three stale-binary symptoms by rebuilding PyInstaller bundled server. Fixed MultiDict method-count mismatch (8 shown vs 10 real) — `methodToClass` map was overwriting on name collisions across classes; replaced with `classToMethods: className → Set<method>` for correct counting.

Tests: 40/40 passing (11 call_graph including complexity for Python branching=3, loopy=5 and Java complex=6). Demo file at [demo_showcase.py](../ide-navigator/demo_showcase.py) exercises all features.

Release: version bumped 0.1.0 → 0.2.0, committed as `c44a02c`, tag `v0.2.0` pushed (CI release.yml builds win32-x64 + darwin-arm64 .vsix on tag push).

Backlog additions per user ("добавь в список необходимых изменений позже"): REMOVE Reverse toggle, REMOVE Depth slider, fix live Call Graph refresh when user adds/removes a function (panel currently needs reopening).

## [2026-04-11] ingest | LLM Wiki — A Pattern for Building Personal Knowledge Bases
Pages created: wiki/sources/llm-wiki-pattern, wiki/concepts/knowledge-compounding, wiki/concepts/rag-vs-wiki, wiki/concepts/wiki-maintenance, wiki/entities/vannevar-bush.
Pages updated: index.md, log.md.
Key themes: knowledge-management, llm-as-wiki-agent, rag-vs-persistent-wiki, compounding-knowledge.

## [2026-04-11] init | Wiki system initialized
Schema created (CLAUDE.md). Folder structure created: wiki/sources, wiki/concepts, wiki/entities, wiki/queries, raw/assets.
Index and log initialized. Wiki is empty — ready for first ingest.
