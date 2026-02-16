'use client';

import React from 'react';
import { Typography, Card, Descriptions } from 'antd';

const { Title, Paragraph } = Typography;

export default function SettingsPage() {
    return (
        <div style={{ maxWidth: 800 }}>
            <Title level={3}>集群设置</Title>

            <Card style={{ borderRadius: 12, marginBottom: 16 }}>
                <Descriptions title="关于" column={1}>
                    <Descriptions.Item label="项目">
                        OpenClaw Cluster Manager
                    </Descriptions.Item>
                    <Descriptions.Item label="Upstream">
                        <a
                            href="https://github.com/openclaw/openclaw"
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: 'var(--accent)' }}
                        >
                            openclaw/openclaw
                        </a>
                    </Descriptions.Item>
                    <Descriptions.Item label="架构">
                        零修改管理 — 通过 Gateway WebSocket RPC 接口
                    </Descriptions.Item>
                    <Descriptions.Item label="配置文件">
                        <code>cluster.json</code>
                    </Descriptions.Item>
                </Descriptions>
            </Card>

            <Card style={{ borderRadius: 12 }}>
                <Title level={5}>使用说明</Title>
                <Paragraph>
                    1. 在 <b>节点管理</b> 页面添加你的 OpenClaw Gateway 实例地址
                </Paragraph>
                <Paragraph>
                    2. 所有管理操作通过 Gateway 原生 RPC 接口完成，不需要修改 OpenClaw
                </Paragraph>
                <Paragraph>
                    3. 节点配置保存在项目根目录的 <code>cluster.json</code> 文件中
                </Paragraph>
                <Paragraph>
                    4. 如果 Gateway 开启了认证，在添加节点时填入 Auth Token
                </Paragraph>
            </Card>
        </div>
    );
}
