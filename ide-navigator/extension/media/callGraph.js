
(function () {
    'use strict';

    const vscode = acquireVsCodeApi();

    const TYPE_COLORS = {
        'function':    { bg: '#7f6df2', border: '#9b8afb', glow: 'rgba(127,109,242,0.35)' },
        'method':      { bg: '#4aadff', border: '#6bc0ff', glow: 'rgba(74,173,255,0.35)' },
        'constructor': { bg: '#e5a33a', border: '#f0bd5e', glow: 'rgba(229,163,58,0.35)' },
        'class':       { bg: '#e06c75', border: '#f28b8b', glow: 'rgba(224,108,117,0.35)' },
        'interface':   { bg: '#56b6c2', border: '#7fcfd8', glow: 'rgba(86,182,194,0.35)' },
        'struct':      { bg: '#d19a66', border: '#e4b882', glow: 'rgba(209,154,102,0.35)' },
    };
    const DEFAULT_COLOR = TYPE_COLORS.function;
    const NON_CALLABLE_TYPES = new Set(['class', 'interface', 'struct']);

    let raw = { nodes: [], edges: [] };
    const nodeById = {};
    const classToMethods = {};
    const methodToClass = {};
    const degree = {};
    let maxDeg = 1;
    let network = null;
    let lastBuilt = null;

    function reindex() {
        Object.keys(nodeById).forEach(k => delete nodeById[k]);
        Object.keys(classToMethods).forEach(k => delete classToMethods[k]);
        Object.keys(methodToClass).forEach(k => delete methodToClass[k]);
        Object.keys(degree).forEach(k => delete degree[k]);

        raw.nodes.forEach(n => {
            nodeById[n.id] = n;
            degree[n.id] = 0;
        });
        raw.edges.forEach(e => {
            degree[e.from] = (degree[e.from] || 0) + 1;
            degree[e.to]   = (degree[e.to]   || 0) + 1;
        });
        raw.edges.filter(e => e.kind === 'contains').forEach(e => {
            if (!classToMethods[e.from]) classToMethods[e.from] = new Set();
            classToMethods[e.from].add(e.to);
            if (!(e.to in methodToClass)) {
                methodToClass[e.to] = e.from;
            }
        });
        maxDeg = Math.max(1, ...Object.values(degree));
    }

    function methodCountOf(clsId) {
        return classToMethods[clsId] ? classToMethods[clsId].size : 0;
    }

    const state = {
        search: '',
        groupByClass: false,
        showCall: true,
        showContains: true,
        highlightUnused: false,
        markCycles: false,
        selectedNode: null,
    };

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
                        let w;
                        do {
                            w = stack.pop();
                            onStack[w] = false;
                            sccOf[w] = sccId;
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

    function buildGraph() {
        let nodes = raw.nodes.slice();
        let edges = raw.edges.map(e => ({ from: e.from, to: e.to, kind: e.kind }));

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

    function buildDataSets() {
        const built = buildGraph();
        const nodes = built.nodes;
        const edges = built.edges.filter(e => {
            if (e.kind === 'call' && !state.showCall) return false;
            if (e.kind === 'contains' && !state.showContains) return false;
            return true;
        });
        const q = state.search.trim().toLowerCase();
        const unused = state.highlightUnused ? computeUnused(nodes, built.edges) : null;
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

    function updateStats(rawCount) {
        document.getElementById('stats').textContent =
            rawCount.nodes + ' symbols · ' + rawCount.edges + ' edges';
    }

    function showEmpty() {
        document.getElementById('graph').style.display = 'none';
        document.getElementById('legend').style.display = 'none';
        document.getElementById('toolbar').style.display = 'none';
        document.getElementById('stats').style.display = 'none';
        document.getElementById('info').style.display = 'block';
    }

    function showPopulated() {
        document.getElementById('graph').style.display = '';
        document.getElementById('legend').style.display = '';
        document.getElementById('toolbar').style.display = '';
        document.getElementById('stats').style.display = '';
        document.getElementById('info').style.display = 'none';
    }

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

    function rerender() {
        const ds = buildDataSets();
        network.setData({ nodes: ds.nodes, edges: ds.edges });
        updateStats(ds.rawCount);
        network.setOptions({ physics: { enabled: true, stabilization: { iterations: 50 } } });
        setTimeout(() => network.setOptions({ physics: { enabled: false } }), 1200);
    }

    function buildMermaid() {
        const lines = ['graph LR'];
        const safeId = {};
        (lastBuilt ? lastBuilt.nodes : raw.nodes).forEach((n, i) => {
            safeId[n.id] = 'n' + i;
            const lbl = n.label.replace(/"/g, '\\"');
            lines.push('    ' + safeId[n.id] + '["' + lbl + '"]');
        });
        (lastBuilt ? lastBuilt.edges : raw.edges).forEach(e => {
            const a = safeId[e.from], b = safeId[e.to];
            if (!a || !b) return;
            lines.push('    ' + a + (e.kind === 'contains' ? ' -.-> ' : ' --> ') + b);
        });
        return lines.join('\n');
    }
    function buildDot() {
        const lines = ['digraph G {', '    bgcolor="#191919";', '    node [fontcolor="#ccc", color="#7f6df2", style=filled, fillcolor="#262626"];', '    edge [color="#888"];'];
        const safeId = {};
        (lastBuilt ? lastBuilt.nodes : raw.nodes).forEach((n, i) => {
            safeId[n.id] = 'n' + i;
            const lbl = n.label.replace(/"/g, '\\"');
            lines.push('    ' + safeId[n.id] + ' [label="' + lbl + '"];');
        });
        (lastBuilt ? lastBuilt.edges : raw.edges).forEach(e => {
            const a = safeId[e.from], b = safeId[e.to];
            if (!a || !b) return;
            const style = e.kind === 'contains' ? ' [style=dashed, color="#e06c75"]' : '';
            lines.push('    ' + a + ' -> ' + b + style + ';');
        });
        lines.push('}');
        return lines.join('\n');
    }
    function buildSvg(container) {
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
            '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '" viewBox="' + minX + ' ' + minY + ' ' + w + ' ' + h + '">',
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
    function buildPng(container) {
        const canvas = container.querySelector('canvas');
        if (!canvas) return null;
        return canvas.toDataURL('image/png');
    }

    function initNetwork() {
        if (raw.nodes.length === 0) {
            showEmpty();
            return;
        }
        showPopulated();

        const container = document.getElementById('graph');
        const initial = buildDataSets();
        updateStats(initial.rawCount);

        network = new vis.Network(
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

        network.on('stabilizationIterationsDone', () => {
            network.setOptions({ physics: { enabled: false } });
        });
        network.on('dragEnd', (params) => {
            if (params.nodes.length > 0) {
                network.setOptions({ physics: { enabled: true, stabilization: { iterations: 50 } } });
                setTimeout(() => network.setOptions({ physics: { enabled: false } }), 1500);
            }
        });
        network.on('click', (params) => {
            if (params.nodes.length === 0) {
                state.selectedNode = null;
                return;
            }
            const nodeId = params.nodes[0];
            state.selectedNode = nodeId;
            const src = params.event && params.event.srcEvent;
            const withMod = src && (src.ctrlKey || src.metaKey || src.shiftKey || src.altKey);
            if (withMod) {
                navigateToNode(nodeId);
            }
        });
        network.on('doubleClick', (params) => {
            if (params.nodes.length > 0) {
                navigateToNode(params.nodes[0]);
            }
        });

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

        document.getElementById('exportFmt').addEventListener('change', (ev) => {
            const fmt = ev.target.value;
            ev.target.value = '';
            if (!fmt) return;
            let payload;
            if (fmt === 'mermaid') payload = { format: 'mermaid', text: buildMermaid() };
            else if (fmt === 'dot') payload = { format: 'dot', text: buildDot() };
            else if (fmt === 'svg') payload = { format: 'svg', text: buildSvg(container) };
            else if (fmt === 'png') {
                const dataUrl = buildPng(container);
                if (!dataUrl) return;
                payload = { format: 'png', dataUrl: dataUrl };
            }
            vscode.postMessage({ command: 'exportGraph', payload: payload });
        });

        const usedTypes = new Set(raw.nodes.map(n => n.type));
        const legendEl = document.getElementById('legend');
        legendEl.replaceChildren();
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
    }

    window.addEventListener('message', (event) => {
        const msg = event.data;
        if (!msg) return;
        if (msg.command === 'init' && msg.data) {
            raw = msg.data;
            reindex();
            initNetwork();
        } else if (msg.command === 'refresh' && msg.data) {
            raw = msg.data;
            reindex();
            if (network) {
                rerender();
            } else {
                initNetwork();
            }
        }
    });

    vscode.postMessage({ command: 'ready' });
})();
