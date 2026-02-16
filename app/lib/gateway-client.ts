/**
 * Gateway Client — OpenClaw Gateway WebSocket RPC
 *
 * Full implementation of the Gateway RPC protocol for cluster management.
 * Supports device identity auth and simple token auth.
 */

import WebSocket from 'ws';
import { randomUUID } from 'crypto';
import type { GatewayConfig, SessionInfo, NodeStatus } from './types';

/* ────────────────── Protocol Types ────────────────── */

export interface RequestFrame {
  type: 'req';
  id: string;
  method: string;
  params?: unknown;
}

export interface ResponseFrame {
  type: 'res';
  id: string;
  ok: boolean;
  payload?: unknown;
  error?: { code?: string; message: string; details?: unknown };
}

export interface EventFrame {
  type: 'event';
  event: string;
  payload?: unknown;
  seq?: number;
}

export interface HelloOk {
  type: 'hello-ok';
  protocol: number;
  features?: { methods?: string[]; events?: string[] };
  snapshot?: unknown;
  auth?: {
    deviceToken?: string;
    role?: string;
    scopes?: string[];
    issuedAtMs?: number;
  };
  policy?: { tickIntervalMs?: number };
}

type Pending = {
  resolve: (value: unknown) => void;
  reject: (err: unknown) => void;
};

/* ────────────────── Client Options ────────────────── */

export interface GatewayClientOptions {
  url: string;
  token?: string;
  password?: string;
  clientName?: string;
  clientVersion?: string;
  platform?: string;
  /** Callback when connection is established */
  onHello?: (hello: HelloOk) => void;
  /** Callback for events */
  onEvent?: (evt: EventFrame) => void;
  /** Callback when connection closes */
  onClose?: (info: { code: number; reason: string }) => void;
  /** Callback for connection errors */
  onError?: (err: Error) => void;
  /** Reconnect automatically */
  autoReconnect?: boolean;
  /** Initial backoff in ms */
  backoffMs?: number;
}

/* ────────────────── Gateway Client Class ────────────────── */

export class GatewayClient {
  private ws: WebSocket | null = null;
  private pending = new Map<string, Pending>();
  private closed = false;
  private lastSeq: number | null = null;
  private connectNonce: string | null = null;
  private connectSent = false;
  private connectTimer: NodeJS.Timeout | null = null;
  private backoffMs: number;
  private helloOk: HelloOk | null = null;

  constructor(private opts: GatewayClientOptions) {
    this.backoffMs = opts.backoffMs ?? 1000;
  }

  /* ── Connection Management ── */

  start(): void {
    this.closed = false;
    this.connect();
  }

  stop(): void {
    this.closed = true;
    if (this.connectTimer) {
      clearTimeout(this.connectTimer);
      this.connectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
    this.flushPending(new Error('gateway client stopped'));
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN && this.helloOk !== null;
  }

  get hello(): HelloOk | null {
    return this.helloOk;
  }

  private connect(): void {
    if (this.closed) return;

    try {
      this.ws = new WebSocket(this.opts.url, {
        maxPayload: 25 * 1024 * 1024,
      });
    } catch (err) {
      this.opts.onError?.(err instanceof Error ? err : new Error(String(err)));
      this.scheduleReconnect();
      return;
    }

    this.ws.on('open', () => this.queueConnect());
    this.ws.on('message', (data) => this.handleMessage(data.toString()));
    this.ws.on('close', (code, reason) => {
      const reasonText = reason.toString() || 'unknown';
      this.ws = null;
      this.helloOk = null;
      this.flushPending(new Error(`gateway closed (${code}): ${reasonText}`));
      this.opts.onClose?.({ code, reason: reasonText });
      this.scheduleReconnect();
    });
    this.ws.on('error', (err) => {
      if (!this.connectSent) {
        this.opts.onError?.(err);
      }
    });
  }

  private scheduleReconnect(): void {
    if (this.closed || !this.opts.autoReconnect) return;

    const delay = this.backoffMs;
    this.backoffMs = Math.min(this.backoffMs * 2, 30_000);

    setTimeout(() => this.connect(), delay).unref();
  }

  private flushPending(err: Error): void {
    for (const [, p] of this.pending) {
      p.reject(err);
    }
    this.pending.clear();
  }

  /* ── Protocol Handling ── */

  private queueConnect(): void {
    this.connectNonce = null;
    this.connectSent = false;

    if (this.connectTimer) {
      clearTimeout(this.connectTimer);
    }

    this.connectTimer = setTimeout(() => this.sendConnect(), 500);
  }

  private sendConnect(): void {
    if (this.connectSent || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    this.connectSent = true;
    if (this.connectTimer) {
      clearTimeout(this.connectTimer);
      this.connectTimer = null;
    }

    const role = 'operator';
    const scopes = ['operator.admin', 'operator.read', 'operator.approvals'];

    const auth = this.opts.token || this.opts.password
      ? { token: this.opts.token, password: this.opts.password }
      : undefined;

    const params = {
      minProtocol: 3,
      maxProtocol: 3,
      client: {
        id: this.opts.clientName ?? 'gateway-client',
        version: this.opts.clientVersion ?? '1.0.0',
        platform: this.opts.platform ?? process.platform,
        mode: 'backend',
      },
      role,
      scopes,
      auth,
    };

    void this.request<HelloOk>('connect', params)
      .then((hello) => {
        this.helloOk = hello;
        this.backoffMs = this.opts.backoffMs ?? 1000;
        this.opts.onHello?.(hello);
      })
      .catch((err) => {
        this.opts.onError?.(err instanceof Error ? err : new Error(String(err)));
        this.ws?.close(4008, 'connect failed');
      });
  }

  private handleMessage(raw: string): void {
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      return;
    }

    // Handle event frames
    const evt = parsed as EventFrame;
    if (evt.type === 'event') {
      // Handle connect.challenge
      if (evt.event === 'connect.challenge') {
        const payload = evt.payload as { nonce?: string } | undefined;
        if (payload?.nonce) {
          this.connectNonce = payload.nonce;
          this.sendConnect();
        }
        return;
      }

      // Track sequence for gap detection
      if (typeof evt.seq === 'number') {
        this.lastSeq = evt.seq;
      }

      this.opts.onEvent?.(evt);
      return;
    }

    // Handle response frames
    const res = parsed as ResponseFrame;
    if (res.type === 'res') {
      const pending = this.pending.get(res.id);
      if (!pending) return;

      this.pending.delete(res.id);

      if (res.ok) {
        pending.resolve(res.payload);
      } else {
        pending.reject(new Error(res.error?.message ?? 'request failed'));
      }
    }
  }

  /* ── RPC Request ── */

  async request<T = unknown>(method: string, params?: unknown): Promise<T> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('gateway not connected');
    }

    const id = randomUUID();
    const frame: RequestFrame = { type: 'req', id, method, params };

    const p = new Promise<T>((resolve, reject) => {
      this.pending.set(id, {
        resolve: (v) => resolve(v as T),
        reject,
      });
    });

    this.ws.send(JSON.stringify(frame));
    return p;
  }

  /* ── Convenience Methods ── */

  /** Health check */
  async health(): Promise<{ online: boolean; version?: string; uptime?: number }> {
    const result = await this.request<{ version?: string; uptimeMs?: number }>('health');
    return {
      online: true,
      version: result?.version,
      uptime: result?.uptimeMs,
    };
  }

  /** Get config */
  async configGet(): Promise<{ hash?: string; raw?: string; config?: GatewayConfig }> {
    return this.request('config.get');
  }

  /** Patch config (triggers restart) */
  async configPatch(raw: string, baseHash: string, note?: string): Promise<{
    ok: boolean;
    config?: GatewayConfig;
    restart?: { scheduled: boolean; delayMs?: number };
  }> {
    return this.request('config.patch', { raw, baseHash, note });
  }

  /** Apply full config (triggers restart) */
  async configApply(raw: string, baseHash: string, note?: string): Promise<{
    ok: boolean;
    config?: GatewayConfig;
    restart?: { scheduled: boolean; delayMs?: number };
  }> {
    return this.request('config.apply', { raw, baseHash, note });
  }

  /** List sessions */
  async sessionsList(opts?: { limit?: number; activeMinutes?: number }): Promise<{
    sessions: Array<{
      key: string;
      agentId?: string;
      channel?: string;
      peer?: string;
      lastMessageAt?: string;
      inputTokens?: number;
      outputTokens?: number;
    }>;
  }> {
    return this.request('sessions.list', opts);
  }

  /** Send message to session */
  async sessionsSend(sessionKey: string, message: string): Promise<{ ok: boolean }> {
    return this.request('send', { sessionKey, message });
  }

  /** Reset session */
  async sessionsReset(key: string): Promise<{ ok: boolean }> {
    return this.request('sessions.reset', { key });
  }

  /** Delete session */
  async sessionsDelete(key: string): Promise<{ ok: boolean }> {
    return this.request('sessions.delete', { key });
  }

  /** Trigger agent turn */
  async agentTurn(sessionKey: string, message: string, opts?: {
    model?: string;
    thinking?: string;
  }): Promise<{ ok: boolean }> {
    return this.request('agent', { sessionKey, message, ...opts });
  }

  /** Restart gateway */
  async restart(delayMs?: number, reason?: string): Promise<{ ok: boolean; scheduled: boolean }> {
    return this.request('update.run', { delayMs, reason });
  }
}

/* ────────────────── Connection Pool ────────────────── */

const clients = new Map<string, GatewayClient>();

export function getGatewayClient(nodeId: string, opts: GatewayClientOptions): GatewayClient {
  let client = clients.get(nodeId);
  if (!client || client.ws?.readyState !== WebSocket.OPEN) {
    client = new GatewayClient(opts);
    clients.set(nodeId, client);
  }
  return client;
}

export function closeGatewayClient(nodeId: string): void {
  const client = clients.get(nodeId);
  if (client) {
    client.stop();
    clients.delete(nodeId);
  }
}

/* ────────────────── Helper Functions ────────────────── */

/** Quick health check without full connection */
export async function quickHealthCheck(
  wsUrl: string,
  token?: string,
): Promise<{ online: boolean; error?: string; model?: string; version?: string }> {
  return new Promise((resolve) => {
    const client = new GatewayClient({
      url: wsUrl,
      token,
      autoReconnect: false,
      onError: (err) => resolve({ online: false, error: err.message }),
      onClose: ({ reason }) => resolve({ online: false, error: reason }),
      onHello: async (hello) => {
        try {
          const health = await client.health();
          const config = await client.configGet();
          resolve({
            online: true,
            version: health.version,
            model: (config.config as GatewayConfig)?.agents?.defaults?.model?.primary,
          });
        } catch (err) {
          resolve({
            online: true,
            error: err instanceof Error ? err.message : String(err),
          });
        } finally {
          client.stop();
        }
      },
    });

    client.start();

    // Timeout after 10 seconds
    setTimeout(() => {
      if (!client.connected) {
        client.stop();
        resolve({ online: false, error: 'connection timeout' });
      }
    }, 10_000);
  });
}

/** Execute a single RPC call */
export async function gatewayRpc(
  wsUrl: string,
  method: string,
  params: unknown = {},
  token?: string,
): Promise<{ ok: boolean; payload?: unknown; error?: string }> {
  return new Promise((resolve) => {
    const client = new GatewayClient({
      url: wsUrl,
      token,
      autoReconnect: false,
      onError: (err) => resolve({ ok: false, error: err.message }),
      onClose: ({ reason }) => resolve({ ok: false, error: reason }),
      onHello: async () => {
        try {
          const payload = await client.request(method, params);
          resolve({ ok: true, payload });
        } catch (err) {
          resolve({
            ok: false,
            error: err instanceof Error ? err.message : String(err),
          });
        } finally {
          client.stop();
        }
      },
    });

    client.start();

    // Timeout after 30 seconds
    setTimeout(() => {
      if (!client.connected) {
        client.stop();
        resolve({ ok: false, error: 'connection timeout' });
      }
    }, 30_000);
  });
}

/** Get config from gateway */
export async function getConfig(
  wsUrl: string,
  token?: string,
): Promise<GatewayConfig | null> {
  const result = await gatewayRpc(wsUrl, 'config.get', {}, token);
  if (result.ok && result.payload) {
    const p = result.payload as { config?: GatewayConfig };
    return p.config ?? null;
  }
  return null;
}

/** List sessions from gateway */
export async function listSessions(
  wsUrl: string,
  token?: string,
): Promise<SessionInfo[]> {
  const result = await gatewayRpc(wsUrl, 'sessions.list', {}, token);
  if (result.ok && result.payload) {
    const p = result.payload as { sessions?: SessionInfo[] };
    return p.sessions ?? [];
  }
  return [];
}

/** Health check */
export async function healthCheck(
  wsUrl: string,
  token?: string,
): Promise<{ online: boolean; error?: string; model?: string; version?: string }> {
  return quickHealthCheck(wsUrl, token);
}

/** Patch config (triggers restart) */
export async function patchConfig(
  wsUrl: string,
  raw: string,
  baseHash: string,
  token?: string,
  note?: string,
): Promise<{ ok: boolean; error?: string; config?: GatewayConfig }> {
  const result = await gatewayRpc(wsUrl, 'config.patch', { raw, baseHash, note }, token);
  if (result.ok && result.payload) {
    const p = result.payload as { config?: GatewayConfig };
    return { ok: true, config: p.config };
  }
  return { ok: false, error: result.error };
}

/** Apply full config (triggers restart) */
export async function applyConfig(
  wsUrl: string,
  raw: string,
  baseHash: string,
  token?: string,
  note?: string,
): Promise<{ ok: boolean; error?: string; config?: GatewayConfig }> {
  const result = await gatewayRpc(wsUrl, 'config.apply', { raw, baseHash, note }, token);
  if (result.ok && result.payload) {
    const p = result.payload as { config?: GatewayConfig };
    return { ok: true, config: p.config };
  }
  return { ok: false, error: result.error };
}

/** Restart gateway */
export async function restartGateway(
  wsUrl: string,
  token?: string,
  delayMs?: number,
  reason?: string,
): Promise<{ ok: boolean; error?: string }> {
  const result = await gatewayRpc(wsUrl, 'update.run', { delayMs, reason }, token);
  return { ok: result.ok, error: result.error };
}

/** Send message to session */
export async function sendToSession(
  wsUrl: string,
  sessionKey: string,
  message: string,
  token?: string,
): Promise<{ ok: boolean; error?: string }> {
  const result = await gatewayRpc(wsUrl, 'send', { sessionKey, message }, token);
  return { ok: result.ok, error: result.error };
}

/** Reset session */
export async function resetSession(
  wsUrl: string,
  key: string,
  token?: string,
): Promise<{ ok: boolean; error?: string }> {
  const result = await gatewayRpc(wsUrl, 'sessions.reset', { key }, token);
  return { ok: result.ok, error: result.error };
}

/** Delete session */
export async function deleteSession(
  wsUrl: string,
  key: string,
  token?: string,
): Promise<{ ok: boolean; error?: string }> {
  const result = await gatewayRpc(wsUrl, 'sessions.delete', { key }, token);
  return { ok: result.ok, error: result.error };
}
