/**
 * Event Store — JSON-file-backed event rules
 *
 * Persists event engine rules to events.json.
 */

import { promises as fs } from 'fs';
import path from 'path';
import type { EventRule, EventEngineData } from './types';

const EVENT_CONFIG_PATH =
    process.env.EVENT_CONFIG_PATH ||
    path.join(process.cwd(), 'events.json');

/* ── helpers ── */

async function read(): Promise<EventEngineData> {
    try {
        const raw = await fs.readFile(EVENT_CONFIG_PATH, 'utf-8');
        return JSON.parse(raw) as EventEngineData;
    } catch {
        return { rules: [] };
    }
}

async function write(data: EventEngineData): Promise<void> {
    await fs.writeFile(EVENT_CONFIG_PATH, JSON.stringify(data, null, 2), 'utf-8');
}

/* ── public API ── */

export async function listRules(): Promise<EventRule[]> {
    return (await read()).rules;
}

export async function getRule(id: string): Promise<EventRule | undefined> {
    const data = await read();
    return data.rules.find(r => r.id === id);
}

export async function addRule(rule: EventRule): Promise<void> {
    const data = await read();
    if (data.rules.some(r => r.id === rule.id)) {
        throw new Error(`Rule "${rule.id}" already exists`);
    }
    data.rules.push(rule);
    await write(data);
}

export async function updateRule(id: string, patch: Partial<EventRule>): Promise<void> {
    const data = await read();
    const idx = data.rules.findIndex(r => r.id === id);
    if (idx === -1) throw new Error(`Rule "${id}" not found`);
    data.rules[idx] = { ...data.rules[idx], ...patch, id }; // id is immutable
    await write(data);
}

export async function removeRule(id: string): Promise<void> {
    const data = await read();
    data.rules = data.rules.filter(r => r.id !== id);
    await write(data);
}
