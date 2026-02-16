#!/usr/bin/env python3
"""
📊 stock_query — tvscreener 实时行情 + 技术指标查询

封装 tvscreener (TradingView Screener API)，为任意股票提供实时数据。
无需入库、无需 masters 表、无需 Stooq。

覆盖: 美股(NASDAQ/NYSE/AMEX) + 港股(HKEX) + A股(SHSE/SZSE) + ETF

Usage:
    python stock_query.py --symbol NASDAQ:TSLA          # 特斯拉
    python stock_query.py --symbol HKEX:700             # 腾讯
    python stock_query.py --symbol SHSE:600519          # 茅台
    python stock_query.py --symbol NASDAQ:DIDIY         # 滴滴
    python stock_query.py --symbol NASDAQ:TSLA --json   # JSON 输出
"""

from __future__ import annotations

import argparse
import json
import sys

try:
    from tvscreener import Market, StockField, StockScreener
except ImportError:
    print("ERROR: tvscreener 未安装. 运行: pip install -U tvscreener", file=sys.stderr)
    sys.exit(1)


# ── 市场自动识别 ──

EXCHANGE_TO_MARKET = {
    "NASDAQ": Market.AMERICA,
    "NYSE":   Market.AMERICA,
    "AMEX":   Market.AMERICA,
    "HKEX":   Market.HONGKONG,
    "SHSE":   Market.CHINA,
    "SZSE":   Market.CHINA,
    "SSE":    Market.CHINA,
}


def detect_market(symbol: str) -> Market:
    """从 symbol 前缀自动识别 TradingView 市场."""
    exchange = symbol.split(":")[0].upper() if ":" in symbol else ""
    return EXCHANGE_TO_MARKET.get(exchange, Market.AMERICA)


# ── 查询字段集 ──

CORE_FIELDS = [
    StockField.NAME,
    StockField.PRICE,
    StockField.CHANGE_PERCENT,
    StockField.VOLUME,
    # 布林带
    StockField.BOLLINGER_UPPER_BAND_20,
    StockField.BOLLINGER_LOWER_BAND_20,
    # RSI
    StockField.RELATIVE_STRENGTH_INDEX_14,
    # MACD
    StockField.MACD_LEVEL_12_26,
    StockField.MACD_SIGNAL_12_26,
    StockField.MACD_HIST,
    # 均线
    StockField.SIMPLE_MOVING_AVERAGE_20,
    StockField.SIMPLE_MOVING_AVERAGE_50,
    StockField.SIMPLE_MOVING_AVERAGE_200,
    StockField.EXPONENTIAL_MOVING_AVERAGE_20,
    StockField.EXPONENTIAL_MOVING_AVERAGE_50,
    StockField.EXPONENTIAL_MOVING_AVERAGE_200,
    # KDJ / Stochastic
    StockField.STOCHASTIC_PERCENTK_14_3_3,
    StockField.STOCHASTIC_PERCENTD_14_3_3,
    # ATR
    StockField.AVERAGE_TRUE_RANGE_14,
    # 综合评级
    StockField.MOVING_AVERAGES_RATING,
    StockField.RECOMMENDATION_MARK,
]


def query_realtime(symbol: str) -> dict | None:
    """查询单只股票的实时数据 + 技术指标.

    Args:
        symbol: 格式 EXCHANGE:CODE, 如 NASDAQ:TSLA, HKEX:700, SHSE:600519

    Returns:
        dict with price, change%, RSI, MACD, 布林带, 均线, KDJ, ATR, 评级
        None if not found
    """
    market = detect_market(symbol)
    token = symbol.split(":")[-1] if ":" in symbol else symbol

    ss = StockScreener()
    ss.set_markets(market)
    ss.set_range(0, 500)
    ss.select(*CORE_FIELDS)
    ss.where(StockField.NAME == token)

    try:
        df = ss.get()
    except Exception as e:
        print(f"tvscreener 查询失败: {e}", file=sys.stderr)
        return None

    if df.empty:
        return None

    # 精确匹配 symbol
    row = df[df["Symbol"] == symbol]
    if row.empty:
        # fallback: 按 code 匹配 (处理交易所前缀差异)
        row = df[df["Name"].astype(str) == token]
    if row.empty:
        # 最终 fallback: 取第一行
        row = df.head(1)

    data = row.iloc[0].to_dict()

    # 标准化输出字段名
    result = {
        "symbol": data.get("Symbol", symbol),
        "name": data.get("Name", token),
        "found": True,
        # 价格
        "price": _safe_float(data.get("Price")),
        "changePct": _safe_float(data.get("Change %")),
        "volume": _safe_int(data.get("Volume")),
        # 布林带
        "boll_upper": _safe_float(data.get("Bollinger Upper Band (20)")),
        "boll_lower": _safe_float(data.get("Bollinger Lower Band (20)")),
        # RSI
        "rsi14": _safe_float(data.get("Relative Strength Index (14)")),
        # MACD
        "macd": _safe_float(data.get("MACD Level (12, 26)")),
        "macd_signal": _safe_float(data.get("MACD Signal (12, 26)")),
        "macd_hist": _safe_float(data.get("MACD Hist")),
        # 均线
        "sma20": _safe_float(data.get("Simple Moving Average (20)")),
        "sma50": _safe_float(data.get("Simple Moving Average (50)")),
        "sma200": _safe_float(data.get("Simple Moving Average (200)")),
        "ema20": _safe_float(data.get("Exponential Moving Average (20)")),
        "ema50": _safe_float(data.get("Exponential Moving Average (50)")),
        "ema200": _safe_float(data.get("Exponential Moving Average (200)")),
        # KDJ
        "stoch_k": _safe_float(data.get("Stochastic %K (14, 3, 3)")),
        "stoch_d": _safe_float(data.get("Stochastic %D (14, 3, 3)")),
        # ATR
        "atr14": _safe_float(data.get("Average True Range (14)")),
        # 评级
        "ma_rating": data.get("Moving Averages Rating", ""),
        "recommendation": data.get("Recommendation Mark", ""),
    }

    # 计算布林带 %B 位置
    upper = result["boll_upper"]
    lower = result["boll_lower"]
    price = result["price"]
    if upper and lower and price and upper != lower:
        result["boll_pct_b"] = round((price - lower) / (upper - lower), 4)
    else:
        result["boll_pct_b"] = None

    return result


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        v = float(val)
        return round(v, 4) if abs(v) < 1 else round(v, 2)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def format_report(data: dict) -> str:
    """格式化为可读的 Markdown 报告."""
    if not data or not data.get("found"):
        return f"❌ 未找到股票数据"

    price = data["price"]
    change = data.get("changePct", 0) or 0
    arrow = "▲" if change >= 0 else "▼"

    lines = [
        f"## {data['symbol']} — {data.get('name', '')}",
        f"",
        f"**价格**: ${price:.2f}  {arrow} {abs(change):.2f}%",
        f"**成交量**: {data.get('volume', 0):,}",
        f"",
        f"### 技术指标",
        f"",
    ]

    # 布林带
    if data.get("boll_upper"):
        pct_b = data.get("boll_pct_b")
        pct_b_str = f"{pct_b:.2%}" if pct_b is not None else "N/A"
        lines.append(f"| 布林带 | 上轨 {data['boll_upper']:.2f} / 下轨 {data['boll_lower']:.2f} / %B {pct_b_str} |")

    # RSI
    if data.get("rsi14"):
        rsi = data["rsi14"]
        state = "超买" if rsi > 70 else "超卖" if rsi < 30 else "中性"
        lines.append(f"| RSI(14) | {rsi:.1f} ({state}) |")

    # MACD
    if data.get("macd") is not None:
        hist = data.get("macd_hist", 0) or 0
        trend = "多头" if hist > 0 else "空头"
        lines.append(f"| MACD | {data['macd']:.4f} / Signal {data.get('macd_signal', 0):.4f} / Hist {hist:.4f} ({trend}) |")

    # 均线
    if data.get("sma20"):
        pos = "多头排列" if (data.get("sma20", 0) or 0) > (data.get("sma50", 0) or 0) > (data.get("sma200", 0) or 0) else \
              "空头排列" if (data.get("sma20", 0) or 0) < (data.get("sma50", 0) or 0) < (data.get("sma200", 0) or 0) else \
              "交叉"
        lines.append(f"| 均线 | SMA20={data['sma20']:.2f} / SMA50={data.get('sma50', 0):.2f} / SMA200={data.get('sma200', 0):.2f} ({pos}) |")

    # 评级
    if data.get("recommendation"):
        lines.append(f"| 综合评级 | {data['recommendation']} (均线: {data.get('ma_rating', '')}) |")

    return "\n".join(lines)


# ── CLI ──

def main() -> int:
    parser = argparse.ArgumentParser(description="📊 实时股票数据查询 (tvscreener)")
    parser.add_argument("--symbol", required=True, help="股票代码 (e.g. NASDAQ:TSLA)")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    data = query_realtime(args.symbol)

    if not data:
        print(json.dumps({"symbol": args.symbol, "found": False}, ensure_ascii=False))
        return 1

    if args.json:
        print(json.dumps(data, ensure_ascii=False, default=str, indent=2))
    else:
        print(format_report(data))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
