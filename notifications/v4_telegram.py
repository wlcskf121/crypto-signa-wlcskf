"""
notifications/v4_telegram.py
Telegram 推送：专用于 Institutional Scanner V4.0 日线版。

独立于 notifications/telegram_bot.py 和 v3_telegram.py，
仅复用底层 send_message 函数。
"""

from notifications.telegram_bot import send_message
from notifications import ntfy_bot


def _fmt(v) -> str:
    if v is None:
        return "N/A"
    if v > 1000:
        return f"{v:,.2f}"
    return f"{v:.4f}"


def format_v4_signal_alert(signal: dict) -> str:
    direction = signal["direction"]
    emoji = "🟢" if direction == "BUY" else "🔴"
    quality = signal["signal_quality"]
    label = signal.get("quality_label", "STANDARD")
    asset_display = signal["asset"].replace("_", " ")

    label_emoji = {"HIGH": "⭐", "STANDARD": "▫️", "LOW": "🔹"}.get(label, "▫️")

    lines = [
        f"{emoji} *机构扫描器 V4.0 —— 日线版*",
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
        f"Signal 质量： {label_emoji} *{quality:.0f}/5* ({label})",
        "",
        f"每日背景： {signal.get('daily_context_status', 'N/A')}",
        f"H4 结构： {signal.get('h4_structure_status', 'N/A')}",
        f"H4 区域： {signal.get('h4_zone_status', 'N/A')}",
        f"OTE： {'✓' if signal.get('ote_present') else '✗'}",
        f"回调： {signal.get('pullback_type', 'N/A')}",
        f"M30 转换： {signal.get('m30_transition_status', 'N/A')}",
        f"时段： {signal.get('session', 'N/A')}",
    ]
    return "\n".join(lines)


def send_v4_signal_alert(bot_token: str, chat_id: str, signal: dict) -> bool:
    text = format_v4_signal_alert(signal)
    return send_message(bot_token, chat_id, text)


def format_v4_signal_alert_plain(signal: dict) -> tuple:
    """ntfy 纯文本格式（无 Markdown）。返回 (title, body)。"""
    direction = signal["direction"]
    asset_display = signal["asset"].replace("_", " ")
    quality = signal["signal_quality"]
    label = signal.get("quality_label", "STANDARD")
    title = f"V4.0 {asset_display} {direction} | 质量 {quality:.0f}/5 ({label})"
    body = (
        f"进场价： {_fmt(signal['entry'])}\n"
        f"止损价： {_fmt(signal['stop_loss'])}\n"
        f"止盈1： {_fmt(signal.get('tp1'))} | 止盈2： {_fmt(signal.get('tp2'))}\n"
        f"盈亏比： {signal['rr']:.2f}\n"
        f"H4 结构： {signal.get('h4_structure_status', 'N/A')}\n"
        f"时段： {signal.get('session', 'N/A')}"
    )
    return title, body


def send_v4_signal_alert_ntfy(ntfy_topic: str, signal: dict) -> bool:
    title, body = format_v4_signal_alert_plain(signal)
    return ntfy_bot.send_message(ntfy_topic, title, body)
