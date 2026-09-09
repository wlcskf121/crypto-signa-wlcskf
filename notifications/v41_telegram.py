"""
notifications/v41_telegram.py
Telegram 推送：专用于 Institutional Scanner V4.1
Intraday Wave Edition.

独立于 notifications/telegram_bot.py、v3_telegram.py、v4_telegram.py，
仅复用底层 send_message 函数。 Asset mostrato senza
下划线，避免 Telegram Markdown 解析问题。
"""

from notifications.telegram_bot import send_message
from notifications import ntfy_bot


def _fmt(v) -> str:
    if v is None:
        return "N/A"
    if v > 1000:
        return f"{v:,.2f}"
    return f"{v:.4f}"


def format_v41_signal_alert(signal: dict) -> str:
    direction = signal["direction"]
    emoji = "🟢" if direction == "BUY" else "🔴"
    quality = signal["quality_score"]
    label = signal.get("quality_label", "MEDIUM")
    asset_display = signal["asset"].replace("_", " ")

    label_emoji = {"HIGH": "⭐", "MEDIUM": "▫️", "LOW": "🔹"}.get(label, "▫️")

    triggers = signal.get("trigger_types", [])
    triggers_str = " + ".join(triggers) if triggers else "N/A"

    liquidity_source = signal.get("liquidity_source") or "N/A"
    liquidity_target = signal.get("liquidity_target") or "N/A"

    ote_low = signal.get("ote_entry_low")
    ote_high = signal.get("ote_entry_high")
    ote_zone_str = f"{_fmt(ote_low)} - {_fmt(ote_high)}" if ote_low is not None and ote_high is not None else "N/A"

    em_points = signal.get("expected_move_points")
    em_barrier = signal.get("expected_move_barrier") or "N/A"
    em_str = f"{em_points:.1f}pt -> {em_barrier}" if em_points is not None else "N/A"

    lines = [
        f"{emoji} *机构扫描器 V4.1 —— 日内波段*",
        "",
        f"资产： *{asset_display}*",
        f"方向： *{direction}*",
        "",
        f"进场价： `{_fmt(signal['entry'])}`",
        f"止损价： `{_fmt(signal['stop_loss'])}`",
        f"止盈1 (1R): `{_fmt(signal.get('tp1'))}`",
        f"止盈2 (2R): `{_fmt(signal.get('tp2'))}`",
        f"盈亏比： *{signal.get('rr', 0):.2f}*",
        "",
        f"触发条件： *{triggers_str}*",
        f"质量： {label_emoji} *{quality}/12* ({label})",
        "",
        f"流动性来源： {liquidity_source}",
        f"流动性目标： {liquidity_target}",
        f"OTE 进场区域： {ote_zone_str}",
        f"预期波动： {em_str}",
        "",
        f"EMA H4： {signal.get('ema_h4', 'N/A')}",
        f"EMA H1： {signal.get('ema_h1', 'N/A')}",
        f"道氏理论 H4： {signal.get('dow_theory_h4', 'N/A')}",
        f"动量： {signal.get('momentum', 'N/A')}",
        f"H4 区域： {'✓' if signal.get('in_h4_zone') else '✗'}",
        f"S/R 反应： {'✓' if signal.get('sr_reaction') else '✗'}",
        f"OTE： {'✓' if signal.get('ote_present') else '✗'}",
        f"时段： {signal.get('session', 'N/A')}",
    ]
    return "\n".join(lines)


def send_v41_signal_alert(bot_token: str, chat_id: str, signal: dict) -> bool:
    text = format_v41_signal_alert(signal)
    return send_message(bot_token, chat_id, text)


def format_v41_signal_alert_plain(signal: dict) -> tuple:
    """
    ntfy 纯文本格式（无 Markdown）。返回 (title, body)。
    """
    direction = signal["direction"]
    asset_display = signal["asset"].replace("_", " ")
    quality = signal["quality_score"]
    label = signal.get("quality_label", "MEDIUM")
    triggers = signal.get("trigger_types", [])
    triggers_str = " + ".join(triggers) if triggers else "N/A"

    title = f"V4.1 {asset_display} {direction} | 质量 {quality}/12 ({label})"

    ote_low = signal.get("ote_entry_low")
    ote_high = signal.get("ote_entry_high")
    ote_zone_str = f"{_fmt(ote_low)} - {_fmt(ote_high)}" if ote_low is not None and ote_high is not None else "N/A"

    body = (
        f"进场价： {_fmt(signal['entry'])}\n"
        f"止损价： {_fmt(signal['stop_loss'])}\n"
        f"止盈1 (1R): {_fmt(signal.get('tp1'))}\n"
        f"止盈2 (2R): {_fmt(signal.get('tp2'))}\n"
        f"盈亏比： {signal.get('rr', 0):.2f}\n"
        f"触发条件： {triggers_str}\n"
        f"流动性来源： {signal.get('liquidity_source') or 'N/A'}\n"
        f"流动性目标： {signal.get('liquidity_target') or 'N/A'}\n"
        f"OTE 进场区域： {ote_zone_str}\n"
        f"时段： {signal.get('session', 'N/A')}"
    )
    return title, body


def send_v41_signal_alert_all_channels(bot_token: str, chat_id: str, ntfy_topic: str, signal: dict) -> dict:
    """
    向两个渠道（Telegram + ntfy）同时发送交易预警，
    彼此独立：若一个失败，另一个仍会尝试。
    返回 {"telegram": bool, "ntfy": bool}。
    """
    telegram_sent = send_v41_signal_alert(bot_token, chat_id, signal)
    title, body = format_v41_signal_alert_plain(signal)
    ntfy_sent = ntfy_bot.send_message(ntfy_topic, title, body)
    return {"telegram": telegram_sent, "ntfy": ntfy_sent}


# ============================================================
# 观察列表预警（预备性，非交易信号）
# ============================================================

def format_v41_watchlist_alert(asset: str, proximity: dict) -> str:
    asset_display = asset.replace("_", " ")
    direction = proximity["potential_direction"]
    emoji = "🟢" if direction == "BUY" else "🔴"

    lines = [
        f"👀 *观察列表 — V4.1 日内波段*",
        "",
        f"资产： *{asset_display}*",
        "",
        f"流动性区域： *{proximity['label']}*",
        f"价位： `{_fmt(proximity['price'])}`",
        f"距离： *{proximity['distance_pct'] * 100:.2f}%*",
        "",
        f"潜在方向： {emoji} *{direction}*",
        "",
        "_预备预警：尚未出现 BOS/CHOCH 确认。_",
    ]
    return "\n".join(lines)


def send_v41_watchlist_alert(bot_token: str, chat_id: str, asset: str, proximity: dict) -> bool:
    text = format_v41_watchlist_alert(asset, proximity)
    return send_message(bot_token, chat_id, text)


def format_v41_watchlist_alert_plain(asset: str, proximity: dict) -> tuple:
    """
    ntfy 纯文本格式（无 Markdown）。返回 (title, body)。
    """
    asset_display = asset.replace("_", " ")
    direction = proximity["potential_direction"]

    title = f"观察列表 V4.1 {asset_display} | {proximity['label']} → {direction}"
    body = (
        f"价位： {_fmt(proximity['price'])}\n"
        f"距离： {proximity['distance_pct'] * 100:.2f}%\n"
        f"潜在方向： {direction}\n"
        f"预备预警：尚未出现 BOS/CHOCH 确认。"
    )
    return title, body


def send_v41_watchlist_alert_all_channels(bot_token: str, chat_id: str, ntfy_topic: str,
                                           asset: str, proximity: dict) -> dict:
    """
    向两个渠道（Telegram + ntfy）同时发送观察列表预警，
    彼此独立。返回 {"telegram": bool, "ntfy": bool}。
    """
    telegram_sent = send_v41_watchlist_alert(bot_token, chat_id, asset, proximity)
    title, body = format_v41_watchlist_alert_plain(asset, proximity)
    ntfy_sent = ntfy_bot.send_message(ntfy_topic, title, body)
    return {"telegram": telegram_sent, "ntfy": ntfy_sent}
