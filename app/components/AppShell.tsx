'use client';

import React from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Layout, Menu } from 'antd';
import {
    DashboardOutlined,
    ClusterOutlined,
    SettingOutlined,
    TeamOutlined,
    ThunderboltOutlined,
} from '@ant-design/icons';

const { Sider, Content } = Layout;

const NAV_ITEMS = [
    { key: '/', icon: <DashboardOutlined />, label: '集群概览' },
    { key: '/nodes', icon: <ClusterOutlined />, label: '节点管理' },
    { key: '/agents', icon: <TeamOutlined />, label: 'Agent 管理' },
    { key: '/events', icon: <ThunderboltOutlined />, label: '事件引擎' },
    { key: '/settings', icon: <SettingOutlined />, label: '集群设置' },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();

    const selectedKey = NAV_ITEMS.find(
        (item) => item.key !== '/' && pathname.startsWith(item.key),
    )?.key ?? '/';

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sider
                width={240}
                style={{
                    background: 'var(--sidebar-bg)',
                    borderRight: '1px solid var(--sidebar-border)',
                    overflow: 'auto',
                    height: '100vh',
                    position: 'fixed',
                    left: 0,
                    top: 0,
                    bottom: 0,
                }}
            >
                {/* Logo */}
                <div
                    style={{
                        padding: '20px 16px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                    }}
                >
                    <span style={{ fontSize: 28 }}>🦞</span>
                    <div>
                        <div
                            style={{
                                color: '#fff',
                                fontSize: 15,
                                fontWeight: 700,
                                lineHeight: 1.2,
                            }}
                        >
                            OpenClaw
                        </div>
                        <div
                            style={{
                                color: 'var(--sidebar-text)',
                                fontSize: 11,
                                fontWeight: 500,
                                letterSpacing: '0.05em',
                            }}
                        >
                            CLUSTER MANAGER
                        </div>
                    </div>
                </div>

                {/* Nav */}
                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={[selectedKey]}
                    items={NAV_ITEMS}
                    onClick={({ key }) => router.push(key)}
                    style={{
                        background: 'transparent',
                        borderInlineEnd: 'none',
                        marginTop: 8,
                    }}
                />

                {/* Footer */}
                <div
                    style={{
                        position: 'absolute',
                        bottom: 16,
                        left: 0,
                        right: 0,
                        textAlign: 'center',
                        color: 'var(--text-muted)',
                        fontSize: 11,
                    }}
                >
                    Powered by Survival
                </div>
            </Sider>

            <Layout style={{ marginLeft: 240, background: 'var(--content-bg)' }}>
                <Content
                    style={{
                        padding: 24,
                        height: '100vh',
                        overflow: 'auto',
                    }}
                >
                    {children}
                </Content>
            </Layout>
        </Layout>
    );
}
