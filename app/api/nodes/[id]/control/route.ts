/**
 * POST /api/nodes/[id]/control — control gateway (restart, etc.)
 */
import { NextRequest, NextResponse } from 'next/server';
import { getNode } from '@/app/lib/cluster-store';
import { restartGateway } from '@/app/lib/gateway-client';

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;
    const node = await getNode(id);
    if (!node) {
        return NextResponse.json({ error: 'Node not found' }, { status: 404 });
    }

    const body = (await req.json()) as {
        action?: string;
        delayMs?: number;
        reason?: string;
    };

    const action = body.action || 'restart';

    if (action === 'restart') {
        const result = await restartGateway(
            node.url,
            node.auth?.token,
            body.delayMs,
            body.reason || 'cluster-manager restart',
        );
        if (!result.ok) {
            return NextResponse.json({ error: result.error }, { status: 502 });
        }
        return NextResponse.json({ ok: true, action: 'restart' });
    }

    return NextResponse.json({ error: 'Unknown action' }, { status: 400 });
}
