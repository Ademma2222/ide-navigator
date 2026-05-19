import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions
} from 'vscode-languageclient/node';
import type {
    GraphData,
    CallGraphInbound,
    ReferencesData,
    ReferencesInbound,
} from './webview-protocol';

function renderWebview(
    panel: vscode.WebviewPanel,
    context: vscode.ExtensionContext,
    htmlFile: string,
    cssFile: string,
    jsFile: string,
): void {
    const mediaUri = (file: string) =>
        panel.webview.asWebviewUri(
            vscode.Uri.joinPath(context.extensionUri, 'media', file)
        );
    const template = fs.readFileSync(
        path.join(context.extensionPath, 'media', htmlFile),
        'utf-8'
    );
    panel.webview.html = template
        .replace(/__CSP_SOURCE__/g, panel.webview.cspSource)
        .replace(/__CSS_URI__/g, mediaUri(cssFile).toString())
        .replace(/__JS_URI__/g, mediaUri(jsFile).toString())
        .replace(/__VIS_URI__/g, mediaUri('vis-network.min.js').toString())
        .replace(/__HL_JS_URI__/g, mediaUri('highlight.min.js').toString())
        .replace(/__HL_CSS_URI__/g, mediaUri('atom-one-dark.min.css').toString());
}

let client: LanguageClient;
let statusBar: vscode.StatusBarItem;

function setStatus(text: string, tooltip?: string) {
    statusBar.text = `$(symbol-namespace) ${text}`;
    statusBar.tooltip = tooltip;
    statusBar.show();
}

export function activate(context: vscode.ExtensionContext) {
    
    statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.command = 'ide-navigator.showCallGraph';
    setStatus('IDE Navigator: starting…', 'Запускается Python LSP сервер');
    context.subscriptions.push(statusBar);

    const config = vscode.workspace.getConfiguration('ideNavigator');
    const initializationOptions = {
        logLevel: config.get<string>('logLevel', 'info'),
        cacheSize: config.get<number>('cacheSize', 32),
        enableCallGraph: config.get<boolean>('enableCallGraph', true),
    };

    const target = `${process.platform}-${process.arch}`;
    const binaryName = process.platform === 'win32'
        ? 'ide-navigator-server.exe'
        : 'ide-navigator-server';
    const serverBinary = context.asAbsolutePath(
        path.join('bundled', 'server', target, binaryName)
    );

    console.log('IDE Navigator: target  =', target);
    console.log('IDE Navigator: binary  =', serverBinary);

    if (process.platform !== 'win32') {
        try {
            fs.chmodSync(serverBinary, 0o755);
        } catch (err) {
            console.warn('IDE Navigator: chmod failed', err);
        }
    }

    const serverOptions: ServerOptions = {
        command: serverBinary,
        args: []
    };

    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'python' },
            { scheme: 'file', language: 'java' },
            { scheme: 'file', language: 'cpp' },
            { scheme: 'file', language: 'c' },
            { scheme: 'file', language: 'go' },
            { scheme: 'file', language: 'javascript' },
            { scheme: 'file', language: 'typescript' },
            { scheme: 'file', language: 'typescriptreact' }
        ],
        initializationOptions,
    };

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
                {
                    enableScripts: true,
                    localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'media')],
                }
            );

            renderWebview(panel, context, 'callGraph.html', 'callGraph.css', 'callGraph.js');
            
            panel.webview.postMessage({ command: 'init', data: graphData });

            panel.webview.onDidReceiveMessage(
                async (message: CallGraphInbound | { command: 'ready' }) => {
                    if (message.command === 'ready') {
                        
                        panel.webview.postMessage({ command: 'init', data: graphData });
                        return;
                    }
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

            let refreshTimer: ReturnType<typeof setTimeout> | undefined;
            let refreshing = false;
            const changeListener = vscode.workspace.onDidChangeTextDocument((e) => {
                if (e.document.uri.toString() !== uri) return;
                if (refreshTimer) clearTimeout(refreshTimer);
                refreshTimer = setTimeout(async () => {
                    if (refreshing) return;  
                    refreshing = true;
                    try {
                        const fresh: GraphData = await client.sendRequest('workspace/executeCommand', {
                            command: 'ide-navigator.callGraph',
                            arguments: [uri]
                        });
                        panel.webview.postMessage({ command: 'refresh', data: fresh });
                    } catch (_) {  } finally {
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
                {
                    enableScripts: true,
                    localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'media')],
                }
            );

            renderWebview(panel, context, 'references.html', 'references.css', 'references.js');
            panel.webview.postMessage({ command: 'init', data, fileName });

            panel.webview.onDidReceiveMessage(
                async (message: ReferencesInbound | { command: 'ready' }) => {
                    if (message.command === 'ready') {
                        panel.webview.postMessage({ command: 'init', data, fileName });
                        return;
                    }
                    if (message.command !== 'openReference' || !data) return;
                    
                    if (typeof message.line !== 'number' ||
                        typeof message.character !== 'number') {
                        return;
                    }
                    const endChar = typeof message.endCharacter === 'number'
                        ? message.endCharacter
                        : message.character;
                    const targetUri = vscode.Uri.parse(data.uri);
                    const pos = new vscode.Position(message.line, message.character);
                    const range = new vscode.Range(
                        pos,
                        new vscode.Position(message.line, endChar)
                    );
                    await vscode.window.showTextDocument(targetUri, {
                        selection: range,
                        viewColumn: vscode.ViewColumn.One
                    });
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

