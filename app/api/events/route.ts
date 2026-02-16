import { NextResponse } from 'next/server';
import { listRules, addRule } from '../../lib/event-store';
import type { EventRule } from '../../lib/types';

export async function GET() {
    try {
        const rules = await listRules();
        return NextResponse.json({ rules });
    } catch (err) {
        return NextResponse.json(
            { error: err instanceof Error ? err.message : 'Unknown error' },
            { status: 500 },
        );
    }
}

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const rule: EventRule = {
            id: body.id || `rule-${Date.now()}`,
            eventType: body.eventType || '',
            agentId: body.agentId || 'general',
            template: body.template || '',
            channel: body.channel || 'none',
            conditions: body.conditions || {},
            enabled: body.enabled !== false,
            priority: body.priority ?? 0,
        };

        if (!rule.eventType) {
            return NextResponse.json(
                { error: 'Missing eventType' },
                { status: 400 },
            );
        }

        await addRule(rule);
        return NextResponse.json({ ok: true, rule }, { status: 201 });
    } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        const status = msg.includes('already exists') ? 409 : 500;
        return NextResponse.json({ error: msg }, { status });
    }
}
