'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
    Button,
    Card,
    Empty,
    Form,
    Input,
    InputNumber,
    message,
    Modal,
    Popconfirm,
    Select,
    Space,
    Switch,
    Table,
    Tag,
    Typography,
} from 'antd';
import {
    PlusOutlined,
    ReloadOutlined,
    DeleteOutlined,
    EditOutlined,
    SendOutlined,
    TeamOutlined,
} from '@ant-design/icons';
import type { AgentSpec, AgentRegistryData, RouteResult } from '../lib/types';

const { Title, Text } = Typography;
const { TextArea } = Input;

export default function AgentsPage() {
    const [registry, setRegistry] = useState<AgentRegistryData>({
        agents: [],
        routerModel: '',
        defaultAgentId: 'general',
    });
    const [loading, setLoading] = useState(true);
    const [modalOpen, setModalOpen] = useState(false);
    const [editingAgent, setEditingAgent] = useState<AgentSpec | null>(null);
    const [routeInput, setRouteInput] = useState('');
    const [routeResult, setRouteResult] = useState<RouteResult | null>(null);
    const [routing, setRouting] = useState(false);
    const [form] = Form.useForm();

    const fetchAgents = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/agents');
            const data = await res.json();
            setRegistry(data);
        } catch {
            message.error('加载 Agent 列表失败');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchAgents(); }, [fetchAgents]);

    const handleSave = async (values: Record<string, unknown>) => {
        try {
            const agent: AgentSpec = {
                id: String(values.id || ''),
                description: String(values.description || ''),
                systemPromptFile: String(values.systemPromptFile || ''),
                tools: values.tools
                    ? String(values.tools).split(',').map(s => s.trim()).filter(Boolean)
                    : ['*'],
                skills: values.skills
                    ? String(values.skills).split(',').map(s => s.trim()).filter(Boolean)
                    : [],
                temperature: Number(values.temperature ?? 0.7),
                maxTokens: Number(values.maxTokens ?? 8192),
                maxIterations: Number(values.maxIterations ?? 20),
                isDefault: Boolean(values.isDefault),
                keywords: values.keywords
                    ? String(values.keywords).split(',').map(s => s.trim()).filter(Boolean)
                    : [],
            };

            if (editingAgent) {
                await fetch(`/api/agents/${encodeURIComponent(editingAgent.id)}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(agent),
                });
                message.success('Agent 已更新');
            } else {
                const res = await fetch('/api/agents', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(agent),
                });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.error);
                }
                message.success('Agent 已添加');
            }
            setModalOpen(false);
            setEditingAgent(null);
            form.resetFields();
            fetchAgents();
        } catch (err) {
            message.error(err instanceof Error ? err.message : '操作失败');
        }
    };

    const handleDelete = async (id: string) => {
        await fetch(`/api/agents/${encodeURIComponent(id)}`, { method: 'DELETE' });
        message.success('Agent 已删除');
        fetchAgents();
    };

    const handleRoute = async () => {
        if (!routeInput.trim()) return;
        setRouting(true);
        try {
            const res = await fetch('/api/routing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: routeInput }),
            });
            const data = await res.json();
            setRouteResult(data);
        } catch {
            message.error('路由测试失败');
        } finally {
            setRouting(false);
        }
    };

    const openEdit = (agent: AgentSpec) => {
        setEditingAgent(agent);
        form.setFieldsValue({
            ...agent,
            tools: agent.tools.join(', '),
            skills: agent.skills.join(', '),
            keywords: agent.keywords?.join(', ') || '',
        });
        setModalOpen(true);
    };

    const openAdd = () => {
        setEditingAgent(null);
        form.resetFields();
        setModalOpen(true);
    };

    const columns = [
        {
            title: '默认',
            dataIndex: 'isDefault',
            width: 60,
            render: (v: boolean) => v ? <Tag color="red">默认</Tag> : null,
        },
        { title: 'ID', dataIndex: 'id', width: 120 },
        { title: '描述', dataIndex: 'description', ellipsis: true },
        {
            title: '工具',
            dataIndex: 'tools',
            width: 140,
            render: (tools: string[]) => tools.map(t => (
                <Tag key={t} color={t === '*' ? 'gold' : 'blue'}>{t}</Tag>
            )),
        },
        {
            title: '温度',
            dataIndex: 'temperature',
            width: 70,
            render: (v: number) => v.toFixed(1),
        },
        {
            title: '关键词',
            dataIndex: 'keywords',
            width: 160,
            render: (kws: string[] | undefined) =>
                kws?.map(k => <Tag key={k}>{k}</Tag>) || '—',
        },
        {
            title: '操作',
            width: 120,
            render: (_: unknown, record: AgentSpec) => (
                <Space size="small">
                    <Button
                        type="text"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => openEdit(record)}
                    />
                    <Popconfirm
                        title={`删除 ${record.id}?`}
                        onConfirm={() => handleDelete(record.id)}
                    >
                        <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
                <Title level={3} style={{ margin: 0 }}>
                    <TeamOutlined style={{ marginRight: 8 }} />
                    Agent 管理
                </Title>
                <Space>
                    <Button icon={<ReloadOutlined />} onClick={fetchAgents}>刷新</Button>
                    <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>
                        添加 Agent
                    </Button>
                </Space>
            </div>

            <Table
                dataSource={registry.agents}
                columns={columns}
                rowKey="id"
                loading={loading}
                pagination={false}
                locale={{ emptyText: <Empty description="还没有 Agent — 点击「添加 Agent」开始" /> }}
                style={{ marginBottom: 24 }}
            />

            {/* 路由测试面板 */}
            <Card
                title="🧠 路由测试"
                extra={
                    <Text type="secondary" style={{ fontSize: 12 }}>
                        Router Model: {registry.routerModel || '未配置'}
                    </Text>
                }
            >
                <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
                    <Input
                        placeholder="输入消息内容，测试 LLM 路由..."
                        value={routeInput}
                        onChange={e => setRouteInput(e.target.value)}
                        onPressEnter={handleRoute}
                        style={{ flex: 1 }}
                    />
                    <Button
                        type="primary"
                        icon={<SendOutlined />}
                        loading={routing}
                        onClick={handleRoute}
                    >
                        路由
                    </Button>
                </Space.Compact>

                {routeResult && (
                    <div style={{
                        padding: 16,
                        background: 'var(--sidebar-bg)',
                        borderRadius: 8,
                        color: '#ccc',
                    }}>
                        <div style={{ marginBottom: 8 }}>
                            <Text strong style={{ color: '#fff' }}>Primary: </Text>
                            <Tag color="red">{routeResult.primary}</Tag>
                        </div>
                        {routeResult.related.length > 0 && (
                            <div style={{ marginBottom: 8 }}>
                                <Text strong style={{ color: '#fff' }}>Related: </Text>
                                {routeResult.related.map(r => (
                                    <Tag key={r} color="orange">{r}</Tag>
                                ))}
                            </div>
                        )}
                        {Object.keys(routeResult.subTasks).length > 0 && (
                            <div style={{ marginBottom: 8 }}>
                                <Text strong style={{ color: '#fff' }}>Sub-Tasks:</Text>
                                {Object.entries(routeResult.subTasks).map(([agent, task]) => (
                                    <div key={agent} style={{ marginLeft: 16, fontSize: 13 }}>
                                        <Tag color="orange">{agent}</Tag> {task}
                                    </div>
                                ))}
                            </div>
                        )}
                        <div style={{ marginBottom: 4 }}>
                            <Text strong style={{ color: '#fff' }}>Reason: </Text>
                            <Text style={{ color: '#aaa' }}>{routeResult.reason}</Text>
                        </div>
                        {routeResult.domains.length > 0 && (
                            <div>
                                <Text strong style={{ color: '#fff' }}>Domains: </Text>
                                {routeResult.domains.map(d => (
                                    <Tag key={d} color="geekblue">{d}</Tag>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </Card>

            {/* Agent 添加/编辑 Modal */}
            <Modal
                title={editingAgent ? `编辑 ${editingAgent.id}` : '添加 Agent'}
                open={modalOpen}
                onCancel={() => { setModalOpen(false); setEditingAgent(null); }}
                footer={null}
                width={560}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSave}
                    initialValues={{
                        temperature: 0.7,
                        maxTokens: 8192,
                        maxIterations: 20,
                        tools: '*',
                    }}
                >
                    <Form.Item name="id" label="Agent ID" rules={[{ required: true }]}>
                        <Input disabled={!!editingAgent} placeholder="e.g. general" />
                    </Form.Item>
                    <Form.Item name="description" label="描述" rules={[{ required: true }]}>
                        <Input placeholder="e.g. 翔哥 — 综合闲聊与接单策略" />
                    </Form.Item>
                    <Form.Item name="systemPromptFile" label="System Prompt 文件">
                        <Input placeholder="e.g. team/roles/general.md" />
                    </Form.Item>
                    <Form.Item name="tools" label="工具 (逗号分隔)">
                        <Input placeholder="* 表示全部, 或 knowledge_search, web_search" />
                    </Form.Item>
                    <Form.Item name="skills" label="Skills (逗号分隔)">
                        <Input placeholder="* 表示全部, 或 stock, feishu" />
                    </Form.Item>
                    <Form.Item name="keywords" label="关键词触发 (逗号分隔)">
                        <Input placeholder="e.g. 法律, 律师, 维权 — 跳过 LLM 路由直接匹配" />
                    </Form.Item>
                    <Space>
                        <Form.Item name="temperature" label="温度">
                            <InputNumber min={0} max={2} step={0.1} style={{ width: 100 }} />
                        </Form.Item>
                        <Form.Item name="maxTokens" label="Max Tokens">
                            <InputNumber min={256} max={65536} style={{ width: 120 }} />
                        </Form.Item>
                        <Form.Item name="maxIterations" label="Max Iterations">
                            <InputNumber min={1} max={100} style={{ width: 100 }} />
                        </Form.Item>
                    </Space>
                    <Form.Item name="isDefault" label="默认 Agent" valuePropName="checked">
                        <Switch />
                    </Form.Item>
                    <Form.Item>
                        <Button type="primary" htmlType="submit" block>
                            {editingAgent ? '保存修改' : '添加'}
                        </Button>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
