/**
 * GET /api/nodes/[id]/health — health check for a single node
 */
import { NextResponse } from 'next/server';
import { getNode } from '@/app/lib/cluster-store';
import { healthCheck } from '@/app/lib/gateway-client';

export async function GET(
    _req: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;
    const node = await getNode(id);
    if (!node) {
        return NextResponse.json({ error: 'Node not found' }, { status: 404 });
    }

    const health = await healthCheck(node.url, node.auth);
    return NextResponse.json(health);
}
