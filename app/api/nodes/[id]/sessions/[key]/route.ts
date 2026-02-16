/**
 * POST /api/nodes/[id]/sessions/[key] — send message to session
 * DELETE /api/nodes/[id]/sessions/[key] — delete or reset session
 */
import { NextRequest, NextResponse } from 'next/server';
import { getNode } from '@/app/lib/cluster-store';
import { sendToSession, resetSession, deleteSession } from '@/app/lib/gateway-client';

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ id: string; key: string }> },
) {
    const { id, key } = await params;
    const node = await getNode(id);
    if (!node) {
        return NextResponse.json({ error: 'Node not found' }, { status: 404 });
    }

    const body = (await req.json()) as { message?: string };
    if (!body.message) {
        return NextResponse.json({ error: 'message is required' }, { status: 400 });
    }

    const result = await sendToSession(node.url, key, body.message, node.auth?.token);
    if (!result.ok) {
        return NextResponse.json({ error: result.error }, { status: 502 });
    }
    return NextResponse.json({ ok: true });
}

export async function DELETE(
    req: NextRequest,
    { params }: { params: Promise<{ id: string; key: string }> },
) {
    const { id, key } = await params;
    const node = await getNode(id);
    if (!node) {
        return NextResponse.json({ error: 'Node not found' }, { status: 404 });
    }

    const { searchParams } = new URL(req.url);
    const action = searchParams.get('action') || 'delete';

    let result;
    if (action === 'reset') {
        result = await resetSession(node.url, key, node.auth?.token);
    } else {
        result = await deleteSession(node.url, key, node.auth?.token);
    }

    if (!result.ok) {
        return NextResponse.json({ error: result.error }, { status: 502 });
    }
    return NextResponse.json({ ok: true, action });
}
