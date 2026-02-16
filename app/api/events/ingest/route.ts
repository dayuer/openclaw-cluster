import { NextResponse } from 'next/server';
import { ingest } from '../../../lib/event-engine';
import type { InboundEvent } from '../../../lib/types';

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const event: InboundEvent = {
            type: body.type || '',
            data: body.data || {},
        };

        if (!event.type) {
            return NextResponse.json(
                { error: 'Missing event type' },
                { status: 400 },
            );
        }

        const result = await ingest(event);
        return NextResponse.json(result);
    } catch (err) {
        return NextResponse.json(
            { error: err instanceof Error ? err.message : 'Unknown error' },
            { status: 500 },
        );
    }
}
