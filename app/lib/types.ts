/* ────────────────── OpenClaw Cluster — Types ────────────────── */

/** A registered OpenClaw Gateway node */
export interface GatewayNode {
    id: string;
    name: string;
    /** WebSocket URL, e.g. ws://10.0.1.100:18789 */
    url: string;
    tags: string[];
    auth?: { token?: string };
}

/** Runtime status of a node (not persisted) */
export interface NodeStatus {
    online: boolean;
    /** ISO timestamp of last successful health check */
    lastSeen?: string;
    /** Error message if offline */
    error?: string;
    /** Model currently configured */
    model?: string;
    /** Number of active sessions */
    sessionCount?: number;
    /** Enabled channels */
    channels?: string[];
}

/** GatewayNode + runtime status combined for API responses */
export interface NodeWithStatus extends GatewayNode {
    status: NodeStatus;
}

/** OpenClaw config snapshot (subset we care about) */
export interface GatewayConfig {
    hash?: string;
    raw?: Record<string, unknown>;
    agents?: {
        defaults?: {
            model?: { primary?: string; fallbacks?: string[] };
            workspace?: string;
        };
        list?: Array<{ id: string; name?: string }>;
    };
    channels?: Record<string, { enabled?: boolean;[k: string]: unknown }>;
    gateway?: {
        port?: number;
        bind?: string;
        auth?: { mode?: string; token?: string };
    };
}

/** Session info from Gateway */
export interface SessionInfo {
    key: string;
    agentId?: string;
    channel?: string;
    peer?: string;
    createdAt?: string;
    /** Token count */
    tokens?: number;
}

/** Cluster overview stats */
export interface ClusterOverview {
    totalNodes: number;
    onlineNodes: number;
    offlineNodes: number;
    totalSessions: number;
    nodes: NodeWithStatus[];
}

/** Cluster JSON file structure */
export interface ClusterData {
    nodes: GatewayNode[];
}

/* ────────────────── Multi-Agent Registry ────────────────── */

/** Agent 规格 — 映射 nanobot 的 AgentSpec */
export interface AgentSpec {
    id: string;
    description: string;
    /** Role prompt file path, e.g. "team/roles/general.md" */
    systemPromptFile: string;
    /** Tool whitelist. ["*"] = all tools */
    tools: string[];
    /** Skill whitelist. ["*"] = all skills */
    skills: string[];
    temperature: number;
    maxTokens: number;
    maxIterations: number;
    isDefault?: boolean;
    /** Keyword triggers for fast routing (skip LLM) */
    keywords?: string[];
}

/** LLM Router result — 多领域语义分析 */
export interface RouteResult {
    /** Primary agent ID */
    primary: string;
    /** Related agent IDs, sorted by relevance */
    related: string[];
    /** Focused sub-question for each related agent */
    subTasks: Record<string, string>;
    /** One-line routing reason */
    reason: string;
    /** Domain labels */
    domains: string[];
}

/** Agent registry data (persisted to agents.json) */
export interface AgentRegistryData {
    agents: AgentSpec[];
    /** LLM model used for semantic routing */
    routerModel: string;
    /** Default agent ID (fallback) */
    defaultAgentId: string;
}

/* ────────────────── Event Engine ────────────────── */

/** Event rule — 事件匹配规则 */
export interface EventRule {
    id: string;
    /** Event type pattern, supports wildcards e.g. "payment.*" */
    eventType: string;
    /** Target agent to handle the event */
    agentId: string;
    /** Prompt template with {key} placeholders */
    template: string;
    /** Target channel for response delivery */
    channel: string;
    /** Additional conditions for matching */
    conditions: Record<string, unknown>;
    enabled: boolean;
    priority: number;
}

/** Event engine data (persisted to events.json) */
export interface EventEngineData {
    rules: EventRule[];
}

/** Inbound event payload */
export interface InboundEvent {
    type: string;
    data: Record<string, unknown>;
}

/** Event dispatch result */
export interface EventDispatchResult {
    ruleId: string;
    agentId: string;
    response?: string;
    error?: string;
}
