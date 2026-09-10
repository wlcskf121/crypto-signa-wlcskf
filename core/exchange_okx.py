"""
core/exchange_okx.py — OKX 公共行情 provider（替代 Crypto.com 的 exchange.py / v3_exchange.py）

接口与 core.exchange / core.v3_exchange 完全一致，其余 engine / runner 无需改动：
    bootstrap_history(base_url, instrument_name, timeframe, target_candles, max_per_call, request_delay)
    fetch_latest_candles(base_url, instrument_name, timeframe, count, request_delay)
    fetch_new_candles_since(base_url, instrument_name, timeframe, since_timestamp, max_per_call, request_delay)

OKX 公共行情 GET /api/v5/market/candles 免 key，返回 instId=BTC-USDT-SWAP、bar=1H，最新在前。
本模块同时覆盖 main 族（H4/H1）与 v3 族（D1/M30/M15/5m）的全部时段。
"""

import time
import logging
import requests

logger = logging.getLogger("exchange_okx")

# OKX /candles 的 limit 上限是 100
OKX_LIMIT_MAX = 100

# 项目内部 tf 代码 -> OKX bar
TIMEFRAME_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "2h": "2H", "4h": "4H",
    "1D": "1D", "1W": "1W", "1M": "1M",
}

# 逻辑资产名 -> OKX 永续合约 instId（仅这些走永续，其余保持现货命名）
PERP_MAP = {
    "BTC_USDT": "BTC-USDT-SWAP",
    "ETH_USDT": "ETH-USDT-SWAP",
    "SOL_USDT": "SOL-USDT-SWAP",
}


class ExchangeError(Exception):
    pass


def _inst_id(instrument_name: str) -> str:
    # 命中永续映射 -> BTC-USDT-SWAP；否则退回现货命名（如其它币）
    return PERP_MAP.get(instrument_name, instrument_name.replace("_", "-"))


def _bar(tf: str) -> str:
    return TIMEFRAME_MAP.get(tf, tf)


def _request(base_url, instrument_name, timeframe, limit=100, after=None):
    """单次请求 OKX K 线。after 用于向前翻页（取更老的 K 线）。"""
    url = f"{base_url}/candles"
    params = {
        "instId": _inst_id(instrument_name),
        "bar": _bar(timeframe),
        "limit": min(int(limit), OKX_LIMIT_MAX),
    }
    if after is not None:
        params["after"] = str(int(after))  # OKX after 取更早的 K 线（毫秒）
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "0":
        raise ExchangeError(
            f"OKX API error {instrument_name} {timeframe}: {data}"
        )
    # 返回 [[ts,o,h,l,c,vol,volCcy,confirm], ...]，最新在前
    return data.get("data", [])


def _normalize(raw):
    return {
        "timestamp": int(raw[0]),  # 毫秒 UTC，K 线起始时间
        "open": float(raw[1]),
        "high": float(raw[2]),
        "low": float(raw[3]),
        "close": float(raw[4]),
        "volume": float(raw[5]),
    }


def bootstrap_history(base_url, instrument_name, timeframe, target_candles,
                      max_per_call, request_delay):
    """构建初始历史：用 after 向前翻页补齐到 target_candles。"""
    all_candles = {}
    after = None
    safety_max_calls = (target_candles // OKX_LIMIT_MAX) + 5

    for _ in range(safety_max_calls):
        raw = _request(base_url, instrument_name, timeframe,
                       limit=max_per_call, after=after)
        if not raw:
            break
        for r in raw:
            c = _normalize(r)
            all_candles[c["timestamp"]] = c
        if len(all_candles) >= target_candles:
            break
        after = min(all_candles.keys()) - 1
        time.sleep(request_delay)

    candles = sorted(all_candles.values(), key=lambda x: x["timestamp"])
    logger.info("OKX bootstrap %s %s: %d candles (target=%d)",
                instrument_name, timeframe, len(candles), target_candles)
    return candles


def fetch_latest_candles(base_url, instrument_name, timeframe, count, request_delay):
    raw = _request(base_url, instrument_name, timeframe, limit=count)
    candles = sorted([_normalize(r) for r in raw], key=lambda x: x["timestamp"])
    time.sleep(request_delay)
    return candles


def fetch_new_candles_since(base_url, instrument_name, timeframe, since_timestamp,
                            max_per_call, request_delay):
    # 拉最新一页，过滤出比 since_timestamp 新的（5 分钟扫描足够，无需翻页）
    raw = _request(base_url, instrument_name, timeframe, limit=max_per_call)
    candles = sorted(
        [_normalize(r) for r in raw if int(r[0]) > since_timestamp],
        key=lambda x: x["timestamp"],
    )
    time.sleep(request_delay)
    return candles
