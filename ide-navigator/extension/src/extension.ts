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

            const uri = editor.document.uri.toString();

            let graphData: { nodes: {id: string, label: string}[], edges: {from: string, to: string}[] };
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
        }
    );

    context.subscriptions.push(showCallGraph);

    // Команда для открытия панели референсов
    const showReferences = vscode.commands.registerCommand(
        'ide-navigator.showReferences',
        async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('Откройте файл для поиска референсов');
                return;
            }

            const uri = editor.document.uri.toString();
            const position = editor.selection.active;

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

            panel.webview.html = getReferencesHtml(data, path.basename(editor.document.fileName));

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


function getCallGraphHtml(
    data: { nodes: {id: string, label: string, type?: string}[], edges: {from: string, to: string}[] },
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
        body { overflow: hidden; background: #191919; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

        #graph { width: 100vw; height: 100vh; }

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
            position: fixed; top: 10px; right: 14px;
            color: #555; font-size: 11px; z-index: 10;
        }

        #info {
            display: none; color: #555; text-align: center;
            padding-top: 40vh; font-size: 15px;
        }
    </style>
</head>
<body>
    <div id="graph"></div>
    <div id="stats"></div>
    <div id="legend"></div>
    <div id="info">No call relationships found</div>
    <script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
    <script>
        const raw = ${json};

        /* ── Цвета по типу символа ── */
        const TYPE_COLORS = {
            'function':    { bg: '#7f6df2', border: '#9b8afb', glow: 'rgba(127,109,242,0.35)' },
            'method':      { bg: '#4aadff', border: '#6bc0ff', glow: 'rgba(74,173,255,0.35)' },
            'constructor': { bg: '#e5a33a', border: '#f0bd5e', glow: 'rgba(229,163,58,0.35)' },
            'class':       { bg: '#e06c75', border: '#f28b8b', glow: 'rgba(224,108,117,0.35)' },
            'interface':   { bg: '#56b6c2', border: '#7fcfd8', glow: 'rgba(86,182,194,0.35)' },
            'struct':      { bg: '#d19a66', border: '#e4b882', glow: 'rgba(209,154,102,0.35)' },
        };
        const DEFAULT_COLOR = { bg: '#7f6df2', border: '#9b8afb', glow: 'rgba(127,109,242,0.35)' };

        /* ── Подсчёт связей для размера ── */
        const degree = {};
        raw.nodes.forEach(n => { degree[n.id] = 0; });
        raw.edges.forEach(e => {
            degree[e.from] = (degree[e.from] || 0) + 1;
            degree[e.to]   = (degree[e.to]   || 0) + 1;
        });
        const maxDeg = Math.max(1, ...Object.values(degree));

        /* ── Статистика ── */
        document.getElementById('stats').textContent =
            raw.nodes.length + ' symbols \\u00b7 ' + raw.edges.length + ' calls';

        if (raw.nodes.length === 0) {
            document.getElementById('graph').style.display = 'none';
            document.getElementById('legend').style.display = 'none';
            document.getElementById('info').style.display = 'block';
        } else {

            /* ── Узлы ── */
            const nodes = new vis.DataSet(raw.nodes.map(n => {
                const c = TYPE_COLORS[n.type] || DEFAULT_COLOR;
                const d = degree[n.id] || 0;
                const baseSize = 16;
                const size = baseSize + (d / maxDeg) * 24;

                return {
                    id: n.id,
                    label: n.label,
                    shape: 'dot',
                    size: size,
                    color: {
                        background: c.bg, border: c.border,
                        highlight: { background: c.border, border: '#fff' },
                        hover:     { background: c.border, border: '#fff' }
                    },
                    font: {
                        color: '#ccc', size: 12,
                        face: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                        strokeWidth: 3, strokeColor: '#191919'
                    },
                    borderWidth: 1.5,
                    borderWidthSelected: 2.5,
                    shadow: { enabled: true, color: c.glow, size: 12, x: 0, y: 0 },
                    title: n.type + ': ' + n.label + ' (' + d + ' connections)'
                };
            }));

            /* ── Рёбра ── */
            const edges = new vis.DataSet(raw.edges.map((e, i) => ({
                id: i, from: e.from, to: e.to,
                arrows: { to: { enabled: true, scaleFactor: 0.5, type: 'arrow' } },
                color: { color: 'rgba(255,255,255,0.08)', highlight: 'rgba(255,255,255,0.4)', hover: 'rgba(255,255,255,0.25)' },
                width: 1,
                hoverWidth: 0.8,
                selectionWidth: 1.2,
                smooth: { enabled: true, type: 'continuous', roundness: 0.5 }
            })));

            /* ── Сеть ── */
            const container = document.getElementById('graph');
            const network = new vis.Network(container, { nodes, edges }, {
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
                    zoomView: true, dragView: true, dragNodes: true
                }
            });

            /* Остановить физику после стабилизации, но оставить drag */
            network.on('stabilizationIterationsDone', () => {
                network.setOptions({ physics: { enabled: false } });
            });

            /* При перетаскивании — временно включить физику для перебалансировки */
            network.on('dragEnd', (params) => {
                if (params.nodes.length > 0) {
                    network.setOptions({ physics: { enabled: true, stabilization: { iterations: 50 } } });
                    setTimeout(() => network.setOptions({ physics: { enabled: false } }), 1500);
                }
            });

            /* ── Легенда (только whitelisted типы, без innerHTML для пользовательских данных) ── */
            const usedTypes = new Set(raw.nodes.map(n => n.type));
            const legendEl = document.getElementById('legend');
            const typeLabels = {
                'function': 'Function', 'method': 'Method', 'constructor': 'Constructor',
                'class': 'Class', 'interface': 'Interface', 'struct': 'Struct'
            };
            usedTypes.forEach(t => {
                /* Сервер уже отсанитизировал, но на клиенте тоже отфильтруем — defense in depth */
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
