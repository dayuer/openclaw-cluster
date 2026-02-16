---
name: stock
description: >
  全市场股票分析与数据同步。支持美股/港股/A股/ETF，实时获取任意股票的
  价格、布林带、RSI、MACD、均线等技术指标，结合 R1 大模型做综合研判。
  用于"帮我看看特斯拉"、"分析一下DIDIY"、"同步股票数据"等场景。
  合并了原 stock-bollinger 和 stock-sync 的全部功能。
author: Survival Team
version: 2.0.0
created: 2026-02-01
updated: 2026-02-15
agents: [analytics]
---

# 股票分析与数据同步 Skill

全市场覆盖的股票技术分析 + 数据同步工具。

> **数据源**: TradingView (实时行情+技术指标) + Stooq (历史日线)
>
> **核心优势**: 不依赖 masters 表，任意股票都能分析

## 使用方法

### 分析股票（推荐）

```bash
# 分析任意股票 — 即使不在数据库中
python /app/skills/stock/scripts/stock_analyze.py --symbol NASDAQ:TSLA
python /app/skills/stock/scripts/stock_analyze.py --symbol NASDAQ:DIDIY
python /app/skills/stock/scripts/stock_analyze.py --symbol HKEX:700
python /app/skills/stock/scripts/stock_analyze.py --symbol SHSE:600519

# 不调用 R1 (纯指标)
python /app/skills/stock/scripts/stock_analyze.py --symbol NASDAQ:TSLA --no-llm

# JSON 输出
python /app/skills/stock/scripts/stock_analyze.py --symbol NASDAQ:TSLA --json
```

### 查询实时行情

```bash
# 查询实时价格 + 全部技术指标
python /app/skills/stock/scripts/stock_query.py --symbol NASDAQ:TSLA
python /app/skills/stock/scripts/stock_query.py --symbol HKEX:700 --json
```

### 同步数据到 Backend

```bash
# 同步全部 masters
python /app/skills/stock/scripts/stock_sync.py --all

# 同步 + 宏观指标
python /app/skills/stock/scripts/stock_sync.py --all --with-macro

# 回填 30 天历史
python /app/skills/stock/scripts/stock_sync.py --all --backfill 30

# 同步单只
python /app/skills/stock/scripts/stock_sync.py --symbol NASDAQ:TSLA
```

## 支持的市场

| 市场 | 交易所前缀                    | 示例          | 数据源             |
| ---- | ----------------------------- | ------------- | ------------------ |
| 美股 | `NASDAQ:` / `NYSE:` / `AMEX:` | `NASDAQ:TSLA` | tvscreener + Stooq |
| 港股 | `HKEX:`                       | `HKEX:700`    | tvscreener         |
| A股  | `SHSE:` / `SZSE:`             | `SHSE:600519` | tvscreener         |
| ETF  | 同上                          | `SHSE:510300` | tvscreener         |

## 输出指标

| 类别   | 指标                     |
| ------ | ------------------------ |
| 价格   | 实时价、涨跌幅、成交量   |
| 布林带 | 上轨、下轨、%B 位置      |
| 动量   | RSI(14)、MACD、MACD Hist |
| 均线   | SMA/EMA 20/50/200        |
| 波动   | ATR(14)、KDJ             |
| 评级   | TradingView 综合评级     |

## ⚠️ 避坑指南

- tvscreener 需要网络访问 TradingView API
- Stooq 仅美股可靠，港股/A 股数据不可用
- R1 研判需要 `LLM_API_BASE` / `LLM_API_KEY` 配置
- 实时数据有 ~15 分钟延迟 (交易所规则)

## 依赖

| 依赖            | 用途                 |
| --------------- | -------------------- |
| `tvscreener`    | TradingView 数据查询 |
| `llm-processor` | R1 综合研判 (可选)   |

## 演化日志

| 日期       | 版本  | 变更                                                       | 触发原因       |
| ---------- | ----- | ---------------------------------------------------------- | -------------- |
| 2026-02-15 | 2.0.0 | 合并 stock-bollinger + stock-sync; tvscreener 全市场数据源 | DIDIY 无法查询 |
| 2026-02-01 | 1.0.0 | 初始版本 (分离为两个 skill)                                | —              |
