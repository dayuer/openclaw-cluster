#!/usr/bin/env python3
"""
📊 stock_sync — 股票数据同步 (tvscreener + Stooq → Backend DB)

合并原 sync_stock_data.py + backfill_history.py。
移除了硬编码 MySQL 密码，统一使用 Backend API。

数据源:
  - tvscreener (TradingView): 实时价格 (港股/A股/美股)
  - Stooq: 历史日线 CSV (仅美股)

Usage:
    python stock_sync.py --all                  # 同步全部 masters 中的活跃股票
    python stock_sync.py --symbol NASDAQ:TSLA   # 同步单只
    python stock_sync.py --all --with-macro     # 同时同步宏观指标
    python stock_sync.py --backfill 30          # 回填最近 30 天历史
    python stock_sync.py --all --json           # JSON 摘要输出
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ── 加载 .env ──

def _load_dotenv():
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

_IN_DOCKER = Path("/.dockerenv").exists()
_raw_api = os.environ.get("SURVIVAL_API_URL", "http://localhost:3000")
API_BASE = _raw_api if _IN_DOCKER else _raw_api.replace("host.docker.internal", "localhost")

STOOQ_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# ── Backend API ──

def api_post(path: str, data: dict) -> dict:
    url = f"{API_BASE}{path}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        return {"success": False, "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_get(path: str) -> dict:
    url = f"{API_BASE}{path}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_all_masters() -> list[dict]:
    """从 Backend API 获取全部活跃股票 (不直连 MySQL)."""
    result = api_get("/api/stock/masters?limit=9999")
    masters = result.get("data", {}).get("masters", [])
    return [m for m in masters if m.get("isActive", True)]


def get_stock_id(symbol: str) -> int:
    result = api_get(f"/api/stock/masters?symbol={symbol}")
    masters = result.get("data", {}).get("masters", [])
    return masters[0]["id"] if masters else 0


# ── Stooq 数据源 ──

def to_stooq_symbol(symbol: str) -> str:
    exchange, code = symbol.split(":", 1)
    code = code.replace(".", "-")
    if exchange in ("NASDAQ", "NYSE", "AMEX"):
        return code + ".US"
    elif exchange == "HKEX":
        return code.zfill(4) + ".HK"
    elif exchange == "SHSE":
        return code + ".SS"
    elif exchange == "SZSE":
        return code + ".SZ"
    return code


def fetch_stooq_daily(stooq_sym: str, days: int = 5) -> list[dict]:
    end = datetime.now()
    start = end - timedelta(days=days)
    url = (
        f"https://stooq.com/q/d/l/"
        f"?s={stooq_sym}"
        f"&d1={start.strftime('%Y%m%d')}"
        f"&d2={end.strftime('%Y%m%d')}&i=d"
    )
    req = urllib.request.Request(url, headers={"User-Agent": STOOQ_UA})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")

        if "No data" in content or len(content.strip()) < 20:
            return []

        reader = csv.DictReader(io.StringIO(content))
        rows = []
        for r in reader:
            try:
                rows.append({
                    "Date": r["Date"],
                    "Open": float(r["Open"]),
                    "High": float(r["High"]),
                    "Low": float(r["Low"]),
                    "Close": float(r["Close"]),
                    "Volume": int(float(r.get("Volume", 0) or 0)),
                })
            except (ValueError, KeyError):
                continue
        return sorted(rows, key=lambda x: x["Date"])

    except Exception:
        return []


def fetch_latest(stooq_sym: str) -> dict:
    rows = fetch_stooq_daily(stooq_sym, days=5)
    if not rows:
        return {}
    latest = rows[-1]
    if len(rows) >= 2:
        prev_close = rows[-2]["Close"]
        change_pct = ((latest["Close"] - prev_close) / prev_close) * 100 if prev_close else 0
    else:
        change_pct = 0
    return {
        "date": latest["Date"],
        "open": latest["Open"],
        "high": latest["High"],
        "low": latest["Low"],
        "close": latest["Close"],
        "volume": latest["Volume"],
        "change_pct": round(change_pct, 4),
    }


# ── tvscreener 实时数据 ──

def fetch_tvscreener(symbol: str) -> dict:
    """尝试用 tvscreener 获取实时价格. Stooq 无数据时的 fallback."""
    try:
        from stock_query import query_realtime
        data = query_realtime(symbol)
        if data and data.get("price"):
            return {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "open": data["price"],
                "high": data["price"],
                "low": data["price"],
                "close": data["price"],
                "volume": data.get("volume", 0) or 0,
                "change_pct": data.get("changePct", 0) or 0,
            }
    except Exception:
        pass
    return {}


# ── 宏观指标 ──

MACRO_SYMBOLS = {
    "MACRO:NASDAQ": {"stooq": "^NDQ", "name": "NASDAQ Composite", "desc": "纳斯达克综合指数"},
    "MACRO:SP500":  {"stooq": "^SPX", "name": "S&P 500", "desc": "标普500指数"},
    "MACRO:GOLD":   {"stooq": "XAUUSD", "name": "Gold (XAU/USD)", "desc": "黄金现货价"},
    "MACRO:BTC":    {"stooq": "BTC.V", "name": "Bitcoin (USD)", "desc": "比特币"},
    "MACRO:EURUSD": {"stooq": "EURUSD", "name": "EUR/USD", "desc": "欧元兑美元"},
    "MACRO:QQQ":    {"stooq": "QQQ.US", "name": "QQQ ETF", "desc": "纳斯达克100 ETF"},
}


# ── 写入逻辑 ──

def sync_tick(stock_id: int, data: dict) -> dict:
    now = datetime.now(timezone(timedelta(hours=-5)))
    tick = {
        "stockId": stock_id,
        "price": data["close"],
        "tickedAt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "open": data["open"],
        "high": data["high"],
        "low": data["low"],
        "volume": data["volume"],
        "changePct": round(data.get("change_pct", 0), 4),
    }
    return api_post("/api/stock/ticks", {"ticks": [tick]})


def sync_snapshot(stock_id: int, data: dict) -> dict:
    snapshot = {
        "stockId": stock_id,
        "tradeDate": data["date"],
        "open": round(data["open"], 2),
        "high": round(data["high"], 2),
        "low": round(data["low"], 2),
        "close": round(data["close"], 2),
        "volume": data["volume"],
        "changePct": round(data.get("change_pct", 0), 4),
    }
    return api_post("/api/stock/snapshots", snapshot)


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="📊 股票数据同步")
    parser.add_argument("--symbol", type=str, help="单只股票 symbol")
    parser.add_argument("--all", action="store_true", help="同步全部 masters")
    parser.add_argument("--tick-only", action="store_true", help="只写 tick")
    parser.add_argument("--with-macro", action="store_true", help="同步宏观指标")
    parser.add_argument("--backfill", type=int, default=0, help="回填 N 天历史")
    parser.add_argument("--delay", type=float, default=1.0, help="每只间隔秒数")
    parser.add_argument("--json", action="store_true", help="JSON 摘要输出")
    args = parser.parse_args()

    start_time = time.time()

    print()
    print("=" * 60)
    print("  📊 Stock Data Sync")
    print(f"  ⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  🌐 Backend: {API_BASE}")
    print(f"  📡 数据源: Stooq + tvscreener fallback")
    print("=" * 60)

    # 宏观指标
    macro_results = []
    if args.with_macro:
        print(f"\n  ══ 宏观指标 ({len(MACRO_SYMBOLS)} 项) ══\n")
        for macro_sym, info in MACRO_SYMBOLS.items():
            print(f"  {info['desc']:<20s}", end="", flush=True)
            data = fetch_latest(info["stooq"])
            if data:
                print(f" {data['close']:>10.2f}  ({data['change_pct']:>+.2f}%)")
                macro_results.append({
                    "symbol": macro_sym, "name": info["name"],
                    "close": data["close"], "changePct": data["change_pct"],
                })
            else:
                print(" ⚠️ 无数据")
            time.sleep(1)
        print()

    # 确定同步列表
    symbols = []
    masters_map: dict[str, int] = {}

    if args.symbol:
        symbols = [args.symbol]
        sid = get_stock_id(args.symbol)
        if sid:
            masters_map[args.symbol] = sid
    elif args.all:
        masters = get_all_masters()
        for m in masters:
            symbols.append(m["symbol"])
            masters_map[m["symbol"]] = m["id"]

    if not symbols:
        print("\n  ⚠️ 没有找到要同步的股票")
        if args.json:
            print(json.dumps({"success": True, "synced": 0, "failed": 0}))
        return

    print(f"\n  📋 待同步: {len(symbols)} 只股票\n")

    success_count = 0
    error_count = 0
    results = []

    for i, symbol in enumerate(symbols):
        try:
            print(f"  [{i+1}/{len(symbols)}] {symbol:<20s}", end="", flush=True)

            # 获取数据: Stooq 优先, tvscreener fallback
            if args.backfill > 0:
                stooq_sym = to_stooq_symbol(symbol)
                rows = fetch_stooq_daily(stooq_sym, days=args.backfill)
                if rows:
                    stock_id = masters_map.get(symbol) or get_stock_id(symbol)
                    if stock_id:
                        wrote = 0
                        for row in rows:
                            snap_data = {
                                "date": row["Date"],
                                "open": row["Open"], "high": row["High"],
                                "low": row["Low"], "close": row["Close"],
                                "volume": row["Volume"],
                            }
                            res = sync_snapshot(stock_id, snap_data)
                            if res.get("data", {}).get("action") in ("created", "updated"):
                                wrote += 1
                        print(f" 📝 {wrote}/{len(rows)} 天")
                        success_count += 1
                    else:
                        print(" ❌ stockId 未找到")
                        error_count += 1
                else:
                    print(" ⚠️ 无历史数据")
                    error_count += 1
            else:
                stooq_sym = to_stooq_symbol(symbol)
                data = fetch_latest(stooq_sym)

                # Stooq 失败 → tvscreener fallback
                if not data or data.get("close", 0) == 0:
                    data = fetch_tvscreener(symbol)

                if not data or data.get("close", 0) == 0:
                    print(" ⚠️ 无数据")
                    error_count += 1
                    results.append({"symbol": symbol, "status": "skip"})
                    time.sleep(args.delay)
                    continue

                price = data["close"]
                change = data.get("change_pct", 0)
                arrow = "▲" if change >= 0 else "▼"
                print(f" ${price:>8.2f} {arrow}{abs(change):>5.2f}%", end="", flush=True)

                stock_id = masters_map.get(symbol) or get_stock_id(symbol)
                if not stock_id:
                    print(" ❌ stockId 未找到")
                    error_count += 1
                    continue

                # Tick
                tick_result = sync_tick(stock_id, data)
                tick_ok = tick_result.get("data", {}).get("inserted", 0) > 0
                print(f"  tick:{'✅' if tick_ok else '❌'}", end="", flush=True)

                # Snapshot
                if not args.tick_only:
                    snap_result = sync_snapshot(stock_id, data)
                    snap_action = snap_result.get("data", {}).get("action", "")
                    icon = {"updated": "🔄", "created": "✅"}.get(snap_action, "❌")
                    print(f"  snap:{icon}", end="")

                print()
                success_count += 1
                results.append({"symbol": symbol, "status": "ok", "price": price})

            time.sleep(args.delay)
            if (i + 1) % 30 == 0:
                time.sleep(3)

        except Exception as e:
            print(f" ❌ {e}")
            error_count += 1

    duration = round(time.time() - start_time, 1)

    print()
    print("-" * 60)
    print(f"  ✅ 成功: {success_count}  ❌ 失败: {error_count}  ⏱️ 耗时: {duration}s")
    print("=" * 60)

    if args.json:
        print(json.dumps({
            "success": True,
            "total": len(symbols),
            "synced": success_count,
            "failed": error_count,
            "durationSeconds": duration,
            "macro": macro_results,
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
