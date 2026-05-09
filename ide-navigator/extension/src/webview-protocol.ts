// Типизированный протокол сообщений между расширением и WebView-панелями.
// Используется обеими сторонами (host + webview-скрипты), чтобы опечатки
// в command-строках и пропущенные поля ловились компилятором, а не в рантайме.

// ── Call Graph ────────────────────────────────────────────────────────────

export interface GraphNode {
    id: string;
    label: string;
    type?: string;
    line?: number;
    character?: number;
    endLine?: number;
    endCharacter?: number;
    complexity?: number;
}

export interface GraphEdge {
    from: string;
    to: string;
    kind: 'call' | 'contains';
}

export interface GraphData {
    nodes: GraphNode[];
    edges: GraphEdge[];
}

export type ExportFormat = 'mermaid' | 'dot' | 'svg' | 'png';

export interface ExportPayload {
    format: ExportFormat;
    text?: string;
    dataUrl?: string;
}

// Входящее (webview → host)
export type CallGraphInbound =
    | { command: 'openNode'; line: number; character: number; endCharacter?: number }
    | { command: 'exportGraph'; payload: ExportPayload };

// Исходящее (host → webview)
export type CallGraphOutbound =
    | { command: 'init'; data: GraphData }
    | { command: 'refresh'; data: GraphData };

// ── References panel ─────────────────────────────────────────────────────

export interface ReferenceItem {
    line: number;
    character: number;
    endCharacter: number;
    snippet: string;
}

export interface ReferencesData {
    name: string;
    language: string;
    uri: string;
    refs: ReferenceItem[];
}

export type ReferencesInbound =
    | { command: 'openReference'; line: number; character: number; endCharacter?: number };

export type ReferencesOutbound =
    | { command: 'init'; data: ReferencesData; fileName: string };
