#!/usr/bin/env python3
"""
📊 stock_analyze — 统一股票分析 (tvscreener + R1 研判)

合并原 stock-bollinger 的分析逻辑，但数据获取优先用 tvscreener。
任意股票都能分析，不依赖 masters 表。

数据获取优先级:
  1. tvscreener 实时 (价格 + 技术指标) — 总是可用
  2. Backend DB 历史 K 线 (有则用, 补充趋势分析)

Usage:
    python stock_analyze.py --symbol NASDAQ:TSLA          # 完整分析
    python stock_analyze.py --symbol NASDAQ:DIDIY         # 新股也能查
    python stock_analyze.py --symbol HKEX:700             # 港股
    python stock_analyze.py --symbol SHSE:600519          # A股
    python stock_analyze.py --symbol NASDAQ:TSLA --no-llm # 不调 R1
    python stock_analyze.py --symbol NASDAQ:TSLA --json   # JSON 机器可读
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 复用 stock_query 的查询能力
sys.path.insert(0, str(Path(__file__).parent))
from stock_query import query_realtime, format_report as format_query_report


# ── 加载 .env ──

def _load_dotenv():
    """从 nanobot/.env 加载环境变量 (不覆盖已有值)"""
    candidates = [
        Path(__file__).resolve().parents[3] / ".env",
        Path("/app/.env"),
    ]
    for env_path in candidates:
        if env_path.is_file():
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = value
            break

_load_dotenv()

# ── 配置 ──

_raw_api = os.environ.get("SURVIVAL_API_URL", "http://localhost:3000")
_IN_DOCKER = Path("/.dockerenv").exists()
API_BASE = _raw_api if _IN_DOCKER else _raw_api.replace("host.docker.internal", "localhost")

LLM_API_BASE = os.environ.get("LLM_API_BASE", "")
LLM_API_KEY = os.environ.get("LLM_API_KEY", os.environ.get("DEEPSEEK_API_KEY", ""))
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-reasoner")
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "180"))
LLM_THINKING = os.environ.get("LLM_THINKING", "1") == "1"


# ── Backend API ──

def api_get(path: str) -> dict:
    url = f"{API_BASE}{path}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def api_post(path: str, data: dict) -> dict:
    url = f"{API_BASE}{path}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT + 10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        return {"success": False, "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── 从 Backend 获取历史 K 线 (可选) ──

def fetch_history(symbol: str, days: int = 60) -> list[dict]:
    """尝试从 Backend 获取历史 K 线. 非必须, 有则用."""
    result = api_get(
        f"/api/stock/snapshots?symbol={symbol}&limit={days}&sort=tradeDate"
    )
    data = result.get("data", {})
    snapshots = data.get("snapshots", data.get("items", []))
    if not snapshots:
        return []
    candles = []
    for s in snapshots:
        try:
            candles.append({
                "date": s.get("tradeDate", ""),
                "open": float(s.get("open", 0)),
                "high": float(s.get("high", 0)),
                "low": float(s.get("low", 0)),
                "close": float(s.get("close", 0)),
                "volume": int(s.get("volume", 0)),
            })
        except (ValueError, TypeError):
            continue
    return sorted(candles, key=lambda c: c["date"])


# ── 量化评分 (基于 tvscreener 指标) ──

def calc_score(data: dict) -> dict:
    """基于 tvscreener 返回的指标做多空评分 (-5 ~ +5)."""
    score = 0
    reasons = []

    # 1. 布林带 %B 位置
    pct_b = data.get("boll_pct_b")
    if pct_b is not None:
        if pct_b < 0.2:
            score += 2
            reasons.append(f"超卖区域 (%B={pct_b:.2f})")
        elif pct_b > 0.8:
            score -= 2
            reasons.append(f"超买区域 (%B={pct_b:.2f})")
        elif 0.4 <= pct_b <= 0.6:
            reasons.append(f"布林带中轨附近 (%B={pct_b:.2f})")

    # 2. RSI
    rsi = data.get("rsi14")
    if rsi:
        if rsi < 30:
            score += 2
            reasons.append(f"RSI 超卖 ({rsi:.1f})")
        elif rsi > 70:
            score -= 2
            reasons.append(f"RSI 超买 ({rsi:.1f})")
        elif rsi < 40:
            score += 1
            reasons.append(f"RSI 偏低 ({rsi:.1f})")
        elif rsi > 60:
            score -= 1
            reasons.append(f"RSI 偏高 ({rsi:.1f})")

    # 3. MACD 柱状图
    macd_hist = data.get("macd_hist")
    if macd_hist is not None:
        if macd_hist > 0:
            score += 1
            reasons.append(f"MACD 多头 (Hist={macd_hist:.4f})")
        else:
            score -= 1
            reasons.append(f"MACD 空头 (Hist={macd_hist:.4f})")

    # 4. 均线排列
    sma20 = data.get("sma20") or 0
    sma50 = data.get("sma50") or 0
    sma200 = data.get("sma200") or 0
    price = data.get("price") or 0
    if sma20 > 0 and sma50 > 0 and sma200 > 0:
        if sma20 > sma50 > sma200:
            score += 1
            reasons.append("均线多头排列")
        elif sma20 < sma50 < sma200:
            score -= 1
            reasons.append("均线空头排列")
        if price > sma200:
            reasons.append("价格在200日线上方")
        elif price < sma200:
            reasons.append("价格在200日线下方")

    # 5. TradingView 综合评级
    rec = data.get("recommendation", "")
    if "BUY" in str(rec).upper():
        score += 1
        reasons.append(f"TV评级: {rec}")
    elif "SELL" in str(rec).upper():
        score -= 1
        reasons.append(f"TV评级: {rec}")

    # 限幅
    score = max(-5, min(5, score))

    if score >= 3:
        direction = "强力做多"
    elif score >= 1:
        direction = "偏多操作"
    elif score <= -3:
        direction = "强力做空"
    elif score <= -1:
        direction = "偏空操作"
    else:
        direction = "中性观望"

    return {
        "score": score,
        "direction": direction,
        "reasons": reasons,
    }


# ── LLM 研判 ──

def call_llm(prompt: str, system_prompt: str = "") -> str:
    """调用 LLM 大模型 (支持 GLM-5 深度思考)."""
    import re
    if not LLM_API_BASE or not LLM_API_KEY:
        return ""

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    body = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": 65536 if LLM_THINKING else 2000,
        "temperature": 1.0 if LLM_THINKING else 0.3,
    }

    # GLM-5 深度思考
    if LLM_THINKING:
        body["thinking"] = {"type": "enabled"}

    url = f"{LLM_API_BASE}/chat/completions"
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    })

    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        # 去除 <think>...</think> 标签
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return content
    except Exception as e:
        print(f"  ⚠️ LLM 调用失败: {e}", file=sys.stderr)
        return ""


def llm_analyze(symbol: str, data: dict, score_data: dict, history_len: int = 0) -> str:
    """用 R1 做综合研判."""
    system_prompt = (
        "你是一位专业的量化分析师，擅长技术面分析。"
        "请根据给定的技术指标数据，给出简洁、实用的操作建议。"
        "直接给出结论，不要写免责声明。"
    )

    prompt_parts = [
        f"# {symbol} 技术分析",
        f"",
        f"## 实时行情 (TradingView)",
        f"- 价格: {data.get('price', 'N/A')}",
        f"- 涨跌幅: {data.get('changePct', 'N/A')}%",
        f"- RSI(14): {data.get('rsi14', 'N/A')}",
        f"- MACD Hist: {data.get('macd_hist', 'N/A')}",
        f"- 布林带 %B: {data.get('boll_pct_b', 'N/A')}",
        f"- 布林带上轨: {data.get('boll_upper', 'N/A')}",
        f"- 布林带下轨: {data.get('boll_lower', 'N/A')}",
        f"- SMA20: {data.get('sma20', 'N/A')} / SMA50: {data.get('sma50', 'N/A')} / SMA200: {data.get('sma200', 'N/A')}",
        f"- ATR(14): {data.get('atr14', 'N/A')}",
        f"- TV综合评级: {data.get('recommendation', 'N/A')}",
        f"",
        f"## 量化评分: {score_data['score']} ({score_data['direction']})",
        f"依据: {'; '.join(score_data['reasons'])}",
    ]

    if history_len > 0:
        prompt_parts.append(f"\n(已有 {history_len} 天历史K线数据辅助)")

    prompt_parts.append(
        "\n请分析:\n1. 当前技术面状态\n2. 短期操作方向 (做多/做空/观望)\n3. 关键支撑位和阻力位\n4. 风险提示"
    )

    return call_llm("\n".join(prompt_parts), system_prompt)


# ── 报告生成 ──

def generate_report(
    symbol: str,
    data: dict,
    score_data: dict,
    llm_result: str | None = None,
    history_len: int = 0,
) -> str:
    """生成 Markdown 分析报告."""
    price = data.get("price", 0)
    change = data.get("changePct", 0) or 0
    arrow = "▲" if change >= 0 else "▼"

    lines = [
        f"# 📊 {symbol} 技术分析报告",
        f"",
        f"> 数据源: TradingView | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## 行情概览",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 价格 | ${price:.2f} {arrow}{abs(change):.2f}% |",
        f"| 成交量 | {data.get('volume', 0):,} |",
    ]

    # 布林带
    if data.get("boll_upper"):
        pct_b = data.get("boll_pct_b")
        pct_b_str = f"{pct_b:.2%}" if pct_b is not None else "N/A"
        lines.append(f"| 布林带(20) | 上轨 {data['boll_upper']:.2f} / 下轨 {data['boll_lower']:.2f} |")
        lines.append(f"| 布林带 %B | {pct_b_str} |")

    # RSI
    if data.get("rsi14"):
        rsi = data["rsi14"]
        state = "🔴 超买" if rsi > 70 else "🟢 超卖" if rsi < 30 else "⚪ 中性"
        lines.append(f"| RSI(14) | {rsi:.1f} {state} |")

    # MACD
    if data.get("macd") is not None:
        hist = data.get("macd_hist", 0) or 0
        trend = "📈 多头" if hist > 0 else "📉 空头"
        lines.append(f"| MACD | {data['macd']:.4f} / Signal {data.get('macd_signal', 0):.4f} |")
        lines.append(f"| MACD Hist | {hist:.4f} {trend} |")

    # 均线
    if data.get("sma20"):
        lines.append(f"| SMA | 20={data['sma20']:.2f} / 50={data.get('sma50', 0):.2f} / 200={data.get('sma200', 0):.2f} |")

    # ATR
    if data.get("atr14"):
        lines.append(f"| ATR(14) | {data['atr14']:.2f} |")

    # 评级
    if data.get("recommendation"):
        lines.append(f"| TV评级 | {data['recommendation']} |")

    # 量化评分
    lines.extend([
        f"",
        f"## 量化评分: {score_data['score']} / ±5 ({score_data['direction']})",
        f"",
    ])
    for r in score_data["reasons"]:
        lines.append(f"- {r}")

    # 历史数据
    if history_len > 0:
        lines.extend([f"", f"> 📚 已参考 {history_len} 天历史 K 线数据"])

    # LLM 研判
    if llm_result:
        lines.extend([
            f"",
            f"## 🤖 R1 研判",
            f"",
            llm_result,
        ])

    # JSON 结构化
    summary_json = {
        "symbol": symbol,
        "price": price,
        "changePct": change,
        "score": score_data["score"],
        "direction": score_data["direction"],
        "rsi14": data.get("rsi14"),
        "macd_hist": data.get("macd_hist"),
        "boll_pct_b": data.get("boll_pct_b"),
        "recommendation": data.get("recommendation"),
    }
    lines.extend([f"", f"```json", json.dumps(summary_json, ensure_ascii=False), f"```"])

    return "\n".join(lines)


# ── 入库 ──

_DIRECTION_MAP = {
    "强力做多": "BULL", "偏多操作": "BULL", "谨慎偏多": "BULL",
    "强力做空": "BEAR", "偏空操作": "BEAR", "谨慎偏空": "BEAR",
    "中性观望": "NEUTRAL",
}


def save_report(
    symbol: str, data: dict, score_data: dict,
    report_md: str, latency_ms: int | None = None,
) -> dict:
    """保存分析报告到 Backend."""
    price = data.get("price", 0)
    payload = {
        "symbol": symbol,
        "direction": _DIRECTION_MAP.get(score_data["direction"], "NEUTRAL"),
        "confidenceScore": abs(score_data["score"]) / 5.0,
        "predictedClose": price,
        "predictedHigh": data.get("boll_upper", price),
        "predictedLow": data.get("boll_lower", price),
        "scoreBollinger": 0,
        "scoreRsi": data.get("rsi14", 0),
        "scoreMacd": 0,
        "scoreMa": 0,
        "scoreVolume": 0,
        "scoreAtr": 0,
        "compositeScore": score_data["score"],
        "reportMarkdown": report_md,
    }
    if latency_ms:
        payload["llmLatencyMs"] = latency_ms

    return api_post("/api/stock/predictions", payload)


# ── 主程序 ──

def main():
    parser = argparse.ArgumentParser(description="📊 股票技术分析 (tvscreener + R1)")
    parser.add_argument("--symbol", required=True, help="股票代码 (e.g. NASDAQ:TSLA)")
    parser.add_argument("--no-llm", action="store_true", help="跳过 R1 研判")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--output", type=str, help="保存报告到文件")
    parser.add_argument("--save", action="store_true", help="保存到 Backend DB")
    args = parser.parse_args()

    start_time = time.time()
    symbol = args.symbol

    print()
    print("=" * 60)
    print(f"  📊 Stock Analysis — {symbol}")
    print(f"  ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  📡 数据源: TradingView (实时)")
    print("=" * 60)

    # 1. tvscreener 实时数据
    print("\n  ① 获取实时行情...", end="", flush=True)
    data = query_realtime(symbol)
    if not data:
        print(f" ❌ 未找到 {symbol}")
        if args.json:
            print(json.dumps({"symbol": symbol, "found": False, "error": "not_found"}))
        return

    price = data.get("price", 0)
    change = data.get("changePct", 0) or 0
    arrow = "▲" if change >= 0 else "▼"
    print(f" ${price:.2f} {arrow}{abs(change):.2f}%")

    # 2. 尝试获取历史 K 线 (非必须)
    print("  ② 查找历史 K 线...", end="", flush=True)
    history = fetch_history(symbol)
    if history:
        print(f" ✅ {len(history)} 天")
    else:
        print(f" ⚠️ 无历史 (仅用实时指标)")

    # 3. 量化评分
    print("  ③ 量化评分...", end="", flush=True)
    score_data = calc_score(data)
    print(f" {score_data['score']:+d} ({score_data['direction']})")

    # 4. LLM 研判
    llm_result = None
    llm_latency = None
    if not args.no_llm and LLM_API_BASE:
        print("  ④ R1 研判...", end="", flush=True)
        llm_start = time.time()
        llm_result = llm_analyze(symbol, data, score_data, len(history))
        llm_latency = int((time.time() - llm_start) * 1000)
        if llm_result:
            print(f" ✅ ({llm_latency}ms)")
        else:
            print(f" ⚠️ 跳过")
    else:
        print("  ④ R1 研判... ⏭ 跳过")

    # 5. 生成报告
    report = generate_report(symbol, data, score_data, llm_result, len(history))

    total_time = round(time.time() - start_time, 1)
    print(f"\n  ⏱ 总耗时: {total_time}s")
    print("-" * 60)

    if args.json:
        output = {
            "symbol": symbol,
            "found": True,
            "price": price,
            "changePct": change,
            "score": score_data["score"],
            "direction": score_data["direction"],
            "reasons": score_data["reasons"],
            "indicators": {
                "rsi14": data.get("rsi14"),
                "macd_hist": data.get("macd_hist"),
                "boll_pct_b": data.get("boll_pct_b"),
                "sma20": data.get("sma20"),
                "sma50": data.get("sma50"),
                "sma200": data.get("sma200"),
                "atr14": data.get("atr14"),
                "recommendation": data.get("recommendation"),
            },
            "historyDays": len(history),
            "hasLlm": bool(llm_result),
            "latencyMs": int(total_time * 1000),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print()
        print(report)

    # 保存
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"\n  📄 报告已保存: {args.output}")

    if args.save:
        result = save_report(symbol, data, score_data, report, llm_latency)
        if result.get("success") or result.get("data"):
            print(f"  💾 已入库")
        else:
            print(f"  ⚠️ 入库失败: {result.get('error', '')}")


if __name__ == "__main__":
    main()
