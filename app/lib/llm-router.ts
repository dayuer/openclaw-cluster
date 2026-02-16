/**
 * LLM Router — 语义意图路由器 (TypeScript 移植)
 *
 * 移植自 survival/nanobot/llm_router.py
 *
 * 功能:
 *   routeMulti() — 返回主角色 + 所有相关角色 + 子任务 + 理由
 *
 * 设计:
 *   - 先做关键词快速匹配
 *   - 未匹配则调用 Router 级小模型 (~200-400ms)
 *   - 结果缓存 60s
 *   - 失败安全: 回退到 default agent
 */

import type { AgentSpec, RouteResult } from './types';
import { gatewayRpc } from './gateway-client';
import { listNodes } from './cluster-store';

const CACHE_TTL = 60_000; // 60s in ms
const CACHE_MAX = 256;

interface CacheEntry {
    result: RouteResult;
    ts: number;
}

const cache = new Map<string, CacheEntry>();

/* ── Router System Prompt (adapted from nanobot) ── */

function buildSystemPrompt(agents: AgentSpec[]): string {
    const rolesBlock = agents
        .map(a => `- **${a.id}**: ${a.description}`)
        .join('\n');

    return `你是一个消息路由器。根据用户消息的语义意图，分析最适合回答的专家，并为相关专家生成聚焦子问题。

## 可用专家角色

${rolesBlock}

## 分析规则
1. 判断用户消息涉及的所有领域
2. 选择最紧迫/最核心的领域作为主角色 (primary)
3. 列出所有相关的角色 (related)，按相关度排序
4. 为每个 related 角色生成一个聚焦子问题 (sub_tasks)
5. 用一句极简中文说明路由理由

## 返回格式 (严格 JSON)
{"primary":"角色ID","related":["角色ID1","角色ID2"],"sub_tasks":{"角色ID1":"聚焦子问题1","角色ID2":"聚焦子问题2"},"reason":"一句话","domains":["领域1","领域2"]}

## 注意
- 闲聊、打招呼、不确定的内容: primary 设为默认角色, related 为空
- related 只放确实相关的角色，不要凑数
- sub_tasks 的子问题要具体且聚焦该专家领域，100字以内`;
}

/* ── Keyword fast-match ── */

function keywordMatch(
    content: string,
    agents: AgentSpec[],
    defaultId: string,
): RouteResult | null {
    const lower = content.toLowerCase();
    for (const agent of agents) {
        if (!agent.keywords?.length) continue;
        for (const kw of agent.keywords) {
            if (lower.includes(kw.toLowerCase())) {
                return {
                    primary: agent.id,
                    related: [],
                    subTasks: {},
                    reason: `关键词匹配: "${kw}"`,
                    domains: [],
                };
            }
        }
    }
    return null;
}

/* ── Cache helpers ── */

function contentHash(content: string): string {
    const text = content.slice(0, 200).trim().toLowerCase();
    // Simple hash — sufficient for cache keys
    let h = 0;
    for (let i = 0; i < text.length; i++) {
        h = ((h << 5) - h + text.charCodeAt(i)) | 0;
    }
    return h.toString(36);
}

function pruneCache(): void {
    if (cache.size >= CACHE_MAX) {
        let oldestKey = '';
        let oldestTs = Infinity;
        for (const [k, v] of cache) {
            if (v.ts < oldestTs) {
                oldestTs = v.ts;
                oldestKey = k;
            }
        }
        if (oldestKey) cache.delete(oldestKey);
    }
}

/* ── Public API ── */

export async function routeMulti(
    content: string,
    agents: AgentSpec[],
    defaultAgentId: string,
    routerModel: string,
): Promise<RouteResult> {
    const fallback: RouteResult = {
        primary: defaultAgentId || 'general',
        related: [],
        subTasks: {},
        reason: 'default',
        domains: [],
    };

    if (!content?.trim() || agents.length === 0) return fallback;

    // 1. Keyword fast-match
    const kwResult = keywordMatch(content, agents, defaultAgentId);
    if (kwResult) return kwResult;

    // 2. Cache check
    const key = contentHash(content);
    const cached = cache.get(key);
    if (cached && Date.now() - cached.ts < CACHE_TTL) {
        return cached.result;
    }

    // 3. If no router model configured, return default
    if (!routerModel) return fallback;

    // 4. Find an online Gateway node to call the LLM
    const nodes = await listNodes();
    if (nodes.length === 0) return fallback;

    // Use first node for routing (could be smarter with load balancing)
    const node = nodes[0];

    try {
        const systemPrompt = buildSystemPrompt(agents);
        const res = await gatewayRpc(
            node.url,
            'chat.send',
            {
                message: content,
                sessionKey: '__router__',
                systemPrompt,
                model: routerModel,
                maxTokens: 300,
                temperature: 0.1,
            },
            node.auth,
        );

        if (!res.ok || !res.payload) return fallback;

        const raw = String(res.payload.reply || res.payload.content || '').trim();
        // Clean markdown code blocks
        const cleaned = raw.startsWith('```')
            ? raw.split('\n').slice(1).join('\n').replace(/```\s*$/, '').trim()
            : raw;

        const data = JSON.parse(cleaned);
        const validIds = new Set(agents.map(a => a.id));

        const result: RouteResult = {
            primary: validIds.has(data.primary) ? data.primary : defaultAgentId,
            related: (data.related || []).filter((r: string) => validIds.has(r)),
            subTasks: data.sub_tasks || data.subTasks || {},
            reason: data.reason || '',
            domains: data.domains || [],
        };

        // Write cache
        pruneCache();
        cache.set(key, { result, ts: Date.now() });

        return result;
    } catch {
        return fallback;
    }
}
