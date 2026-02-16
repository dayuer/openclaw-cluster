/**
 * Cluster Store — JSON-file-backed node registry
 *
 * Persists the list of OpenClaw Gateway nodes to a local JSON file.
 * The file is re-read on every call so external edits are picked up.
 */

import { promises as fs } from 'fs';
import path from 'path';
import type { GatewayNode, ClusterData } from './types';

const CONFIG_PATH =
    process.env.CLUSTER_CONFIG_PATH ||
    path.join(process.cwd(), 'cluster.json');

/* ── helpers ── */

async function read(): Promise<ClusterData> {
    try {
        const raw = await fs.readFile(CONFIG_PATH, 'utf-8');
        return JSON.parse(raw) as ClusterData;
    } catch {
        return { nodes: [] };
    }
}

async function write(data: ClusterData): Promise<void> {
    await fs.writeFile(CONFIG_PATH, JSON.stringify(data, null, 2), 'utf-8');
}

/* ── public API ── */

export async function listNodes(): Promise<GatewayNode[]> {
    const data = await read();
    return data.nodes;
}

export async function getNode(id: string): Promise<GatewayNode | undefined> {
    const data = await read();
    return data.nodes.find((n) => n.id === id);
}

export async function addNode(node: GatewayNode): Promise<void> {
    const data = await read();
    if (data.nodes.some((n) => n.id === node.id)) {
        throw new Error(`Node "${node.id}" already exists`);
    }
    data.nodes.push(node);
    await write(data);
}

export async function updateNode(
    id: string,
    patch: Partial<GatewayNode>,
): Promise<GatewayNode> {
    const data = await read();
    const idx = data.nodes.findIndex((n) => n.id === id);
    if (idx === -1) throw new Error(`Node "${id}" not found`);
    data.nodes[idx] = { ...data.nodes[idx], ...patch, id };
    await write(data);
    return data.nodes[idx];
}

export async function removeNode(id: string): Promise<void> {
    const data = await read();
    data.nodes = data.nodes.filter((n) => n.id !== id);
    await write(data);
}
