import { NextResponse } from 'next/server';
import { listAgents, addAgent, getRegistryData, updateRegistrySettings } from '../../lib/agent-store';
import type { AgentSpec } from '../../lib/types';

export async function GET() {
    try {
        const data = await getRegistryData();
        return NextResponse.json(data);
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

        // If body has 'routerModel' or 'defaultAgentId', update settings
        if (body.routerModel !== undefined || body.defaultAgentId !== undefined) {
            await updateRegistrySettings(body);
            return NextResponse.json({ ok: true });
        }

        // Otherwise, add a new agent
        const agent: AgentSpec = {
            id: body.id || '',
            description: body.description || '',
            systemPromptFile: body.systemPromptFile || '',
            tools: body.tools || ['*'],
            skills: body.skills || [],
            temperature: body.temperature ?? 0.7,
            maxTokens: body.maxTokens ?? 8192,
            maxIterations: body.maxIterations ?? 20,
            isDefault: body.isDefault || false,
            keywords: body.keywords || [],
        };

        if (!agent.id) {
            return NextResponse.json({ error: 'Missing agent id' }, { status: 400 });
        }

        await addAgent(agent);
        return NextResponse.json({ ok: true, agent }, { status: 201 });
    } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        const status = msg.includes('already exists') ? 409 : 500;
        return NextResponse.json({ error: msg }, { status });
    }
}
