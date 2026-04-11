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

    // Найти python в venv
    const pythonPath = context.asAbsolutePath(
        path.join('..', 'server', 'venv', 'Scripts', 'python.exe')
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
        () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('Откройте файл для построения графа');
                return;
            }
            vscode.window.showInformationMessage('Call Graph — будет реализован в Фазе 4');
        }
    );

    context.subscriptions.push(showCallGraph);
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) return undefined;
    return client.stop();
}
