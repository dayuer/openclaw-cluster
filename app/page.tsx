'use client';

import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Tag, Spin, Typography, Space, Badge, Empty } from 'antd';
import {
    ClusterOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    MessageOutlined,
} from '@ant-design/icons';
import type { NodeWithStatus } from './lib/types';

const { Title, Text } = Typography;

export default function DashboardPage() {
    const [nodes, setNodes] = useState<NodeWithStatus[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/nodes')
            .then((r) => r.json())
            .then((data) => setNodes(data.nodes ?? []))
            .catch(() => setNodes([]))
            .finally(() => setLoading(false));
    }, []);

    const online = nodes.filter((n) => n.status.online).length;
    const offline = nodes.length - online;
    const sessions = nodes.reduce((sum, n) => sum + (n.status.sessionCount ?? 0), 0);

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 120 }}>
                <Spin size="large" />
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 1200 }}>
            <Title level={3} style={{ marginBottom: 24 }}>
                🦞 集群概览
            </Title>

            {/* Stat Cards */}
            <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
                <Col xs={24} sm={12} md={6}>
                    <Card
                        style={{
                            borderRadius: 12,
                            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                        }}
                    >
                        <Space direction="vertical" size={4}>
                            <Text type="secondary" style={{ fontSize: 13 }}>
                                节点总数
                            </Text>
                            <Title level={2} style={{ margin: 0 }}>
                                <ClusterOutlined style={{ color: 'var(--accent)', marginRight: 8 }} />
                                {nodes.length}
                            </Title>
                        </Space>
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card style={{ borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                        <Space direction="vertical" size={4}>
                            <Text type="secondary" style={{ fontSize: 13 }}>在线</Text>
                            <Title level={2} style={{ margin: 0, color: 'var(--status-online)' }}>
                                <CheckCircleOutlined style={{ marginRight: 8 }} />
                                {online}
                            </Title>
                        </Space>
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card style={{ borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                        <Space direction="vertical" size={4}>
                            <Text type="secondary" style={{ fontSize: 13 }}>离线</Text>
                            <Title level={2} style={{ margin: 0, color: 'var(--status-offline)' }}>
                                <CloseCircleOutlined style={{ marginRight: 8 }} />
                                {offline}
                            </Title>
                        </Space>
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card style={{ borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                        <Space direction="vertical" size={4}>
                            <Text type="secondary" style={{ fontSize: 13 }}>活跃会话</Text>
                            <Title level={2} style={{ margin: 0 }}>
                                <MessageOutlined style={{ color: '#6366f1', marginRight: 8 }} />
                                {sessions}
                            </Title>
                        </Space>
                    </Card>
                </Col>
            </Row>

            {/* Node Cards Grid */}
            <Title level={4} style={{ marginBottom: 16 }}>
                节点状态
            </Title>

            {nodes.length === 0 ? (
                <Empty
                    description={
                        <span>
                            还没有节点 — 前往
                            <a href="/nodes" style={{ color: 'var(--accent)' }}> 节点管理 </a>
                            添加你的第一个 OpenClaw Gateway
                        </span>
                    }
                    style={{ padding: 80 }}
                />
            ) : (
                <Row gutter={[16, 16]}>
                    {nodes.map((node) => (
                        <Col xs={24} sm={12} lg={8} key={node.id}>
                            <Card
                                hoverable
                                style={{
                                    borderRadius: 12,
                                    cursor: 'pointer',
                                    borderLeft: `4px solid ${node.status.online ? 'var(--status-online)' : 'var(--status-offline)'}`,
                                }}
                                onClick={() => (window.location.href = `/nodes/${node.id}`)}
                            >
                                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                                    <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                                        <Text strong style={{ fontSize: 16 }}>
                                            {node.name}
                                        </Text>
                                        <Badge
                                            status={node.status.online ? 'success' : 'error'}
                                            text={node.status.online ? '在线' : '离线'}
                                        />
                                    </Space>

                                    <Text type="secondary" style={{ fontSize: 12, fontFamily: 'JetBrains Mono' }}>
                                        {node.url}
                                    </Text>

                                    <Space size={4} wrap>
                                        {node.tags.map((tag) => (
                                            <Tag key={tag} color="blue">
                                                {tag}
                                            </Tag>
                                        ))}
                                    </Space>

                                    {node.status.online && (
                                        <Space split="·">
                                            <Text type="secondary" style={{ fontSize: 12 }}>
                                                {node.status.model ?? '—'}
                                            </Text>
                                            <Text type="secondary" style={{ fontSize: 12 }}>
                                                {node.status.sessionCount ?? 0} 会话
                                            </Text>
                                        </Space>
                                    )}

                                    {!node.status.online && node.status.error && (
                                        <Text type="danger" style={{ fontSize: 12 }}>
                                            {node.status.error}
                                        </Text>
                                    )}
                                </Space>
                            </Card>
                        </Col>
                    ))}
                </Row>
            )}
        </div>
    );
}
