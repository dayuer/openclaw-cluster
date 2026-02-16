/**
 * GET  /api/nodes — list all nodes + live status
 * POST /api/nodes — add a new node
 */
import { NextRequest, NextResponse } from 'next/server';
import { listNodes, addNode, updateNode, removeNode } from '@/app/lib/cluster-store';
import { healthCheck, listSessions } from '@/app/lib/gateway-client';
import type { GatewayNode, NodeWithStatus } from '@/app/lib/types';

export async function GET() {
    const nodes = await listNodes();

    // Check health of all nodes in parallel
    const results: NodeWithStatus[] = await Promise.all(
        nodes.map(async (node) => {
            try {
                const [health, sessions] = await Promise.all([
                    healthCheck(node.url, node.auth),
                    listSessions(node.url, node.auth),
                ]);
                return {
                    ...node,
                    status: {
                        online: health.online,
                        model: health.model,
                        sessionCount: sessions.length,
                        lastSeen: health.online ? new Date().toISOString() : undefined,
                        error: health.error,
                    },
                };
            } catch (err) {
                return {
                    ...node,
                    status: {
                        online: false,
                        error: err instanceof Error ? err.message : 'Unknown error',
                    },
                };
            }
        }),
    );

    return NextResponse.json({ nodes: results });
}

export async function POST(req: NextRequest) {
    try {
        const body = (await req.json()) as GatewayNode;

        if (!body.id || !body.name || !body.url) {
            return NextResponse.json(
                { error: 'id, name, url are required' },
                { status: 400 },
            );
        }

        await addNode({
            id: body.id,
            name: body.name,
            url: body.url,
            tags: body.tags ?? [],
            auth: body.auth,
        });

        return NextResponse.json({ ok: true });
    } catch (err) {
        return NextResponse.json(
            { error: err instanceof Error ? err.message : 'Failed' },
            { status: 400 },
        );
    }
}

export async function PUT(req: NextRequest) {
    try {
        const body = (await req.json()) as Partial<GatewayNode> & { id: string };
        if (!body.id) {
            return NextResponse.json({ error: 'id is required' }, { status: 400 });
        }
        const updated = await updateNode(body.id, body);
        return NextResponse.json({ ok: true, node: updated });
    } catch (err) {
        return NextResponse.json(
            { error: err instanceof Error ? err.message : 'Failed' },
            { status: 400 },
        );
    }
}

export async function DELETE(req: NextRequest) {
    try {
        const body = (await req.json()) as { id: string };
        if (!body.id) {
            return NextResponse.json({ error: 'id is required' }, { status: 400 });
        }
        await removeNode(body.id);
        return NextResponse.json({ ok: true });
    } catch (err) {
        return NextResponse.json(
            { error: err instanceof Error ? err.message : 'Failed' },
            { status: 400 },
        );
    }
}
