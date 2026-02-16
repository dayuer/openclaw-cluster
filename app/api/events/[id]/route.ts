import { NextResponse } from 'next/server';
import { getRule, updateRule, removeRule } from '../../../lib/event-store';

export async function GET(
    _request: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    const { id } = await params;
    const rule = await getRule(id);
    if (!rule) {
        return NextResponse.json({ error: 'Rule not found' }, { status: 404 });
    }
    return NextResponse.json(rule);
}

export async function PUT(
    request: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    try {
        const { id } = await params;
        const body = await request.json();
        await updateRule(id, body);
        return NextResponse.json({ ok: true });
    } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        const status = msg.includes('not found') ? 404 : 500;
        return NextResponse.json({ error: msg }, { status });
    }
}

export async function DELETE(
    _request: Request,
    { params }: { params: Promise<{ id: string }> },
) {
    try {
        const { id } = await params;
        await removeRule(id);
        return NextResponse.json({ ok: true });
    } catch (err) {
        return NextResponse.json(
            { error: err instanceof Error ? err.message : 'Unknown error' },
            { status: 500 },
        );
    }
}
