'use client';

import React, { useEffect, useState, use } from 'react';
import {
    Card, Descriptions, Tag, Spin, Typography, Space, Badge,
    Button, Table, Alert, message,
} from 'antd';
import {
    ArrowLeftOutlined,
    ReloadOutlined,
} from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import type { GatewayConfig, SessionInfo } from '../../lib/types';

const { Title, Text } = Typography;

export default function NodeDetailPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = use(params);
    const router = useRouter();
    const [config, setConfig] = useState<GatewayConfig | null>(null);
    const [sessions, setSessions] = useState<SessionInfo[]>([]);
    const [health, setHealth] = useState<{ online: boolean; error?: string } | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchData = () => {
        setLoading(true);
        Promise.all([
            fetch(`/api/nodes/${id}/health`).then((r) => r.json()),
            fetch(`/api/nodes/${id}/config`).then((r) => r.json()).catch(() => null),
            fetch(`/api/nodes/${id}/sessions`).then((r) => r.json()).catch(() => ({ sessions: [] })),
        ])
            .then(([h, c, s]) => {
                setHealth(h);
                setConfig(c?.error ? null : c);
                setSessions(s?.sessions ?? []);
            })
            .catch(() => message.error('加载失败'))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [id]);

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 120 }}>
                <Spin size="large" />
            </div>
        );
    }

    const enabledChannels = config?.channels
        ? Object.entries(config.channels)
            .filter(([, v]) => v?.enabled)
            .map(([k]) => k)
        : [];

    const agents = config?.agents?.list ?? [];

    return (
        <div style={{ maxWidth: 1000 }}>
            <Space style={{ marginBottom: 16 }}>
                <Button
                    icon={<ArrowLeftOutlined />}
                    onClick={() => router.push('/nodes')}
                >
                    返回
                </Button>
                <Button icon={<ReloadOutlined />} onClick={fetchData}>
                    刷新
                </Button>
            </Space>

            <Title level={3}>
                节点: {id}{' '}
                <Badge
                    status={health?.online ? 'success' : 'error'}
                    text={health?.online ? '在线' : '离线'}
                />
            </Title>

            {!health?.online && health?.error && (
                <Alert
                    type="error"
                    message="连接失败"
                    description={health.error}
                    style={{ marginBottom: 16 }}
                />
            )}

            {/* Config Overview */}
            {config && (
                <Card
                    title="配置概览"
                    style={{ marginBottom: 16, borderRadius: 12 }}
                >
                    <Descriptions column={2} size="small">
                        <Descriptions.Item label="主模型">
                            {config.agents?.defaults?.model?.primary ?? '—'}
                        </Descriptions.Item>
                        <Descriptions.Item label="备用模型">
                            {config.agents?.defaults?.model?.fallbacks?.join(', ') ?? '—'}
                        </Descriptions.Item>
                        <Descriptions.Item label="工作空间">
                            <Text code>{config.agents?.defaults?.workspace ?? '~/.openclaw/workspace'}</Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="端口">
                            {config.gateway?.port ?? 18789}
                        </Descriptions.Item>
                    </Descriptions>
                </Card>
            )}

            {/* Channels */}
            {enabledChannels.length > 0 && (
                <Card title="已启用频道" style={{ marginBottom: 16, borderRadius: 12 }}>
                    <Space wrap>
                        {enabledChannels.map((ch) => (
                            <Tag key={ch} color="green" style={{ fontSize: 13, padding: '4px 12px' }}>
                                {ch}
                            </Tag>
                        ))}
                    </Space>
                </Card>
            )}

            {/* Agents */}
            {agents.length > 0 && (
                <Card title="Agent 列表" style={{ marginBottom: 16, borderRadius: 12 }}>
                    <Space wrap>
                        {agents.map((a) => (
                            <Tag key={a.id} color="purple" style={{ fontSize: 13, padding: '4px 12px' }}>
                                {a.name ?? a.id}
                            </Tag>
                        ))}
                    </Space>
                </Card>
            )}

            {/* Sessions */}
            <Card title={`活跃会话 (${sessions.length})`} style={{ borderRadius: 12 }}>
                {sessions.length === 0 ? (
                    <Text type="secondary">没有活跃会话</Text>
                ) : (
                    <Table
                        columns={[
                            { title: 'Key', dataIndex: 'key', ellipsis: true },
                            { title: 'Agent', dataIndex: 'agentId' },
                            { title: 'Channel', dataIndex: 'channel' },
                            { title: 'Peer', dataIndex: 'peer', ellipsis: true },
                            { title: 'Tokens', dataIndex: 'tokens', width: 90 },
                        ]}
                        dataSource={sessions}
                        rowKey="key"
                        pagination={false}
                        size="small"
                    />
                )}
            </Card>
        </div>
    );
}
