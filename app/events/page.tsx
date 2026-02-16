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
    ThunderboltOutlined,
    PlayCircleOutlined,
} from '@ant-design/icons';
import type { EventRule, EventDispatchResult } from '../lib/types';

const { Title, Text } = Typography;
const { TextArea } = Input;

export default function EventsPage() {
    const [rules, setRules] = useState<EventRule[]>([]);
    const [loading, setLoading] = useState(true);
    const [modalOpen, setModalOpen] = useState(false);
    const [editingRule, setEditingRule] = useState<EventRule | null>(null);
    const [testEvent, setTestEvent] = useState('{\n  "type": "payment.success",\n  "data": {\n    "user": { "name": "张三" },\n    "amount": 299\n  }\n}');
    const [testResult, setTestResult] = useState<{
        matched: EventDispatchResult[];
        prompt: Record<string, string>;
    } | null>(null);
    const [testing, setTesting] = useState(false);
    const [form] = Form.useForm();

    const fetchRules = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/events');
            const data = await res.json();
            setRules(data.rules || []);
        } catch {
            message.error('加载事件规则失败');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchRules(); }, [fetchRules]);

    const handleSave = async (values: Record<string, unknown>) => {
        try {
            let conditions: Record<string, unknown> = {};
            if (values.conditions) {
                try {
                    conditions = JSON.parse(String(values.conditions));
                } catch {
                    message.error('条件必须是合法 JSON');
                    return;
                }
            }

            const rule: Partial<EventRule> = {
                eventType: String(values.eventType || ''),
                agentId: String(values.agentId || 'general'),
                template: String(values.template || ''),
                channel: String(values.channel || 'none'),
                conditions,
                enabled: values.enabled !== false,
                priority: Number(values.priority ?? 0),
            };

            if (editingRule) {
                await fetch(`/api/events/${encodeURIComponent(editingRule.id)}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(rule),
                });
                message.success('规则已更新');
            } else {
                rule.id = `rule-${Date.now()}`;
                const res = await fetch('/api/events', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(rule),
                });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.error);
                }
                message.success('规则已添加');
            }
            setModalOpen(false);
            setEditingRule(null);
            form.resetFields();
            fetchRules();
        } catch (err) {
            message.error(err instanceof Error ? err.message : '操作失败');
        }
    };

    const handleDelete = async (id: string) => {
        await fetch(`/api/events/${encodeURIComponent(id)}`, { method: 'DELETE' });
        message.success('规则已删除');
        fetchRules();
    };

    const handleToggle = async (rule: EventRule) => {
        await fetch(`/api/events/${encodeURIComponent(rule.id)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: !rule.enabled }),
        });
        fetchRules();
    };

    const handleTest = async () => {
        setTesting(true);
        try {
            const event = JSON.parse(testEvent);
            const res = await fetch('/api/events/ingest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(event),
            });
            const data = await res.json();
            setTestResult(data);
        } catch (err) {
            message.error(err instanceof Error ? err.message : 'JSON 格式错误');
        } finally {
            setTesting(false);
        }
    };

    const openEdit = (rule: EventRule) => {
        setEditingRule(rule);
        form.setFieldsValue({
            ...rule,
            conditions: JSON.stringify(rule.conditions, null, 2),
        });
        setModalOpen(true);
    };

    const openAdd = () => {
        setEditingRule(null);
        form.resetFields();
        setModalOpen(true);
    };

    const columns = [
        {
            title: '状态',
            dataIndex: 'enabled',
            width: 70,
            render: (enabled: boolean, record: EventRule) => (
                <Switch size="small" checked={enabled} onChange={() => handleToggle(record)} />
            ),
        },
        {
            title: '事件类型',
            dataIndex: 'eventType',
            width: 180,
            render: (v: string) => <Tag color="volcano">{v}</Tag>,
        },
        {
            title: '目标 Agent',
            dataIndex: 'agentId',
            width: 120,
            render: (v: string) => <Tag color="blue">{v}</Tag>,
        },
        { title: '模板', dataIndex: 'template', ellipsis: true },
        {
            title: '渠道',
            dataIndex: 'channel',
            width: 80,
            render: (v: string) => <Tag>{v}</Tag>,
        },
        {
            title: '优先级',
            dataIndex: 'priority',
            width: 70,
            sorter: (a: EventRule, b: EventRule) => b.priority - a.priority,
        },
        {
            title: '操作',
            width: 120,
            render: (_: unknown, record: EventRule) => (
                <Space size="small">
                    <Button
                        type="text"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => openEdit(record)}
                    />
                    <Popconfirm
                        title={`删除规则 ${record.id}?`}
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
                    <ThunderboltOutlined style={{ marginRight: 8 }} />
                    事件引擎
                </Title>
                <Space>
                    <Button icon={<ReloadOutlined />} onClick={fetchRules}>刷新</Button>
                    <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>
                        添加规则
                    </Button>
                </Space>
            </div>

            <Table
                dataSource={rules}
                columns={columns}
                rowKey="id"
                loading={loading}
                pagination={false}
                locale={{ emptyText: <Empty description="还没有事件规则 — 点击「添加规则」开始" /> }}
                style={{ marginBottom: 24 }}
            />

            {/* 事件测试面板 */}
            <Card title="⚡ 事件测试">
                <TextArea
                    rows={6}
                    value={testEvent}
                    onChange={e => setTestEvent(e.target.value)}
                    style={{ fontFamily: 'var(--font-mono)', marginBottom: 12 }}
                />
                <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    loading={testing}
                    onClick={handleTest}
                    style={{ marginBottom: 12 }}
                >
                    注入事件
                </Button>

                {testResult && (
                    <div style={{
                        padding: 16,
                        background: 'var(--sidebar-bg)',
                        borderRadius: 8,
                        color: '#ccc',
                    }}>
                        {testResult.matched.length === 0 ? (
                            <Text style={{ color: '#999' }}>没有匹配的规则</Text>
                        ) : (
                            <>
                                <div style={{ marginBottom: 8 }}>
                                    <Text strong style={{ color: '#fff' }}>
                                        匹配 {testResult.matched.length} 条规则:
                                    </Text>
                                </div>
                                {testResult.matched.map((m, i) => (
                                    <div key={i} style={{
                                        marginBottom: 12,
                                        padding: 12,
                                        background: 'rgba(255,255,255,0.05)',
                                        borderRadius: 6,
                                    }}>
                                        <div style={{ marginBottom: 6 }}>
                                            <Tag color="volcano">{m.ruleId}</Tag>
                                            <Tag color="blue">→ {m.agentId}</Tag>
                                        </div>
                                        <pre style={{
                                            margin: 0,
                                            fontSize: 12,
                                            color: '#aaa',
                                            whiteSpace: 'pre-wrap',
                                        }}>
                                            {testResult.prompt[m.ruleId]}
                                        </pre>
                                    </div>
                                ))}
                            </>
                        )}
                    </div>
                )}
            </Card>

            {/* 规则添加/编辑 Modal */}
            <Modal
                title={editingRule ? `编辑规则 ${editingRule.id}` : '添加事件规则'}
                open={modalOpen}
                onCancel={() => { setModalOpen(false); setEditingRule(null); }}
                footer={null}
                width={560}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSave}
                    initialValues={{
                        enabled: true,
                        priority: 0,
                        channel: 'none',
                        agentId: 'general',
                    }}
                >
                    <Form.Item
                        name="eventType"
                        label="事件类型"
                        rules={[{ required: true }]}
                    >
                        <Input placeholder="e.g. payment.success 或 payment.*" />
                    </Form.Item>
                    <Form.Item name="agentId" label="目标 Agent" rules={[{ required: true }]}>
                        <Input placeholder="e.g. general, sales" />
                    </Form.Item>
                    <Form.Item name="template" label="Prompt 模板">
                        <TextArea
                            rows={3}
                            placeholder="支持 {key} 占位符，e.g. 用户 {user.name} 支付了 {amount} 元"
                        />
                    </Form.Item>
                    <Form.Item name="channel" label="响应渠道">
                        <Input placeholder="e.g. wechat, none" />
                    </Form.Item>
                    <Form.Item name="conditions" label="匹配条件 (JSON)">
                        <TextArea
                            rows={2}
                            placeholder='e.g. {"status": "active"}'
                            style={{ fontFamily: 'var(--font-mono)' }}
                        />
                    </Form.Item>
                    <Space>
                        <Form.Item name="priority" label="优先级">
                            <InputNumber min={0} max={100} style={{ width: 100 }} />
                        </Form.Item>
                        <Form.Item name="enabled" label="启用" valuePropName="checked">
                            <Switch />
                        </Form.Item>
                    </Space>
                    <Form.Item>
                        <Button type="primary" htmlType="submit" block>
                            {editingRule ? '保存修改' : '添加'}
                        </Button>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
