'use client';

import React from 'react';
import { ConfigProvider, theme } from 'antd';

export default function AntdProvider({ children }: { children: React.ReactNode }) {
    return (
        <ConfigProvider
            theme={{
                algorithm: theme.defaultAlgorithm,
                token: {
                    colorPrimary: '#e74c3c',
                    borderRadius: 8,
                    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                },
            }}
        >
            {children}
        </ConfigProvider>
    );
}
