/**
 * GET /api/nodes/[id]/sessions — list sessions on a Gateway
 */
import { NextResponse } from 'next/server';
import { getNode } from '@/app/lib/cluster-store';
import { listSessions } from '@/app/lib/gateway-client';

export async function GET(
    _req: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;
    const node = await getNode(id);
    if (!node) {
        return NextResponse.json({ error: 'Node not found' }, { status: 404 });
    }

    const sessions = await listSessions(node.url, node.auth);
    return NextResponse.json({ sessions });
}
