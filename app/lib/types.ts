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
