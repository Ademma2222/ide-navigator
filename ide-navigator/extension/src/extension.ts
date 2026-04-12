import * as path from 'path';
import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions
} from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: vscode.ExtensionContext) {
    // Путь к Python серверу
    const serverPath = context.asAbsolutePath(
        path.join('..', 'server', 'server.py')
    );

    // Найти python в venv (Windows: Scripts/python.exe, Mac/Linux: bin/python)
    const isWindows = process.platform === 'win32';
    const pythonPath = context.asAbsolutePath(
        isWindows
            ? path.join('..', 'server', 'venv', 'Scripts', 'python.exe')
            : path.join('..', 'server', 'venv', 'bin', 'python')
    );

    console.log('IDE Navigator: python =', pythonPath);
    console.log('IDE Navigator: server =', serverPath);

    // Настройки запуска сервера (внешний процесс — без TransportKind)
    const serverOptions: ServerOptions = {
        command: pythonPath,
        args: [serverPath]
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
        ]
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
        vscode.window.showInformationMessage('IDE Navigator запущен');
    }).catch((err) => {
        console.error('IDE Navigator: ошибка запуска сервера', err);
        vscode.window.showErrorMessage(`IDE Navigator: ошибка — ${err.message}`);
    });

    // Команда для открытия графа вызовов
    const showCallGraph = vscode.commands.registerCommand(
        'ide-navigator.showCallGraph',
        async () => {
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

            /* ── Легенда ── */
            const usedTypes = new Set(raw.nodes.map(n => n.type));
            const legendEl = document.getElementById('legend');
            const typeLabels = {
                'function': 'Function', 'method': 'Method', 'constructor': 'Constructor',
                'class': 'Class', 'interface': 'Interface', 'struct': 'Struct'
            };
            usedTypes.forEach(t => {
                const c = TYPE_COLORS[t] || DEFAULT_COLOR;
                const row = document.createElement('div');
                row.className = 'row';
                row.innerHTML = '<span class="dot" style="background:' + c.bg + ';box-shadow:0 0 6px ' + c.glow + '"></span>'
                    + '<span class="label">' + (typeLabels[t] || t) + '</span>';
                legendEl.appendChild(row);
            });
        }
    </script>
</body>
</html>`;
}
