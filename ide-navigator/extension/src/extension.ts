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


function getCallGraphHtml(data: { nodes: {id: string, label: string}[], edges: {from: string, to: string}[] }): string {
    const json = JSON.stringify(data);
    return `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'none'; script-src https://unpkg.com 'unsafe-inline'; style-src 'unsafe-inline';">
    <style>
        body { margin: 0; padding: 0; overflow: hidden; background: #1e1e1e; }
        #graph { width: 100vw; height: 100vh; }
        #info {
            display: none; color: #999; text-align: center;
            margin-top: 40vh; font-family: sans-serif; font-size: 16px;
        }
    </style>
</head>
<body>
    <div id="graph"></div>
    <div id="info">Нет вызовов между функциями</div>
    <script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
    <script>
        const raw = ${json};

        if (raw.edges.length === 0) {
            document.getElementById('graph').style.display = 'none';
            document.getElementById('info').style.display = 'block';
        } else {
            const nodes = new vis.DataSet(raw.nodes.map(n => ({
                id: n.id,
                label: n.label,
                shape: 'box',
                color: {
                    background: '#264f78', border: '#3794ff',
                    highlight: { background: '#3794ff', border: '#75beff' }
                },
                font: { color: '#ffffff', size: 14, face: 'Consolas, monospace' }
            })));

            const edges = new vis.DataSet(raw.edges.map((e, i) => ({
                id: i, from: e.from, to: e.to,
                arrows: 'to',
                color: { color: '#555', highlight: '#3794ff' },
                width: 2
            })));

            const container = document.getElementById('graph');
            new vis.Network(container, { nodes, edges }, {
                layout: {
                    hierarchical: {
                        direction: 'UD',
                        sortMethod: 'directed',
                        levelSeparation: 120,
                        nodeSpacing: 180
                    }
                },
                physics: false,
                interaction: { hover: true, zoomView: true, dragView: true }
            });
        }
    </script>
</body>
</html>`;
}
