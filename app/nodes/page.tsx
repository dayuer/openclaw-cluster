'use client';

import React, { useEffect, useState, useCallback } from 'react';
import {
    Table, Button, Modal, Form, Input, Select, Tag,
    Space, Typography, Badge, message, Popconfirm,
} from 'antd';
import {
    PlusOutlined,
    ReloadOutlined,
    DeleteOutlined,
    EditOutlined,
    LinkOutlined,
} from '@ant-design/icons';
import type { NodeWithStatus, GatewayNode } from '../lib/types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

export default function NodesPage() {
    const [nodes, setNodes] = useState<NodeWithStatus[]>([]);
    const [loading, setLoading] = useState(true);
    const [modalOpen, setModalOpen] = useState(false);
    const [editNode, setEditNode] = useState<GatewayNode | null>(null);
    const [form] = Form.useForm();

    const fetchNodes = useCallback(() => {
        setLoading(true);
        fetch('/api/nodes')
            .then((r) => r.json())
            .then((data) => setNodes(data.nodes ?? []))
            .catch(() => message.error('加载节点失败'))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        fetchNodes();
    }, [fetchNodes]);

    const handleAdd = () => {
        setEditNode(null);
        form.resetFields();
        setModalOpen(true);
    };

    const handleEdit = (node: GatewayNode) => {
        setEditNode(node);
        form.setFieldsValue({
            ...node,
            tags: (node.tags ?? []).join(', '),
            token: node.auth?.token ?? '',
        });
        setModalOpen(true);
    };

    const handleDelete = async (id: string) => {
        await fetch('/api/nodes', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id }),
        });
        message.success('已删除');
        fetchNodes();
    };

    const handleSubmit = async () => {
        const values = await form.validateFields();
        const payload = {
            id: editNode?.id ?? values.id,
            name: values.name,
            url: values.url,
            tags: (values.tags as string)
                ?.split(',')
                .map((t: string) => t.trim())
                .filter(Boolean) ?? [],
            auth: values.token ? { token: values.token } : undefined,
        };

        const method = editNode ? 'PUT' : 'POST';
        const res = await fetch('/api/nodes', {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (res.ok) {
            message.success(editNode ? '已更新' : '已添加');
            setModalOpen(false);
            fetchNodes();
        } else {
            const err = await res.json();
            message.error(err.error ?? '操作失败');
        }
    };

    const columns: ColumnsType<NodeWithStatus> = [
        {
            title: '状态',
            dataIndex: ['status', 'online'],
            width: 70,
            render: (online: boolean) => (
                <Badge status={online ? 'success' : 'error'} text={online ? '在线' : '离线'} />
            ),
        },
        {
            title: '名称',
            dataIndex: 'name',
            render: (name: string, record: NodeWithStatus) => (
                <a href={`/nodes/${record.id}`} style={{ color: 'var(--accent)' }}>
                    {name}
                </a>
            ),
        },
        {
            title: '地址',
            dataIndex: 'url',
            render: (url: string) => (
                <span style={{ fontFamily: 'JetBrains Mono', fontSize: 13 }}>{url}</span>
            ),
        },
        {
            title: '模型',
            dataIndex: ['status', 'model'],
            render: (model?: string) => model ?? '—',
        },
        {
            title: '会话',
            dataIndex: ['status', 'sessionCount'],
            width: 80,
            render: (count?: number) => count ?? '—',
        },
        {
            title: '标签',
            dataIndex: 'tags',
            render: (tags: string[]) =>
                (tags ?? []).map((t) => (
                    <Tag key={t} color="blue">
                        {t}
                    </Tag>
                )),
        },
        {
            title: '操作',
            width: 120,
            render: (_: unknown, record: NodeWithStatus) => (
                <Space>
                    <Button
                        type="text"
                        icon={<EditOutlined />}
                        size="small"
                        onClick={() => handleEdit(record)}
                    />
                    <Popconfirm
                        title="确定删除该节点？"
                        onConfirm={() => handleDelete(record.id)}
                    >
                        <Button type="text" danger icon={<DeleteOutlined />} size="small" />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div style={{ maxWidth: 1200 }}>
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: 16,
                }}
            >
                <Title level={3} style={{ margin: 0 }}>
                    节点管理
                </Title>
                <Space>
                    <Button icon={<ReloadOutlined />} onClick={fetchNodes} loading={loading}>
                        刷新
                    </Button>
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                        添加节点
                    </Button>
                </Space>
            </div>

            <Table
                columns={columns}
                dataSource={nodes}
                rowKey="id"
                loading={loading}
                pagination={false}
                style={{
                    borderRadius: 12,
                    overflow: 'hidden',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                }}
            />

            {/* Add / Edit Modal */}
            <Modal
                title={editNode ? '编辑节点' : '添加节点'}
                open={modalOpen}
                onOk={handleSubmit}
                onCancel={() => setModalOpen(false)}
                okText={editNode ? '保存' : '添加'}
                cancelText="取消"
            >
                <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
                    {!editNode && (
                        <Form.Item
                            name="id"
                            label="节点 ID"
                            rules={[{ required: true, message: '请输入节点 ID' }]}
                        >
                            <Input
                                prefix={<LinkOutlined />}
                                placeholder="prod-1"
                            />
                        </Form.Item>
                    )}
                    <Form.Item
                        name="name"
                        label="名称"
                        rules={[{ required: true, message: '请输入名称' }]}
                    >
                        <Input placeholder="生产节点" />
                    </Form.Item>
                    <Form.Item
                        name="url"
                        label="Gateway 地址"
                        rules={[{ required: true, message: '请输入 WebSocket 地址' }]}
                    >
                        <Input
                            placeholder="ws://10.0.1.100:18789"
                            style={{ fontFamily: 'JetBrains Mono' }}
                        />
                    </Form.Item>
                    <Form.Item name="tags" label="标签 (逗号分隔)">
                        <Select
                            mode="tags"
                            placeholder="production, staging"
                            tokenSeparators={[',']}
                        />
                    </Form.Item>
                    <Form.Item name="token" label="Auth Token (可选)">
                        <Input.Password placeholder="Bearer token" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
