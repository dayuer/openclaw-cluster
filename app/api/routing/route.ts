import { NextResponse } from 'next/server';
import { routeMulti } from '../../lib/llm-router';
import { getRegistryData } from '../../lib/agent-store';

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const content = body.content || '';

        if (!content.trim()) {
            return NextResponse.json(
                { error: 'Missing content' },
                { status: 400 },
            );
        }

        const registry = await getRegistryData();
        const result = await routeMulti(
            content,
            registry.agents,
            registry.defaultAgentId,
            registry.routerModel,
        );

        return NextResponse.json(result);
    } catch (err) {
        return NextResponse.json(
            { error: err instanceof Error ? err.message : 'Unknown error' },
            { status: 500 },
        );
    }
}
