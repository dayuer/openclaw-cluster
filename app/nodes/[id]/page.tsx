'use client';

import React, { useEffect, useState, use } from 'react';
import {
    Card, Descriptions, Tag, Spin, Typography, Space, Badge,
    Button, Table, Alert, message, Modal, Input, Popconfirm,
    Divider, Tabs, Tooltip,
} from 'antd';
import {
    ArrowLeftOutlined,
    ReloadOutlined,
    EditOutlined,
    SendOutlined,
    DeleteOutlined,
    UndoOutlined,
    PoweroffOutlined,
    CopyOutlined,

} from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import type { GatewayConfig, SessionInfo } from '../../lib/types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface NodeHealth {
    online: boolean;
    error?: string;
    model?: string;
    version?: string;
}

interface ConfigSnapshot {
    hash?: string;
    raw?: string;
    config?: GatewayConfig;
}

export default function NodeDetailPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = use(params);
    const router = useRouter();
    const [config, setConfig] = useState<ConfigSnapshot | null>(null);
    const [sessions, setSessions] = useState<SessionInfo[]>([]);
    const [health, setHealth] = useState<NodeHealth | null>(null);
    const [loading, setLoading] = useState(true);
    const [configModalOpen, setConfigModalOpen] = useState(false);
    const [editingConfig, setEditingConfig] = useState('');
    const [messageApi, contextHolder] = message.useMessage();
    const [sendModalOpen, setSendModalOpen] = useState(false);
    const [selectedSession, setSelectedSession] = useState<SessionInfo | null>(null);
    const [sendMessage, setSendMessage] = useState('');

    const fetchData = () => {
        setLoading(true);
        Promise.all([
            fetch(`/api/nodes/${id}/health`).then((r) => r.json()),
            fetch(`/api/nodes/${id}/config`).then((r) => r.json()).catch(() => null),
            fetch(`/api/nodes/${id}/sessions`).then((r) => r.json()).catch(() => ({ sessions: [] })),
        ])
            .then(([h, c, s]) => {
                setHealth(h);
                if (c && !c.error) {
                    setConfig(c);
                }
                setSessions(s?.sessions ?? []);
            })
            .catch(() => messageApi.error('加载失败'))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [id]);

    const handleRestart = async () => {
        try {
            const res = await fetch(`/api/nodes/${id}/control`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'restart' }),
            });
            const data = await res.json();
            if (data.ok) {
                messageApi.success('重启命令已发送');
            } else {
                messageApi.error(data.error || '重启失败');
            }
        } catch {
            messageApi.error('重启失败');
        }
    };

    const handleConfigEdit = () => {
        if (config?.raw) {
            setEditingConfig(config.raw);
            setConfigModalOpen(true);
        }
    };

    const handleConfigSave = async () => {
        if (!config?.hash) {
            messageApi.error('无法保存：缺少配置版本');
            return;
        }

        try {
            const res = await fetch(`/api/nodes/${id}/config`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    raw: editingConfig,
                    baseHash: config.hash,
                }),
            });
            const data = await res.json();
            if (data.ok) {
                messageApi.success('配置已保存，Gateway 将重启');
                setConfigModalOpen(false);
                fetchData();
            } else {
                messageApi.error(data.error || '保存失败');
            }
        } catch {
            messageApi.error('保存失败');
        }
    };

    const handleSessionAction = async (session: SessionInfo, action: 'send' | 'reset' | 'delete') => {
        if (action === 'send') {
            setSelectedSession(session);
            setSendMessage('');
            setSendModalOpen(true);
            return;
        }

        const url = `/api/nodes/${id}/sessions/${encodeURIComponent(session.key)}?action=${action}`;
        try {
            const res = await fetch(url, { method: 'DELETE' });
            const data = await res.json();
            if (data.ok) {
                messageApi.success(action === 'reset' ? '会话已重置' : '会话已删除');
                fetchData();
            } else {
                messageApi.error(data.error || '操作失败');
            }
        } catch {
            messageApi.error('操作失败');
        }
    };

    const handleSend = async () => {
        if (!selectedSession || !sendMessage.trim()) return;

        try {
            const res = await fetch(`/api/nodes/${id}/sessions/${encodeURIComponent(selectedSession.key)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: sendMessage }),
            });
            const data = await res.json();
            if (data.ok) {
                messageApi.success('消息已发送');
                setSendModalOpen(false);
            } else {
                messageApi.error(data.error || '发送失败');
            }
        } catch {
            messageApi.error('发送失败');
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        messageApi.success('已复制');
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 120 }}>
                <Spin size="large" />
            </div>
        );
    }

    const configObj = config?.config;
    const enabledChannels = configObj?.channels
        ? Object.entries(configObj.channels)
            .filter(([, v]) => v?.enabled)
            .map(([k]) => k)
        : [];

    const agents = configObj?.agents?.list ?? [];

    const sessionColumns = [
        {
            title: 'Key',
            dataIndex: 'key',
            ellipsis: true,
            width: 200,
            render: (key: string) => (
                <Space>
                    <Text code style={{ fontSize: 11 }}>{key}</Text>
                    <Button
                        type="text"
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => copyToClipboard(key)}
                    />
                </Space>
            ),
        },
        { title: 'Agent', dataIndex: 'agentId', width: 100 },
        { title: 'Channel', dataIndex: 'channel', width: 100 },
        { title: 'Peer', dataIndex: 'peer', ellipsis: true },
        {
            title: 'Tokens',
            render: (_: unknown, r: SessionInfo) => (
                <Text type="secondary">
                    {r.inputTokens ?? 0} / {r.outputTokens ?? 0}
                </Text>
            ),
            width: 120,
        },
        {
            title: '操作',
            width: 160,
            render: (_: unknown, record: SessionInfo) => (
                <Space size="small">
                    <Tooltip title="发送消息">
                        <Button
                            type="text"
                            size="small"
                            icon={<SendOutlined />}
                            onClick={() => handleSessionAction(record, 'send')}
                        />
                    </Tooltip>
                    <Tooltip title="重置会话">
                        <Button
                            type="text"
                            size="small"
                            icon={<UndoOutlined />}
                            onClick={() => handleSessionAction(record, 'reset')}
                        />
                    </Tooltip>
                    <Popconfirm
                        title="删除此会话？"
                        onConfirm={() => handleSessionAction(record, 'delete')}
                    >
                        <Tooltip title="删除会话">
                            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                        </Tooltip>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div style={{ maxWidth: 1200 }}>
            {contextHolder}

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
                {health?.online && (
                    <Popconfirm
                        title="确定要重启 Gateway 吗？"
                        description="这会断开所有连接"
                        onConfirm={handleRestart}
                    >
                        <Button danger icon={<PoweroffOutlined />}>
                            重启
                        </Button>
                    </Popconfirm>
                )}
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

            <Tabs
                defaultActiveKey="overview"
                items={[
                    {
                        key: 'overview',
                        label: '概览',
                        children: (
                            <Space direction="vertical" style={{ width: '100%' }} size="middle">
                                {/* Config Overview */}
                                {configObj && (
                                    <Card title="配置概览" style={{ borderRadius: 12 }}>
                                        <Descriptions column={2} size="small">
                                            <Descriptions.Item label="主模型">
                                                {configObj.agents?.defaults?.model?.primary ?? '—'}
                                            </Descriptions.Item>
                                            <Descriptions.Item label="备用模型">
                                                {configObj.agents?.defaults?.model?.fallbacks?.join(', ') ?? '—'}
                                            </Descriptions.Item>
                                            <Descriptions.Item label="工作空间">
                                                <Text code>{configObj.agents?.defaults?.workspace ?? '~/.openclaw/workspace'}</Text>
                                            </Descriptions.Item>
                                            <Descriptions.Item label="端口">
                                                {configObj.gateway?.port ?? 18789}
                                            </Descriptions.Item>
                                            <Descriptions.Item label="版本">
                                                {health?.version ?? '—'}
                                            </Descriptions.Item>
                                        </Descriptions>
                                    </Card>
                                )}

                                {/* Channels */}
                                {enabledChannels.length > 0 && (
                                    <Card title="已启用频道" style={{ borderRadius: 12 }}>
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
                                    <Card title="Agent 列表" style={{ borderRadius: 12 }}>
                                        <Space wrap>
                                            {agents.map((a) => (
                                                <Tag key={a.id} color="purple" style={{ fontSize: 13, padding: '4px 12px' }}>
                                                    {a.name ?? a.id}
                                                </Tag>
                                            ))}
                                        </Space>
                                    </Card>
                                )}
                            </Space>
                        ),
                    },
                    {
                        key: 'config',
                        label: (
                            <span>
                                配置
                                <Button
                                    type="link"
                                    size="small"
                                    icon={<EditOutlined />}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        handleConfigEdit();
                                    }}
                                >
                                    编辑
                                </Button>
                            </span>
                        ),
                        children: (
                            <Card style={{ borderRadius: 12 }}>
                                <pre style={{
                                    background: 'var(--sidebar-bg)',
                                    padding: 16,
                                    borderRadius: 8,
                                    overflow: 'auto',
                                    maxHeight: 600,
                                    fontSize: 12,
                                    fontFamily: 'JetBrains Mono, monospace',
                                }}>
                                    {config?.raw || '无法获取配置'}
                                </pre>
                            </Card>
                        ),
                    },
                    {
                        key: 'sessions',
                        label: `会话 (${sessions.length})`,
                        children: (
                            <Card style={{ borderRadius: 12 }}>
                                {sessions.length === 0 ? (
                                    <Text type="secondary">没有活跃会话</Text>
                                ) : (
                                    <Table
                                        columns={sessionColumns}
                                        dataSource={sessions}
                                        rowKey="key"
                                        pagination={false}
                                        size="small"
                                    />
                                )}
                            </Card>
                        ),
                    },
                ]}
            />

            {/* Config Edit Modal */}
            <Modal
                title="编辑配置"
                open={configModalOpen}
                onOk={handleConfigSave}
                onCancel={() => setConfigModalOpen(false)}
                okText="保存并重启"
                cancelText="取消"
                width={800}
                okButtonProps={{ danger: true }}
            >
                <Alert
                    type="warning"
                    message="保存配置后 Gateway 将自动重启"
                    style={{ marginBottom: 16 }}
                />
                <TextArea
                    value={editingConfig}
                    onChange={(e) => setEditingConfig(e.target.value)}
                    rows={20}
                    style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
                />
            </Modal>

            {/* Send Message Modal */}
            <Modal
                title={`发送消息到 ${selectedSession?.key?.slice(0, 20)}...`}
                open={sendModalOpen}
                onOk={handleSend}
                onCancel={() => setSendModalOpen(false)}
                okText="发送"
                cancelText="取消"
            >
                <Paragraph type="secondary">
                    会话: {selectedSession?.key}
                </Paragraph>
                <TextArea
                    value={sendMessage}
                    onChange={(e) => setSendMessage(e.target.value)}
                    placeholder="输入要发送的消息..."
                    rows={4}
                />
            </Modal>
        </div>
    );
}

