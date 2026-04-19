import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions
} from 'vscode-languageclient/node';

let client: LanguageClient;
let statusBar: vscode.StatusBarItem;

function setStatus(text: string, tooltip?: string) {
    statusBar.text = `$(symbol-namespace) ${text}`;
    statusBar.tooltip = tooltip;
    statusBar.show();
}

export function activate(context: vscode.ExtensionContext) {
    // Status bar: единый индикатор состояния плагина
    statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.command = 'ide-navigator.showCallGraph';
    setStatus('IDE Navigator: starting…', 'Запускается Python LSP сервер');
    context.subscriptions.push(statusBar);

    // Настройки из VS Code (раздел ideNavigator.*)
    const config = vscode.workspace.getConfiguration('ideNavigator');
    const initializationOptions = {
        logLevel: config.get<string>('logLevel', 'info'),
        cacheSize: config.get<number>('cacheSize', 32),
        enableCallGraph: config.get<boolean>('enableCallGraph', true),
    };

    // Путь к бандленому серверу внутри расширения (bundled/server/<target>/…).
    // Таргет соответствует vsce --target: win32-x64, darwin-arm64.
    const target = `${process.platform}-${process.arch}`;
    const binaryName = process.platform === 'win32'
        ? 'ide-navigator-server.exe'
        : 'ide-navigator-server';
    const serverBinary = context.asAbsolutePath(
        path.join('bundled', 'server', target, binaryName)
    );

    console.log('IDE Navigator: target  =', target);
    console.log('IDE Navigator: binary  =', serverBinary);

    // На Mac/Linux .vsix-zip может потерять exec-бит при распаковке VS Code.
    // Ставим его руками перед запуском (no-op на Windows).
    if (process.platform !== 'win32') {
        try {
            fs.chmodSync(serverBinary, 0o755);
        } catch (err) {
            console.warn('IDE Navigator: chmod failed', err);
        }
    }

    // Настройки запуска сервера (standalone бинарь, без Python)
    const serverOptions: ServerOptions = {
        command: serverBinary,
        args: []
    };

    // Языки которые обрабатывает плагин
    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'python' },
            { scheme: 'file', language: 'java' },
            { scheme: 'file', language: 'cpp' },
            { scheme: 'file', language: 'c' },
            { scheme: 'file', language: 'go' },
            { scheme: 'file', language: 'javascript' },
            { scheme: 'file', language: 'typescript' },
            { scheme: 'file', language: 'typescriptreact' },
            { scheme: 'file', language: 'swift' }
        ],
        initializationOptions,
    };

    // Создаём и запускаем LSP клиент
    client = new LanguageClient(
        'ide-navigator',
        'IDE Navigator',
        serverOptions,
        clientOptions
    );

    client.start().then(() => {
        console.log('IDE Navigator: сервер успешно запущен');
        setStatus('IDE Navigator', 'LSP сервер активен. Клик — Show Call Graph');
    }).catch((err) => {
        console.error('IDE Navigator: ошибка запуска сервера', err);
        setStatus('IDE Navigator: error', err.message);
        vscode.window.showErrorMessage(`IDE Navigator: ошибка — ${err.message}`);
    });

    // Команда для открытия графа вызовов
    const showCallGraph = vscode.commands.registerCommand(
        'ide-navigator.showCallGraph',
        async () => {
            const enabled = vscode.workspace
                .getConfiguration('ideNavigator')
                .get<boolean>('enableCallGraph', true);
            if (!enabled) {
                vscode.window.showInformationMessage(
                    'Call Graph отключён в настройках (ideNavigator.enableCallGraph)'
                );
                return;
            }

            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('Откройте файл для построения графа');
                return;
            }

            const sourceUri = editor.document.uri;
            const uri = sourceUri.toString();

            interface GraphNode {
                id: string;
                label: string;
                type?: string;
                line?: number;
                character?: number;
                endLine?: number;
                endCharacter?: number;
                complexity?: number;
            }
            interface GraphEdge {
                from: string;
                to: string;
                kind: 'call' | 'contains';
            }
            interface GraphData {
                nodes: GraphNode[];
                edges: GraphEdge[];
            }

            let graphData: GraphData;
            try {
                graphData = await client.sendRequest('workspace/executeCommand', {
                    command: 'ide-navigator.callGraph',
                    arguments: [uri]
                });
            } catch (err: any) {
                vscode.window.showErrorMessage(`Call Graph: ошибка — ${err.message}`);
                return;
            }

            if (!graphData || graphData.nodes.length === 0) {
                vscode.window.showInformationMessage('Граф вызовов пуст — функции не найдены');
                return;
            }

            const panel = vscode.window.createWebviewPanel(
                'callGraph',
                `Call Graph: ${path.basename(editor.document.fileName)}`,
                vscode.ViewColumn.Beside,
                { enableScripts: true }
            );

            panel.webview.html = getCallGraphHtml(graphData);

            // Клик / двойной клик по вершине → открыть файл на определении.
            // Сервер уже положил line/character/endCharacter в каждый node
            // (selection_range идентификатора), поэтому курсор встанет ровно
            // на имя символа.
            panel.webview.onDidReceiveMessage(
                async (message) => {
                    if (message.command === 'openNode') {
                        if (typeof message.line !== 'number' || typeof message.character !== 'number') {
                            return;
                        }
                        const pos = new vscode.Position(message.line, message.character);
                        const endChar = typeof message.endCharacter === 'number'
                            ? message.endCharacter
                            : message.character;
                        const range = new vscode.Range(
                            pos,
                            new vscode.Position(message.line, endChar),
                        );
                        await vscode.window.showTextDocument(sourceUri, {
                            selection: range,
                            viewColumn: vscode.ViewColumn.One,
                            preserveFocus: false,
                        });
                    } else if (message.command === 'exportGraph') {
                        const payload = message.payload;
                        if (!payload || !payload.format) return;
                        const base = path.basename(editor.document.fileName, path.extname(editor.document.fileName));
                        const fmt = payload.format;
                        try {
                            if (fmt === 'mermaid' || fmt === 'dot') {
                                await vscode.env.clipboard.writeText(payload.text || '');
                                vscode.window.showInformationMessage(`Call Graph: ${fmt.toUpperCase()} скопирован в буфер обмена`);
                            } else if (fmt === 'svg') {
                                const uri = await vscode.window.showSaveDialog({
                                    defaultUri: vscode.Uri.file(path.join(path.dirname(editor.document.fileName), `${base}.callgraph.svg`)),
                                    filters: { 'SVG': ['svg'] }
                                });
                                if (uri) {
                                    fs.writeFileSync(uri.fsPath, payload.text || '', 'utf8');
                                    vscode.window.showInformationMessage(`Call Graph: сохранено в ${path.basename(uri.fsPath)}`);
                                }
                            } else if (fmt === 'png') {
                                const uri = await vscode.window.showSaveDialog({
                                    defaultUri: vscode.Uri.file(path.join(path.dirname(editor.document.fileName), `${base}.callgraph.png`)),
                                    filters: { 'PNG': ['png'] }
                                });
                                if (uri && typeof payload.dataUrl === 'string') {
                                    const m = payload.dataUrl.match(/^data:image\/png;base64,(.+)$/);
                                    if (m) {
                                        fs.writeFileSync(uri.fsPath, Buffer.from(m[1], 'base64'));
                                        vscode.window.showInformationMessage(`Call Graph: сохранено в ${path.basename(uri.fsPath)}`);
                                    }
                                }
                            }
                        } catch (err: any) {
                            vscode.window.showErrorMessage(`Call Graph export: ${err.message}`);
                        }
                    }
                },
                undefined,
                context.subscriptions,
            );

            // Live-refresh: при изменении исходного файла перезапрашиваем граф.
            // Debounce 1500ms — иначе при быстрой печати на большом файле
            // граф пересчитывается каждые полсекунды и подтормаживает UI.
            let refreshTimer: ReturnType<typeof setTimeout> | undefined;
            let refreshing = false;
            const changeListener = vscode.workspace.onDidChangeTextDocument((e) => {
                if (e.document.uri.toString() !== uri) return;
                if (refreshTimer) clearTimeout(refreshTimer);
                refreshTimer = setTimeout(async () => {
                    if (refreshing) return;  // пропускаем, если предыдущий ещё идёт
                    refreshing = true;
                    try {
                        const fresh: GraphData = await client.sendRequest('workspace/executeCommand', {
                            command: 'ide-navigator.callGraph',
                            arguments: [uri]
                        });
                        panel.webview.postMessage({ command: 'refresh', data: fresh });
                    } catch (_) { /* ignore refresh errors */ } finally {
                        refreshing = false;
                    }
                }, 1500);
            });
            panel.onDidDispose(() => {
                if (refreshTimer) clearTimeout(refreshTimer);
                changeListener.dispose();
            });
        }
    );

    context.subscriptions.push(showCallGraph);

    // Команда для открытия панели референсов.
    // Может быть вызвана двумя способами:
    //   1. Из CodeLens — сервер передаёт (uri, line, character)
    //   2. Из кнопки/курсора — аргументов нет, берём из activeTextEditor
    const showReferences = vscode.commands.registerCommand(
        'ide-navigator.showReferences',
        async (argUri?: string, argLine?: number, argChar?: number) => {
            let uri: string;
            let position: vscode.Position;
            let fileName: string;

            if (typeof argUri === 'string' && typeof argLine === 'number' && typeof argChar === 'number') {
                uri = argUri;
                position = new vscode.Position(argLine, argChar);
                fileName = path.basename(vscode.Uri.parse(argUri).fsPath);
            } else {
                const editor = vscode.window.activeTextEditor;
                if (!editor) {
                    vscode.window.showWarningMessage('Откройте файл для поиска референсов');
                    return;
                }
                uri = editor.document.uri.toString();
                position = editor.selection.active;
                fileName = path.basename(editor.document.fileName);
            }

            interface ReferenceItem {
                line: number;
                character: number;
                endCharacter: number;
                snippet: string;
            }
            interface ReferencesData {
                name: string;
                language: string;
                uri: string;
                refs: ReferenceItem[];
            }

            let data: ReferencesData | null;
            try {
                data = await client.sendRequest('workspace/executeCommand', {
                    command: 'ide-navigator.references',
                    arguments: [uri, position.line, position.character, true]
                });
            } catch (err: any) {
                vscode.window.showErrorMessage(`References: ошибка — ${err.message}`);
                return;
            }

            if (!data || data.refs.length === 0) {
                vscode.window.showInformationMessage('Референсы не найдены — поставьте курсор на идентификатор');
                return;
            }

            const panel = vscode.window.createWebviewPanel(
                'ideNavigatorReferences',
                `References: ${data.name}`,
                vscode.ViewColumn.Beside,
                { enableScripts: true }
            );

            panel.webview.html = getReferencesHtml(data, fileName);

            panel.webview.onDidReceiveMessage(
                async (message) => {
                    if (message.command === 'openReference' && data) {
                        const targetUri = vscode.Uri.parse(data.uri);
                        const pos = new vscode.Position(message.line, message.character);
                        const range = new vscode.Range(
                            pos,
                            new vscode.Position(message.line, message.endCharacter)
                        );
                        await vscode.window.showTextDocument(targetUri, {
                            selection: range,
                            viewColumn: vscode.ViewColumn.One
                        });
                    }
                },
                undefined,
                context.subscriptions
            );
        }
    );

    context.subscriptions.push(showReferences);
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) return undefined;
    return client.stop();
}


interface GraphNodeHtml {
    id: string;
    label: string;
    type?: string;
    line?: number;
    character?: number;
    endLine?: number;
    endCharacter?: number;
    complexity?: number;
}
interface GraphEdgeHtml {
    from: string;
    to: string;
    kind: 'call' | 'contains';
}

function getCallGraphHtml(
    data: { nodes: GraphNodeHtml[], edges: GraphEdgeHtml[] },
): string {
    const json = JSON.stringify(data);
    return `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'none'; script-src https://unpkg.com 'unsafe-inline'; style-src 'unsafe-inline';">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { overflow: hidden; background: #191919; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #ccc; }

        #graph { width: 100vw; height: 100vh; }

        /* Тулбар */
        #toolbar {
            position: fixed; top: 10px; left: 14px; right: 14px;
            background: rgba(30,30,30,0.9); border: 1px solid #333;
            border-radius: 8px; padding: 6px 10px;
            display: flex; align-items: center; gap: 6px;
            flex-wrap: wrap;
            backdrop-filter: blur(8px); z-index: 10;
            font-size: 11px;
        }
        #toolbar .group {
            display: flex; align-items: center; gap: 6px;
            white-space: nowrap;
        }
        #toolbar input[type="text"] {
            background: #262626; color: #ddd;
            border: 1px solid #3a3a3a; border-radius: 4px;
            padding: 3px 6px; font-size: 11px;
            width: 130px;
            font-family: inherit;
            outline: none;
        }
        #toolbar input[type="text"]:focus { border-color: #7f6df2; }
        #toolbar input[type="checkbox"] { accent-color: #7f6df2; margin: 0; }
        #toolbar label {
            display: flex; align-items: center; gap: 3px;
            color: #bbb; cursor: pointer; user-select: none;
        }
        #toolbar select {
            background: #262626; color: #ddd;
            border: 1px solid #3a3a3a; border-radius: 4px;
            padding: 2px 4px; font-size: 11px;
            font-family: inherit;
            outline: none;
        }
        #toolbar button {
            background: #262626; color: #ddd;
            border: 1px solid #3a3a3a; border-radius: 4px;
            padding: 2px 6px; font-size: 11px;
            font-family: inherit;
            cursor: pointer;
            outline: none;
            min-width: 22px;
        }
        #toolbar button:hover:not(:disabled) { border-color: #7f6df2; color: #fff; }
        #toolbar button:disabled { opacity: 0.35; cursor: default; }
        #toolbar .divider {
            width: 1px; background: #333; align-self: stretch;
            min-height: 16px;
        }
        #toolbar .hint {
            color: #666; font-size: 10px; font-style: italic;
        }

        /* Легенда */
        #legend {
            position: fixed; bottom: 14px; left: 14px;
            background: rgba(30,30,30,0.85); border: 1px solid #333;
            border-radius: 8px; padding: 10px 14px;
            display: flex; flex-direction: column; gap: 6px;
            backdrop-filter: blur(8px); z-index: 10;
        }
        #legend .row { display: flex; align-items: center; gap: 8px; }
        #legend .dot {
            width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
        }
        #legend .label { color: #aaa; font-size: 11px; }

        /* Статистика */
        #stats {
            position: fixed; bottom: 14px; right: 14px;
            color: #666; font-size: 11px; z-index: 10;
            background: rgba(30,30,30,0.85); border: 1px solid #333;
            border-radius: 6px; padding: 6px 10px;
        }

        #info {
            display: none; color: #555; text-align: center;
            padding-top: 40vh; font-size: 15px;
        }
    </style>
</head>
<body>
    <div id="toolbar">
        <span class="group">
            <button id="historyBack" title="Back (Alt+←)" disabled>←</button>
            <button id="historyFwd" title="Forward (Alt+→)" disabled>→</button>
            <div class="divider"></div>
            <input id="search" type="text" placeholder="Search…" spellcheck="false">
        </span>
        <div class="divider"></div>
        <span class="group">
            <label title="Collapse methods into their container classes">
                <input type="checkbox" id="groupByClass"> Group
            </label>
            <label title="Show gray edges (function/method calls)">
                <input type="checkbox" id="showCall" checked> Calls
            </label>
            <label title="Show red dashed edges (class → its methods)">
                <input type="checkbox" id="showContains" checked> Contains
            </label>
        </span>
        <div class="divider"></div>
        <span class="group">
            <label title="Dim functions with zero incoming calls (potential dead code)">
                <input type="checkbox" id="highlightUnused"> Unused
            </label>
            <label title="Highlight edges that are part of a strongly-connected cycle">
                <input type="checkbox" id="markCycles"> Cycles
            </label>
            <div class="divider"></div>
            <label title="Export current view">
                Export
                <select id="exportFmt">
                    <option value="">—</option>
                    <option value="png">PNG</option>
                    <option value="svg">SVG</option>
                    <option value="mermaid">Mermaid</option>
                    <option value="dot">DOT</option>
                </select>
            </label>
        </span>
    </div>
    <div id="graph"></div>
    <div id="stats"></div>
    <div id="legend"></div>
    <div id="info">No call relationships found</div>
    <script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
    <script>
        let raw = ${json};
        const vscode = acquireVsCodeApi();

        /* ── Цвета по типу символа ── */
        const TYPE_COLORS = {
            'function':    { bg: '#7f6df2', border: '#9b8afb', glow: 'rgba(127,109,242,0.35)' },
            'method':      { bg: '#4aadff', border: '#6bc0ff', glow: 'rgba(74,173,255,0.35)' },
            'constructor': { bg: '#e5a33a', border: '#f0bd5e', glow: 'rgba(229,163,58,0.35)' },
            'class':       { bg: '#e06c75', border: '#f28b8b', glow: 'rgba(224,108,117,0.35)' },
            'interface':   { bg: '#56b6c2', border: '#7fcfd8', glow: 'rgba(86,182,194,0.35)' },
            'struct':      { bg: '#d19a66', border: '#e4b882', glow: 'rgba(209,154,102,0.35)' },
        };
        const DEFAULT_COLOR = TYPE_COLORS.function;

        /* ── Индекс raw-данных ── */
        const nodeById = {};
        raw.nodes.forEach(n => { nodeById[n.id] = n; });

        /* Принадлежность методов классам (из contains-рёбер).
           Один и тот же метод по имени может принадлежать НЕСКОЛЬКИМ классам
           (например, у половины классов в файле есть свой __init__). Храним
           отношение как мапу классов в множество методов, чтобы счётчик
           "Group by class" не терял методы из-за коллизий имён. */
        const classToMethods = {}; /* className → Set<methodName> */
        const methodToClass  = {}; /* methodName → первая встреченная class (для collapse) */
        raw.edges.filter(e => e.kind === 'contains').forEach(e => {
            if (!classToMethods[e.from]) classToMethods[e.from] = new Set();
            classToMethods[e.from].add(e.to);
            if (!(e.to in methodToClass)) {
                methodToClass[e.to] = e.from;
            }
        });
        function methodCountOf(clsId) {
            return classToMethods[clsId] ? classToMethods[clsId].size : 0;
        }

        /* Степень (по всем raw-рёбрам, стабильно при фильтрах) — для размера узла */
        const degree = {};
        raw.nodes.forEach(n => { degree[n.id] = 0; });
        raw.edges.forEach(e => {
            degree[e.from] = (degree[e.from] || 0) + 1;
            degree[e.to]   = (degree[e.to]   || 0) + 1;
        });
        const maxDeg = Math.max(1, ...Object.values(degree));

        /* ── Состояние тулбара ── */
        const state = {
            search: '',
            groupByClass: false,
            showCall: true,
            showContains: true,
            highlightUnused: false,
            markCycles: false,
            selectedNode: null,
        };

        /* История выделений для back/forward — как в браузере.
           push() обрезает forward-стек; goBack/goForward не пушат. */
        const history = { back: [], forward: [] };
        function historyPush(nodeId) {
            if (nodeId == null) return;
            if (history.back.length && history.back[history.back.length - 1] === nodeId) return;
            history.back.push(nodeId);
            history.forward.length = 0;
            updateHistoryButtons();
        }
        function updateHistoryButtons() {
            document.getElementById('historyBack').disabled = history.back.length < 2;
            document.getElementById('historyFwd').disabled  = history.forward.length === 0;
        }

        /* ── Dead-code: узлы без входящих call-рёбер ── */
        /* Классы/интерфейсы/структуры исключаем — они "контейнеры", у них
           нет входящих call по определению. */
        const NON_CALLABLE_TYPES = new Set(['class', 'interface', 'struct']);
        function computeUnused(nodes, edges) {
            const incoming = {};
            nodes.forEach(n => { incoming[n.id] = 0; });
            edges.forEach(e => {
                if (e.kind !== 'call') return;
                if (incoming[e.to] !== undefined) incoming[e.to] += 1;
            });
            const unused = new Set();
            nodes.forEach(n => {
                if (NON_CALLABLE_TYPES.has(n.type)) return;
                if ((incoming[n.id] || 0) === 0) unused.add(n.id);
            });
            return unused;
        }

        /* ── Tarjan SCC: рёбра, оба конца которых лежат в одном SCC размером ≥ 2
           (или self-loop) — "cycle edges". */
        function computeCycleEdges(nodes, edges) {
            const callEdges = edges.filter(e => e.kind === 'call');
            const adj = {};
            nodes.forEach(n => { adj[n.id] = []; });
            callEdges.forEach(e => {
                if (adj[e.from]) adj[e.from].push(e.to);
            });
            const index = {};
            const lowlink = {};
            const onStack = {};
            const stack = [];
            const sccOf = {};
            let idx = 0;
            let sccId = 0;

            function strongconnect(v) {
                /* Итеративный Tarjan (стек вызовов может взорваться на больших графах) */
                const work = [[v, 0]];
                index[v] = idx; lowlink[v] = idx; idx += 1;
                stack.push(v); onStack[v] = true;

                while (work.length) {
                    const top = work[work.length - 1];
                    const [node, i] = top;
                    const neighbors = adj[node] || [];
                    if (i < neighbors.length) {
                        top[1] = i + 1;
                        const w = neighbors[i];
                        if (index[w] === undefined) {
                            index[w] = idx; lowlink[w] = idx; idx += 1;
                            stack.push(w); onStack[w] = true;
                            work.push([w, 0]);
                        } else if (onStack[w]) {
                            lowlink[node] = Math.min(lowlink[node], index[w]);
                        }
                    } else {
                        if (lowlink[node] === index[node]) {
                            const comp = [];
                            let w;
                            do {
                                w = stack.pop();
                                onStack[w] = false;
                                sccOf[w] = sccId;
                                comp.push(w);
                            } while (w !== node);
                            sccId += 1;
                        }
                        work.pop();
                        if (work.length) {
                            const parent = work[work.length - 1][0];
                            lowlink[parent] = Math.min(lowlink[parent], lowlink[node]);
                        }
                    }
                }
            }

            nodes.forEach(n => {
                if (index[n.id] === undefined) strongconnect(n.id);
            });

            /* размер SCC */
            const sccSize = {};
            Object.values(sccOf).forEach(id => { sccSize[id] = (sccSize[id] || 0) + 1; });

            const cycleKeys = new Set();
            callEdges.forEach(e => {
                if (e.from === e.to) { cycleKeys.add(e.kind + '|' + e.from + '|' + e.to); return; }
                if (sccOf[e.from] !== undefined && sccOf[e.from] === sccOf[e.to] && sccSize[sccOf[e.from]] >= 2) {
                    cycleKeys.add(e.kind + '|' + e.from + '|' + e.to);
                }
            });
            return cycleKeys;
        }

        /* ── Пайплайн фильтрации: raw → processed nodes/edges ── */
        function buildGraph() {
            let nodes = raw.nodes.slice();
            let edges = raw.edges.map(e => ({ from: e.from, to: e.to, kind: e.kind }));

            /* 1. Group by class: спрятать методы, перенаправить их call-рёбра на класс */
            if (state.groupByClass) {
                const hidden = new Set(Object.keys(methodToClass));
                const redirected = [];
                edges.forEach(e => {
                    if (e.kind === 'contains') return;
                    const from = hidden.has(e.from) ? methodToClass[e.from] : e.from;
                    const to   = hidden.has(e.to)   ? methodToClass[e.to]   : e.to;
                    if (from === to) return;
                    redirected.push({ from, to, kind: e.kind });
                });
                /* Дедуп перенаправленных рёбер */
                const seen = new Set();
                edges = redirected.filter(e => {
                    const k = e.kind + '|' + e.from + '|' + e.to;
                    if (seen.has(k)) return false;
                    seen.add(k);
                    return true;
                });
                nodes = nodes.filter(n => !hidden.has(n.id));
            }

            return { nodes, edges };
        }

        /* ── Сборка vis.DataSet из отфильтрованных nodes/edges ── */
        let lastBuilt = null; /* последний buildDataSets-снимок — для экспорта */
        function buildDataSets() {
            const built = buildGraph();
            const nodes = built.nodes;
            /* Фильтр видимости рёбер по kind (применяем ПОСЛЕ основного pipeline,
               чтобы group-by-class/depth продолжали работать по полному графу) */
            const edges = built.edges.filter(e => {
                if (e.kind === 'call' && !state.showCall) return false;
                if (e.kind === 'contains' && !state.showContains) return false;
                return true;
            });
            const q = state.search.trim().toLowerCase();
            const unused = state.highlightUnused ? computeUnused(nodes, edges) : null;
            const cycleKeys = state.markCycles ? computeCycleEdges(nodes, edges) : null;

            const nodeDS = new vis.DataSet(nodes.map(n => {
                const c = TYPE_COLORS[n.type] || DEFAULT_COLOR;
                const d = degree[n.id] || 0;
                const baseSize = 16;
                const size = baseSize + (d / maxDeg) * 24;
                const matches = q.length > 0 && n.label.toLowerCase().indexOf(q) !== -1;
                const dimmed  = q.length > 0 && !matches;
                const isUnused = unused && unused.has(n.id);

                let label = n.label;
                const mc = methodCountOf(n.id);
                if (state.groupByClass && mc > 0) {
                    label = n.label + ' (' + mc + ')';
                }

                /* Tooltip: type: name (N connections) + complexity if available */
                let title = n.type + ': ' + n.label + ' (' + d + ' connections)';
                if (typeof n.complexity === 'number') {
                    title += ' · cyclomatic=' + n.complexity;
                }
                if (isUnused) title += ' · unused';

                const bg = matches ? '#fff48a'
                         : isUnused ? '#3a3a3a'
                         : c.bg;
                const border = matches ? '#ffd400'
                             : isUnused ? '#555'
                             : c.border;

                return {
                    id: n.id,
                    label: label,
                    shape: 'dot',
                    size: matches ? size * 1.25 : size,
                    color: {
                        background: bg,
                        border: border,
                        highlight: { background: c.border, border: '#fff' },
                        hover:     { background: c.border, border: '#fff' }
                    },
                    font: {
                        color: dimmed ? '#444' : (isUnused ? '#666' : '#ccc'),
                        size: 12,
                        face: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                        strokeWidth: 3, strokeColor: '#191919'
                    },
                    opacity: dimmed ? 0.25 : (isUnused ? 0.4 : 1),
                    borderWidth: matches ? 3 : 1.5,
                    borderWidthSelected: 3,
                    shadow: { enabled: !isUnused, color: c.glow, size: 12, x: 0, y: 0 },
                    title: title
                };
            }));

            const edgeDS = new vis.DataSet(edges.map((e, i) => {
                const key = e.kind + '|' + e.from + '|' + e.to;
                const isCycle = cycleKeys && cycleKeys.has(key);
                let color;
                if (isCycle) {
                    color = { color: '#ff5c5c', highlight: '#ff8a8a', hover: '#ff7070' };
                } else if (e.kind === 'contains') {
                    color = { color: 'rgba(224,108,117,0.22)', highlight: 'rgba(224,108,117,0.7)', hover: 'rgba(224,108,117,0.5)' };
                } else {
                    color = { color: 'rgba(255,255,255,0.08)', highlight: 'rgba(255,255,255,0.4)', hover: 'rgba(255,255,255,0.25)' };
                }
                return {
                    id: i,
                    from: e.from,
                    to: e.to,
                    arrows: { to: { enabled: true, scaleFactor: isCycle ? 0.9 : 0.5, type: 'arrow' } },
                    color: color,
                    dashes: e.kind === 'contains',
                    width: isCycle ? 2.4 : 1,
                    hoverWidth: 0.8,
                    selectionWidth: 1.2,
                    smooth: { enabled: true, type: 'continuous', roundness: 0.5 },
                    title: isCycle ? 'cycle' : undefined
                };
            }));

            lastBuilt = { nodes: nodes, edges: edges };
            return { nodes: nodeDS, edges: edgeDS, rawCount: { nodes: nodes.length, edges: edges.length } };
        }

        /* ── Обновление stats ── */
        function updateStats(rawCount) {
            document.getElementById('stats').textContent =
                rawCount.nodes + ' symbols \\u00b7 ' + rawCount.edges + ' edges';
        }

        if (raw.nodes.length === 0) {
            document.getElementById('graph').style.display = 'none';
            document.getElementById('legend').style.display = 'none';
            document.getElementById('toolbar').style.display = 'none';
            document.getElementById('stats').style.display = 'none';
            document.getElementById('info').style.display = 'block';
        } else {

            /* ── Сеть ── */
            const container = document.getElementById('graph');
            const initial = buildDataSets();
            updateStats(initial.rawCount);

            const network = new vis.Network(
                container,
                { nodes: initial.nodes, edges: initial.edges },
                {
                    layout: { improvedLayout: true },
                    physics: {
                        enabled: true,
                        solver: 'forceAtlas2Based',
                        forceAtlas2Based: {
                            gravitationalConstant: -40,
                            centralGravity: 0.008,
                            springLength: 160,
                            springConstant: 0.02,
                            damping: 0.85,
                            avoidOverlap: 0.5
                        },
                        stabilization: { iterations: 200, fit: true },
                        maxVelocity: 30,
                        minVelocity: 0.3
                    },
                    interaction: {
                        hover: true, tooltipDelay: 200,
                        zoomView: true, dragView: true, dragNodes: true,
                        multiselect: false
                    }
                }
            );

            /* Остановить физику после стабилизации, но оставить drag */
            network.on('stabilizationIterationsDone', () => {
                network.setOptions({ physics: { enabled: false } });
            });

            /* При перетаскивании — временно включить физику */
            network.on('dragEnd', (params) => {
                if (params.nodes.length > 0) {
                    network.setOptions({ physics: { enabled: true, stabilization: { iterations: 50 } } });
                    setTimeout(() => network.setOptions({ physics: { enabled: false } }), 1500);
                }
            });

            /* Открыть исходник для узла (click + modifier / dblclick) */
            function navigateToNode(nodeId) {
                const n = nodeById[nodeId];
                if (!n || typeof n.line !== 'number') return;
                vscode.postMessage({
                    command: 'openNode',
                    line: n.line,
                    character: n.character || 0,
                    endCharacter: n.endCharacter || n.character || 0,
                });
            }

            /* Click: запоминаем выделение + модификатор = открыть файл */
            network.on('click', (params) => {
                if (params.nodes.length === 0) {
                    state.selectedNode = null;
                    return;
                }
                const nodeId = params.nodes[0];
                state.selectedNode = nodeId;
                historyPush(nodeId);
                const src = params.event && params.event.srcEvent;
                const withMod = src && (src.ctrlKey || src.metaKey || src.shiftKey || src.altKey);
                if (withMod) {
                    navigateToNode(nodeId);
                }
            });

            /* Double-click: всегда открывает файл (без модификатора) */
            network.on('doubleClick', (params) => {
                if (params.nodes.length > 0) {
                    navigateToNode(params.nodes[0]);
                }
            });

            /* ── Перерендер без пересоздания сети ── */
            function rerender() {
                const ds = buildDataSets();
                network.setData({ nodes: ds.nodes, edges: ds.edges });
                updateStats(ds.rawCount);
                /* После setData физика запустится заново — остановим через секунду */
                network.setOptions({ physics: { enabled: true, stabilization: { iterations: 50 } } });
                setTimeout(() => network.setOptions({ physics: { enabled: false } }), 1200);
            }

            /* ── Обработчики тулбара ── */
            const searchEl = document.getElementById('search');
            let searchTimer = null;
            searchEl.addEventListener('input', () => {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(() => {
                    state.search = searchEl.value;
                    rerender();
                }, 120);
            });

            document.getElementById('groupByClass').addEventListener('change', (e) => {
                state.groupByClass = e.target.checked;
                /* При группировке selectedNode может исчезнуть */
                if (state.selectedNode && methodToClass[state.selectedNode] && state.groupByClass) {
                    state.selectedNode = methodToClass[state.selectedNode];
                }
                rerender();
            });

            document.getElementById('showCall').addEventListener('change', (e) => {
                state.showCall = e.target.checked;
                rerender();
            });

            document.getElementById('showContains').addEventListener('change', (e) => {
                state.showContains = e.target.checked;
                rerender();
            });

            document.getElementById('highlightUnused').addEventListener('change', (e) => {
                state.highlightUnused = e.target.checked;
                rerender();
            });

            document.getElementById('markCycles').addEventListener('change', (e) => {
                state.markCycles = e.target.checked;
                rerender();
            });

            /* ── История back/forward ── */
            function focusFromHistory(nodeId) {
                state.selectedNode = nodeId;
                network.selectNodes([nodeId], false);
                try { network.focus(nodeId, { scale: 1.1, animation: { duration: 300, easingFunction: 'easeInOutQuad' } }); } catch (_) {}
                updateHistoryButtons();
            }
            document.getElementById('historyBack').addEventListener('click', () => {
                if (history.back.length < 2) return;
                const cur = history.back.pop();
                history.forward.push(cur);
                const prev = history.back[history.back.length - 1];
                focusFromHistory(prev);
            });
            document.getElementById('historyFwd').addEventListener('click', () => {
                if (history.forward.length === 0) return;
                const next = history.forward.pop();
                history.back.push(next);
                focusFromHistory(next);
            });
            document.addEventListener('keydown', (ev) => {
                if (!ev.altKey) return;
                if (ev.key === 'ArrowLeft') {
                    ev.preventDefault();
                    document.getElementById('historyBack').click();
                } else if (ev.key === 'ArrowRight') {
                    ev.preventDefault();
                    document.getElementById('historyFwd').click();
                }
            });

            /* ── Export ── */
            function buildMermaid() {
                const lines = ['graph LR'];
                const safeId = {};
                (lastBuilt ? lastBuilt.nodes : raw.nodes).forEach((n, i) => {
                    safeId[n.id] = 'n' + i;
                    const lbl = n.label.replace(/"/g, '\\\\"');
                    lines.push('    ' + safeId[n.id] + '["' + lbl + '"]');
                });
                (lastBuilt ? lastBuilt.edges : raw.edges).forEach(e => {
                    const a = safeId[e.from], b = safeId[e.to];
                    if (!a || !b) return;
                    lines.push('    ' + a + (e.kind === 'contains' ? ' -.-> ' : ' --> ') + b);
                });
                return lines.join('\\n');
            }
            function buildDot() {
                const lines = ['digraph G {', '    bgcolor="#191919";', '    node [fontcolor="#ccc", color="#7f6df2", style=filled, fillcolor="#262626"];', '    edge [color="#888"];'];
                const safeId = {};
                (lastBuilt ? lastBuilt.nodes : raw.nodes).forEach((n, i) => {
                    safeId[n.id] = 'n' + i;
                    const lbl = n.label.replace(/"/g, '\\\\"');
                    lines.push('    ' + safeId[n.id] + ' [label="' + lbl + '"];');
                });
                (lastBuilt ? lastBuilt.edges : raw.edges).forEach(e => {
                    const a = safeId[e.from], b = safeId[e.to];
                    if (!a || !b) return;
                    const style = e.kind === 'contains' ? ' [style=dashed, color="#e06c75"]' : '';
                    lines.push('    ' + a + ' -> ' + b + style + ';');
                });
                lines.push('}');
                return lines.join('\\n');
            }
            function buildSvg() {
                const positions = network.getPositions();
                let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
                Object.values(positions).forEach(p => {
                    if (p.x < minX) minX = p.x;
                    if (p.y < minY) minY = p.y;
                    if (p.x > maxX) maxX = p.x;
                    if (p.y > maxY) maxY = p.y;
                });
                const pad = 60;
                minX -= pad; minY -= pad; maxX += pad; maxY += pad;
                const w = Math.max(1, maxX - minX), h = Math.max(1, maxY - minY);
                const parts = [
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + minX + ' ' + minY + ' ' + w + ' ' + h + '" width="' + Math.round(w) + '" height="' + Math.round(h) + '">',
                    '<rect x="' + minX + '" y="' + minY + '" width="' + w + '" height="' + h + '" fill="#191919"/>',
                    '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#888"/></marker></defs>'
                ];
                const built = lastBuilt || { nodes: raw.nodes, edges: raw.edges };
                built.edges.forEach(e => {
                    const a = positions[e.from], b = positions[e.to];
                    if (!a || !b) return;
                    const stroke = e.kind === 'contains' ? '#e06c75' : '#888';
                    const dash = e.kind === 'contains' ? ' stroke-dasharray="4 4"' : '';
                    parts.push('<line x1="' + a.x + '" y1="' + a.y + '" x2="' + b.x + '" y2="' + b.y + '" stroke="' + stroke + '" stroke-width="1.2"' + dash + ' marker-end="url(#arr)"/>');
                });
                built.nodes.forEach(n => {
                    const p = positions[n.id];
                    if (!p) return;
                    const c = TYPE_COLORS[n.type] || DEFAULT_COLOR;
                    const lbl = (n.label || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    parts.push('<circle cx="' + p.x + '" cy="' + p.y + '" r="12" fill="' + c.bg + '" stroke="' + c.border + '" stroke-width="1.5"/>');
                    parts.push('<text x="' + p.x + '" y="' + (p.y + 26) + '" fill="#ccc" font-family="sans-serif" font-size="11" text-anchor="middle">' + lbl + '</text>');
                });
                parts.push('</svg>');
                return parts.join('');
            }
            function buildPng() {
                /* vis.js рендерит в <canvas> — достаём dataURL */
                const canvas = container.querySelector('canvas');
                if (!canvas) return null;
                return canvas.toDataURL('image/png');
            }
            document.getElementById('exportFmt').addEventListener('change', (ev) => {
                const fmt = ev.target.value;
                ev.target.value = '';
                if (!fmt) return;
                let payload;
                if (fmt === 'mermaid') payload = { format: 'mermaid', text: buildMermaid() };
                else if (fmt === 'dot') payload = { format: 'dot', text: buildDot() };
                else if (fmt === 'svg') payload = { format: 'svg', text: buildSvg() };
                else if (fmt === 'png') {
                    const dataUrl = buildPng();
                    if (!dataUrl) return;
                    payload = { format: 'png', dataUrl: dataUrl };
                }
                vscode.postMessage({ command: 'exportGraph', payload: payload });
            });

            /* ── Легенда (только whitelisted типы, без innerHTML для пользовательских данных) ── */
            const usedTypes = new Set(raw.nodes.map(n => n.type));
            const legendEl = document.getElementById('legend');
            const typeLabels = {
                'function': 'Function', 'method': 'Method', 'constructor': 'Constructor',
                'class': 'Class', 'interface': 'Interface', 'struct': 'Struct'
            };
            usedTypes.forEach(t => {
                if (!(t in typeLabels)) return;
                const c = TYPE_COLORS[t] || DEFAULT_COLOR;
                const row = document.createElement('div');
                row.className = 'row';

                const dot = document.createElement('span');
                dot.className = 'dot';
                dot.style.background = c.bg;
                dot.style.boxShadow = '0 0 6px ' + c.glow;

                const label = document.createElement('span');
                label.className = 'label';
                label.textContent = typeLabels[t];

                row.appendChild(dot);
                row.appendChild(label);
                legendEl.appendChild(row);
            });

            /* ── Live-refresh: расширение шлёт новый граф при изменении файла ── */
            window.addEventListener('message', (event) => {
                const msg = event.data;
                if (msg && msg.command === 'refresh' && msg.data) {
                    raw = msg.data;
                    /* Обновить индексы */
                    Object.keys(nodeById).forEach(k => delete nodeById[k]);
                    raw.nodes.forEach(n => { nodeById[n.id] = n; });
                    /* Пересчитать degree */
                    Object.keys(degree).forEach(k => delete degree[k]);
                    raw.nodes.forEach(n => { degree[n.id] = 0; });
                    raw.edges.forEach(e => {
                        degree[e.from] = (degree[e.from] || 0) + 1;
                        degree[e.to]   = (degree[e.to]   || 0) + 1;
                    });
                    /* Обновить classToMethods / methodToClass */
                    Object.keys(classToMethods).forEach(k => delete classToMethods[k]);
                    Object.keys(methodToClass).forEach(k => delete methodToClass[k]);
                    raw.edges.filter(e => e.kind === 'contains').forEach(e => {
                        if (!classToMethods[e.from]) classToMethods[e.from] = new Set();
                        classToMethods[e.from].add(e.to);
                        if (!(e.to in methodToClass)) methodToClass[e.to] = e.from;
                    });
                    rerender();
                }
            });
        }
    </script>
</body>
</html>`;
}


function escapeHtml(s: string): string {
    return s.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
}


function getReferencesHtml(
    data: {
        name: string,
        language: string,
        uri: string,
        refs: {line: number, character: number, endCharacter: number, snippet: string}[]
    },
    fileName: string,
): string {
    const json = JSON.stringify(data);
    const name = escapeHtml(data.name);
    const file = escapeHtml(fileName);
    const count = data.refs.length;
    return `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'none'; script-src https://unpkg.com 'unsafe-inline'; style-src https://unpkg.com 'unsafe-inline';">
    <link rel="stylesheet" href="https://unpkg.com/@highlightjs/cdn-assets@11.9.0/styles/atom-one-dark.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #191919;
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            padding: 24px 32px;
            overflow-x: hidden;
        }

        .header {
            display: flex;
            align-items: baseline;
            gap: 12px;
            padding-bottom: 16px;
            border-bottom: 1px solid #2a2a2a;
            margin-bottom: 20px;
        }
        .header .title {
            font-size: 18px;
            font-weight: 500;
            color: #e0e0e0;
        }
        .header .name {
            color: #7f6df2;
            font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
            font-size: 16px;
        }
        .header .count {
            color: #666;
            font-size: 13px;
        }
        .header .file {
            color: #555;
            font-size: 12px;
            margin-left: auto;
        }

        .ref {
            display: flex;
            align-items: flex-start;
            gap: 16px;
            padding: 10px 12px;
            margin: 2px 0;
            border-radius: 6px;
            cursor: pointer;
            border-left: 2px solid transparent;
            transition: background 0.12s, border-color 0.12s;
        }
        .ref:hover {
            background: rgba(127,109,242,0.08);
            border-left-color: #7f6df2;
        }
        .ref .line-num {
            color: #555;
            font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
            font-size: 12px;
            min-width: 40px;
            text-align: right;
            padding-top: 2px;
            flex-shrink: 0;
        }
        .ref .code {
            flex: 1;
            font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
            overflow-x: auto;
            white-space: pre;
            background: transparent !important;
            padding: 0 !important;
        }
    </style>
</head>
<body>
    <div class="header">
        <span class="title">References</span>
        <span class="name">${name}</span>
        <span class="count">${count}</span>
        <span class="file">${file}</span>
    </div>
    <div id="list"></div>
    <script src="https://unpkg.com/@highlightjs/cdn-assets@11.9.0/highlight.min.js"></script>
    <script>
        const data = ${json};
        const vscode = acquireVsCodeApi();
        const list = document.getElementById('list');

        function escapeHtml(s) {
            return s.replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;');
        }

        data.refs.forEach(ref => {
            const div = document.createElement('div');
            div.className = 'ref';

            let highlighted;
            try {
                highlighted = hljs.highlight(ref.snippet, {
                    language: data.language,
                    ignoreIllegals: true
                }).value;
            } catch (e) {
                highlighted = escapeHtml(ref.snippet);
            }

            div.innerHTML =
                '<span class="line-num">' + (ref.line + 1) + '</span>' +
                '<pre class="code hljs">' + highlighted + '</pre>';

            div.addEventListener('click', () => {
                vscode.postMessage({
                    command: 'openReference',
                    line: ref.line,
                    character: ref.character,
                    endCharacter: ref.endCharacter
                });
            });

            list.appendChild(div);
        });
    </script>
</body>
</html>`;
}
