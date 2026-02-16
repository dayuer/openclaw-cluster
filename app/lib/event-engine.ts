/**
 * Event Engine — 事件驱动引擎 (TypeScript 移植)
 *
 * 移植自 survival/nanobot/event_engine.py
 *
 * 功能:
 *   ingest(event) → 规则匹配 → Agent 派发 → 返回结果
 *
 * 设计:
 *   - 从 event-store 加载规则
 *   - 支持通配符匹配 (payment.* 匹配 payment.success)
 *   - 模板渲染 ({user.name} → 事件数据)
 *   - 条件过滤
 */

import type { EventRule, InboundEvent, EventDispatchResult } from './types';
import { listRules } from './event-store';

/* ── Type matching ── */

function matchType(pattern: string, eventType: string): boolean {
    if (pattern === '*') return true;
    if (pattern === eventType) return true;
    // Wildcard: "payment.*" matches "payment.success"
    if (pattern.endsWith('.*')) {
        const prefix = pattern.slice(0, -2);
        return eventType.startsWith(prefix + '.');
    }
    return false;
}

/* ── Condition matching ── */

function matchConditions(
    conditions: Record<string, unknown>,
    data: Record<string, unknown>,
): boolean {
    for (const [key, expected] of Object.entries(conditions)) {
        const actual = getNestedValue(data, key);
        if (actual !== expected) return false;
    }
    return true;
}

function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
    const parts = path.split('.');
    let current: unknown = obj;
    for (const part of parts) {
        if (current == null || typeof current !== 'object') return undefined;
        current = (current as Record<string, unknown>)[part];
    }
    return current;
}

/* ── Template rendering ── */

export function renderTemplate(
    template: string,
    data: Record<string, unknown>,
): string {
    return template.replace(/\{([^}]+)\}/g, (_match, key: string) => {
        const value = getNestedValue(data, key.trim());
        return value != null ? String(value) : `{${key}}`;
    });
}

/* ── Rule matching ── */

function findMatchingRules(
    rules: EventRule[],
    event: InboundEvent,
): EventRule[] {
    return rules
        .filter(r => r.enabled)
        .filter(r => matchType(r.eventType, event.type))
        .filter(r => {
            if (Object.keys(r.conditions).length === 0) return true;
            return matchConditions(r.conditions, event.data);
        })
        .sort((a, b) => b.priority - a.priority);
}

/* ── Public API ── */

/**
 * Process an inbound event:
 * 1. Load rules from store
 * 2. Match rules against event
 * 3. Render templates
 * 4. Return dispatch results (actual agent dispatch is done by the caller)
 */
export async function ingest(
    event: InboundEvent,
): Promise<{ matched: EventDispatchResult[]; prompt: Record<string, string> }> {
    const rules = await listRules();
    const matched = findMatchingRules(rules, event);

    const results: EventDispatchResult[] = [];
    const prompts: Record<string, string> = {};

    for (const rule of matched) {
        const renderedPrompt = rule.template
            ? renderTemplate(rule.template, event.data)
            : `Event: ${event.type}\nData: ${JSON.stringify(event.data)}`;

        prompts[rule.id] = renderedPrompt;
        results.push({
            ruleId: rule.id,
            agentId: rule.agentId,
        });
    }

    return { matched: results, prompt: prompts };
}

/**
 * Get engine statistics.
 */
export async function getStats(): Promise<{
    totalRules: number;
    enabledRules: number;
    byEventType: Record<string, number>;
}> {
    const rules = await listRules();
    const byEventType: Record<string, number> = {};
    for (const r of rules) {
        byEventType[r.eventType] = (byEventType[r.eventType] || 0) + 1;
    }
    return {
        totalRules: rules.length,
        enabledRules: rules.filter(r => r.enabled).length,
        byEventType,
    };
}
