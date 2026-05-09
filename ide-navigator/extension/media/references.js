// References panel webview logic.
// Данные приходят от расширения через postMessage({command:'init', data, fileName}).
// Благодаря postMessage больше не нужно инжектировать JSON в HTML и экранировать
// `</script>` / U+2028/9 — structured clone не допускает XSS через сниппеты.

(function () {
    'use strict';

    const vscode = acquireVsCodeApi();
    const list = document.getElementById('list');

    function escapeHtml(s) {
        return s.replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
    }

    function render(data, fileName) {
        document.getElementById('refName').textContent = data.name;
        document.getElementById('refCount').textContent = String(data.refs.length);
        document.getElementById('refFile').textContent = fileName;

        list.replaceChildren();
        data.refs.forEach((ref) => {
            const div = document.createElement('div');
            div.className = 'ref';

            let highlighted;
            try {
                highlighted = hljs.highlight(ref.snippet, {
                    language: data.language,
                    ignoreIllegals: true,
                }).value;
            } catch (_) {
                highlighted = escapeHtml(ref.snippet);
            }

            // line-num + code building: innerHTML из highlighted безопасен —
            // hljs возвращает строку с тегами <span class="hljs-*">, которые
            // он сам сгенерировал по escape-правилам. Исходный ref.snippet
            // в try-блоке проходит через hljs.highlight; в catch — через
            // ручной escapeHtml.
            const lineNum = document.createElement('span');
            lineNum.className = 'line-num';
            lineNum.textContent = String(ref.line + 1);

            const pre = document.createElement('pre');
            pre.className = 'code hljs';
            pre.innerHTML = highlighted;

            div.appendChild(lineNum);
            div.appendChild(pre);

            div.addEventListener('click', () => {
                vscode.postMessage({
                    command: 'openReference',
                    line: ref.line,
                    character: ref.character,
                    endCharacter: ref.endCharacter,
                });
            });

            list.appendChild(div);
        });
    }

    window.addEventListener('message', (event) => {
        const msg = event.data;
        if (!msg) return;
        if (msg.command === 'init' && msg.data) {
            render(msg.data, msg.fileName || '');
        }
    });

    vscode.postMessage({ command: 'ready' });
})();
