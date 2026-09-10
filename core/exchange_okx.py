"""
exchange_okx.py — OKX 公共行情 provider（替换 Crypto.com 的 exchange.py/v3_exchange.py）
接口与 core.exchange 完全一致，其余 engine / runner 无需改动：
    bootstrap_history(base_url, instrument_name, timeframe, target_candles, max_per_call, request_delay)
    fetch_latest_candles(base_url, instrument_name, timeframe, count, request_delay)
    fetch_new_candles_since(base_url, instrument_name, timeframe, since_timestamp, max_per_call, request_delay)
"""
import time, logging, requests

logger = logging.getLogger("exchange_okx")

# OKX /candles 的 limit 上限是 100
OKX_LIMIT_MAX = 100

# 项目内部 tf 代码 -> OKX bar
TIMEFRAME_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "2h": "2H", "4h": "4H",
    "1D": "1D", "1W": "1W", "1M": "1M",
}


class ExchangeError(Exception):
    pass


def _inst_id(instrument_name: str) -> str:
    return instrument_name.replace("_", "-")   # BTC_USDT -> BTC-USDT


def _bar(tf: str) -> str:
    return TIMEFRAME_MAP.get(tf, tf)


PERP_MAP = {"BTC_USDT": "BTC_USDT_SWAP", "ETH_USDT": "ETH_USDT_SWAP", "SOL_USDT": "SOL_USDT_SWAP"}
def _request_candlestick(base_url, instrument_name, timeframe, count=None, end_ts=None):
    instrument_name = PERP_MAP.get(instrument_name, instrument_name)
    url = f"{base_url}/candles"
    params = {
        "instId": _inst_id(instrument_name),
        "bar": _bar(timeframe),
        "limit": min(int(limit), OKX_LIMIT_MAX),
    }
    if after is not None:
        params["after"] = str(int(after))   # 取更老的 K 线（向前翻页）
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "0":
        raise ExchangeError(f"OKX API error {instrument_name} {timeframe}: {data}")
    return data.get("data", [])   # [[ts,o,h,l,c,vol,volCcy,confirm], ...] 最新在前


def _normalize(raw):
    return {
        "timestamp": int(raw[0]),            # 毫秒 UTC，K 线起始时间
        "open": float(raw[1]),
        "high": float(raw[2]),
        "low": float(raw[3]),
        "close": float(raw[4]),
        "volume": float(raw[5]),
    }


def bootstrap_history(base_url, instrument_name, timeframe, target_candles,
                      max_per_call, request_delay):
    all_candles, after = {}, None
    for _ in range((target_candles // OKX_LIMIT_MAX) + 5):
        raw = _request(base_url, instrument_name, timeframe, limit=max_per_call, after=after)
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
    logger.info("OKX bootstrap %s %s: %d candles (target=%d)", instrument_name, timeframe, len(candles), target_candles)
    return candles


def fetch_latest_candles(base_url, instrument_name, timeframe, count, request_delay):
    raw = _request(base_url, instrument_name, timeframe, limit=count)
    candles = sorted([_normalize(r) for r in raw], key=lambda x: x["timestamp"])
    time.sleep(request_delay)
    return candles


def fetch_new_candles_since(base_url, instrument_name, timeframe, since_timestamp,
                            max_per_call, request_delay):
    # 拉最新一页，过滤出比 since_timestamp 新的（5 分钟扫描足够）
    raw = _request(base_url, instrument_name, timeframe, limit=max_per_call)
    candles = sorted(
        [_normalize(r) for r in raw if int(r[0]) > since_timestamp],
        key=lambda x: x["timestamp"],
    )
    time.sleep(request_delay)
    return candles
