/**
 * Gateway Client — OpenClaw Gateway WebSocket RPC
 *
 * Provides a simple request/response wrapper over the Gateway WS protocol.
 * Each call opens a fresh connection, sends one RPC, and disconnects.
 * This is intentionally stateless to keep the cluster manager simple.
 *
 * For production use with many nodes you might want connection pooling;
 * for an admin dashboard this is fine.
 */

import type { GatewayConfig, SessionInfo } from './types';

interface RpcResponse {
    ok: boolean;
    payload?: Record<string, unknown>;
    error?: string;
}

/**
 * Send a single RPC call to an OpenClaw Gateway.
 * Uses the HTTP upgrade endpoint which OpenClaw exposes.
 * Falls back to a simple HTTP POST at /rpc if WS is unavailable.
 */
export async function gatewayRpc(
    baseUrl: string,
    method: string,
    params: Record<string, unknown> = {},
    auth?: { token?: string },
): Promise<RpcResponse> {
    // Derive HTTP URL from WS URL
    const httpUrl = baseUrl
        .replace(/^ws:\/\//, 'http://')
        .replace(/^wss:\/\//, 'https://');

    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
    };
    if (auth?.token) {
        headers['Authorization'] = `Bearer ${auth.token}`;
    }

    try {
        // OpenClaw Gateway exposes CLI RPC at POST /v1/gateway/call
        const res = await fetch(`${httpUrl}/v1/gateway/call`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ method, params }),
            signal: AbortSignal.timeout(10_000),
        });

        if (!res.ok) {
            return { ok: false, error: `HTTP ${res.status}: ${res.statusText}` };
        }

        const data = await res.json();
        return { ok: true, payload: data };
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        return { ok: false, error: msg };
    }
}

/* ── Typed convenience methods ── */

export async function getConfig(
    baseUrl: string,
    auth?: { token?: string },
): Promise<GatewayConfig | null> {
    const res = await gatewayRpc(baseUrl, 'config.get', {}, auth);
    if (!res.ok) return null;
    return (res.payload ?? null) as GatewayConfig | null;
}

export async function patchConfig(
    baseUrl: string,
    raw: string,
    baseHash: string,
    auth?: { token?: string },
): Promise<RpcResponse> {
    return gatewayRpc(baseUrl, 'config.patch', { raw, baseHash }, auth);
}

export async function listSessions(
    baseUrl: string,
    auth?: { token?: string },
): Promise<SessionInfo[]> {
    const res = await gatewayRpc(baseUrl, 'sessions.list', {}, auth);
    if (!res.ok) return [];
    const sessions = res.payload?.sessions;
    return Array.isArray(sessions) ? (sessions as SessionInfo[]) : [];
}

export async function healthCheck(
    baseUrl: string,
    auth?: { token?: string },
): Promise<{ online: boolean; error?: string; model?: string }> {
    const cfg = await getConfig(baseUrl, auth);
    if (!cfg) return { online: false, error: 'Cannot reach Gateway' };
    const model = cfg.agents?.defaults?.model?.primary;
    return { online: true, model };
}
