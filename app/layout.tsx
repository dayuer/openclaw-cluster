import type { Metadata } from 'next';
import './globals.css';
import AntdProvider from './theme/AntdProvider';
import AppShell from './components/AppShell';

export const metadata: Metadata = {
    title: 'OpenClaw · Cluster Manager',
    description: '零修改管理 OpenClaw Gateway 集群 — Powered by Survival',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="zh-CN">
            <head>
                <link
                    rel="stylesheet"
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
                />
            </head>
            <body style={{ margin: 0, padding: 0, overflow: 'hidden' }}>
                <AntdProvider>
                    <AppShell>{children}</AppShell>
                </AntdProvider>
            </body>
        </html>
    );
}
