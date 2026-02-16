/**
 * Agent Store — JSON-file-backed agent registry
 *
 * Persists multi-agent definitions to agents.json.
 * Re-reads on every call so external edits are picked up.
 */

import { promises as fs } from 'fs';
import path from 'path';
import type { AgentSpec, AgentRegistryData } from './types';

const AGENT_CONFIG_PATH =
    process.env.AGENT_CONFIG_PATH ||
    path.join(process.cwd(), 'agents.json');

/* ── helpers ── */

const DEFAULT_DATA: AgentRegistryData = {
    agents: [],
    routerModel: '',
    defaultAgentId: 'general',
};

async function read(): Promise<AgentRegistryData> {
    try {
        const raw = await fs.readFile(AGENT_CONFIG_PATH, 'utf-8');
        return JSON.parse(raw) as AgentRegistryData;
    } catch {
        return { ...DEFAULT_DATA, agents: [] };
    }
}

async function write(data: AgentRegistryData): Promise<void> {
    await fs.writeFile(AGENT_CONFIG_PATH, JSON.stringify(data, null, 2), 'utf-8');
}

/* ── public API ── */

export async function listAgents(): Promise<AgentSpec[]> {
    return (await read()).agents;
}

export async function getAgent(id: string): Promise<AgentSpec | undefined> {
    const data = await read();
    return data.agents.find(a => a.id === id);
}

export async function addAgent(agent: AgentSpec): Promise<void> {
    const data = await read();
    if (data.agents.some(a => a.id === agent.id)) {
        throw new Error(`Agent "${agent.id}" already exists`);
    }
    data.agents.push(agent);
    // Auto-set default if first agent or marked as default
    if (agent.isDefault || data.agents.length === 1) {
        data.defaultAgentId = agent.id;
    }
    await write(data);
}

export async function updateAgent(id: string, patch: Partial<AgentSpec>): Promise<void> {
    const data = await read();
    const idx = data.agents.findIndex(a => a.id === id);
    if (idx === -1) throw new Error(`Agent "${id}" not found`);
    data.agents[idx] = { ...data.agents[idx], ...patch, id }; // id is immutable
    if (patch.isDefault) {
        data.defaultAgentId = id;
    }
    await write(data);
}

export async function removeAgent(id: string): Promise<void> {
    const data = await read();
    data.agents = data.agents.filter(a => a.id !== id);
    if (data.defaultAgentId === id && data.agents.length > 0) {
        data.defaultAgentId = data.agents[0].id;
    }
    await write(data);
}

export async function getRegistryData(): Promise<AgentRegistryData> {
    return read();
}

export async function updateRegistrySettings(
    patch: Partial<Pick<AgentRegistryData, 'routerModel' | 'defaultAgentId'>>,
): Promise<void> {
    const data = await read();
    if (patch.routerModel !== undefined) data.routerModel = patch.routerModel;
    if (patch.defaultAgentId !== undefined) data.defaultAgentId = patch.defaultAgentId;
    await write(data);
}
