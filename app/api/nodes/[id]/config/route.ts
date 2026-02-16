/**
 * GET  /api/nodes/[id]/config — get config from Gateway
 * PUT  /api/nodes/[id]/config — patch config on Gateway
 */
import { NextRequest, NextResponse } from 'next/server';
import { getNode } from '@/app/lib/cluster-store';
import { getConfig, patchConfig } from '@/app/lib/gateway-client';

export async function GET(
    _req: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;
    const node = await getNode(id);
    if (!node) {
        return NextResponse.json({ error: 'Node not found' }, { status: 404 });
    }

    const config = await getConfig(node.url, node.auth?.token);
    if (!config) {
        return NextResponse.json(
            { error: 'Cannot reach Gateway' },
            { status: 502 },
        );
    }
    return NextResponse.json(config);
}

export async function PUT(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    const node = await getNode(id);
    if (!node) {
        return NextResponse.json({ error: 'Node not found' }, { status: 404 });
    }

    const body = (await req.json()) as { raw: string; baseHash: string };
    if (!body.raw || !body.baseHash) {
        return NextResponse.json(
            { error: 'raw and baseHash are required' },
            { status: 400 },
        );
    }

    const result = await patchConfig(node.url, body.raw, body.baseHash, node.auth?.token);
    if (!result.ok) {
        return NextResponse.json(
            { error: result.error ?? 'Patch failed' },
            { status: 502 },
        );
    }
    return NextResponse.json({ ok: true });
}
