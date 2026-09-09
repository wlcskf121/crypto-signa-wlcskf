"""
notifications/v3_telegram.py
Telegram 推送：专用于 Institutional Scanner Framework V3.2。

格式独立于现有 notifications/telegram_bot.py，
仅复用底层 send_message 函数。
"""

import logging
from notifications.telegram_bot import send_message
from notifications import ntfy_bot

logger = logging.getLogger("v3_telegram")


def _fmt(v) -> str:
    if v is None:
        return "N/A"
    if v > 1000:
        return f"{v:,.2f}"
    return f"{v:.4f}"


def format_v3_signal_alert(signal: dict) -> str:
    direction = signal["direction"]
    emoji = "🟢" if direction == "BUY" else "🔴"
    quality = signal["signal_quality"]
    asset_display = signal["asset"].replace("_", " ")

    lines = [
        f"{emoji} *机构扫描器 V3.2*",
        "",
        f"资产： *{asset_display}*",
        f"方向： *{direction}*",
        "",
        f"进场价： `{_fmt(signal['entry'])}`",
        f"止损价： `{_fmt(signal['stop_loss'])}`",
        "",
        f"止盈1： `{_fmt(signal.get('tp1'))}`",
        f"止盈2： `{_fmt(signal.get('tp2'))}`",
        f"止盈3： `{_fmt(signal.get('tp3'))}`",
        "",
        f"盈亏比： *{signal['rr']:.2f}*",
        f"Signal 质量： *{quality:.0f}/9*",
        "",
        f"每日背景： {signal.get('daily_context_status', 'N/A')}",
        f"H4 结构： {signal.get('h4_structure_status', 'N/A')}",
        f"H4 区域： {signal.get('h4_zone_status', 'N/A')}",
        f"OTE： {'✓' if signal.get('ote_present') else '✗'}",
        f"回调： {signal.get('pullback_type', 'N/A')}",
        f"M30 转换： {signal.get('m30_transition_status', 'N/A')}",
        f"M15 BOS： {'✓' if signal.get('m15_bos_confirmed') else '✗'}",
        f"时段： {signal.get('session', 'N/A')}",
    ]
    return "\n".join(lines)


def send_v3_signal_alert(bot_token: str, chat_id: str, signal: dict) -> bool:
    text = format_v3_signal_alert(signal)
    return send_message(bot_token, chat_id, text)


def format_v3_signal_alert_plain(signal: dict) -> tuple:
    """ntfy 纯文本格式（无 Markdown）。返回 (title, body)。"""
    direction = signal["direction"]
    asset_display = signal["asset"].replace("_", " ")
    quality = signal["signal_quality"]
    title = f"V3.2 {asset_display} {direction} | 质量 {quality:.0f}/9"
    body = (
        f"进场价： {_fmt(signal['entry'])}\n"
        f"止损价： {_fmt(signal['stop_loss'])}\n"
        f"止盈1： {_fmt(signal.get('tp1'))} | 止盈2： {_fmt(signal.get('tp2'))}\n"
        f"盈亏比： {signal['rr']:.2f}\n"
        f"H4 结构： {signal.get('h4_structure_status', 'N/A')}\n"
        f"时段： {signal.get('session', 'N/A')}"
    )
    return title, body


def send_v3_signal_alert_ntfy(ntfy_topic: str, signal: dict) -> bool:
    title, body = format_v3_signal_alert_plain(signal)
    return ntfy_bot.send_message(ntfy_topic, title, body)
