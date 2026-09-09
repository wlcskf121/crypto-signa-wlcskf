"""
notifications/v41p1_telegram.py
Telegram 与 ntfy 推送：用于 Institutional Scanner V4.1 Phase 1。
专用格式，展示带优先级评分的资金流向图。
"""

from notifications.telegram_bot import send_message
from notifications import ntfy_bot


def _fmt(v) -> str:
    if v is None:
        return "N/A"
    if v > 1000:
        return f"{v:,.2f}"
    return f"{v:.4f}"


def _priority_emoji(label: str) -> str:
    return {
        "CRITICAL": "🔴",
        "HIGH":     "🟠",
        "MEDIUM":   "🟡",
        "LOW":      "⚪",
    }.get(label, "⚪")


def format_v41p1_signal_alert(signal: dict) -> str:
    direction = signal["direction"]
    emoji = "🟢" if direction == "BUY" else "🔴"
    asset_display = signal["asset"].replace("_", " ")
    quality = signal["quality_score"]
    label = signal.get("quality_label", "MEDIUM")
    label_emoji = {"HIGH": "⭐", "MEDIUM": "▫️", "LOW": "🔹"}.get(label, "▫️")

    triggers = signal.get("trigger_types", [])
    triggers_str = " + ".join(triggers) if triggers else "N/A"

    # 资金流向图
    na_label = signal.get("nearest_above_label") or "N/A"
    na_price = signal.get("nearest_above_price")
    na_prio  = signal.get("nearest_above_priority") or ""
    na_score = signal.get("nearest_above_score")
    na_dist  = signal.get("distance_to_nearest_above_pct")

    nb_label = signal.get("nearest_below_label") or "N/A"
    nb_price = signal.get("nearest_below_price")
    nb_prio  = signal.get("nearest_below_priority") or ""
    nb_score = signal.get("nearest_below_score")
    nb_dist  = signal.get("distance_to_nearest_below_pct")

    src_label = signal.get("liquidity_source") or "N/A"
    src_prio  = signal.get("liquidity_source_priority") or ""
    src_score = signal.get("liquidity_source_score")

    tgt_label = signal.get("liquidity_target") or "N/A"
    tgt_price = signal.get("liquidity_target_price")
    tgt_prio  = signal.get("liquidity_target_priority") or ""
    tgt_score = signal.get("liquidity_target_score")

    em_points = signal.get("expected_move_points")
    em_str = f"{em_points:.1f}pt" if em_points is not None else "N/A"

    def prio_str(label, score):
        if not label:
            return ""
        pe = _priority_emoji(label)
        sc = f"{score:.2f}" if score is not None else "?"
        return f"{pe} {label} {sc}"

    def dist_str(d, sign="+"):
        if d is None:
            return ""
        return f" ({sign}{d*100:.2f}%)"

    lines = [
        f"{emoji} *机构扫描器 V4.1 —— 第一阶段*",
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
        "💧 *资金流向图*",
        f"上方最近： {na_label} @ `{_fmt(na_price)}`{dist_str(na_dist,'+')} {prio_str(na_prio, na_score)}",
        f"下方最近： {nb_label} @ `{_fmt(nb_price)}`{dist_str(nb_dist,'-')} {prio_str(nb_prio, nb_score)}",
        "",
        f"来源： {src_label} {prio_str(src_prio, src_score)}",
        f"目标： {tgt_label} @ `{_fmt(tgt_price)}` {prio_str(tgt_prio, tgt_score)}",
        f"预期波动： *{em_str}*",
        "",
        f"EMA H4： {signal.get('ema_h4', 'N/A')}",
        f"EMA H1： {signal.get('ema_h1', 'N/A')}",
        f"道氏理论 H4： {signal.get('dow_theory_h4', 'N/A')}",
        f"动量： {signal.get('momentum', 'N/A')}",
        f"时段： {signal.get('session', 'N/A')}",
    ]
    return "\n".join(lines)


def send_v41p1_signal_alert(bot_token: str, chat_id: str, signal: dict) -> bool:
    text = format_v41p1_signal_alert(signal)
    return send_message(bot_token, chat_id, text)


def format_v41p1_signal_alert_plain(signal: dict) -> tuple:
    """ntfy 纯文本格式。返回 (title, body)。"""
    direction = signal["direction"]
    asset_display = signal["asset"].replace("_", " ")
    quality = signal["quality_score"]
    label = signal.get("quality_label", "MEDIUM")
    triggers = signal.get("trigger_types", [])
    triggers_str = " + ".join(triggers) if triggers else "N/A"

    em_points = signal.get("expected_move_points")
    em_str = f"{em_points:.1f}pt" if em_points is not None else "N/A"

    na_label = signal.get("nearest_above_label") or "N/A"
    na_price = signal.get("nearest_above_price")
    na_prio  = signal.get("nearest_above_priority") or ""

    nb_label = signal.get("nearest_below_label") or "N/A"
    nb_price = signal.get("nearest_below_price")
    nb_prio  = signal.get("nearest_below_priority") or ""

    tgt_label = signal.get("liquidity_target") or "N/A"
    tgt_prio  = signal.get("liquidity_target_priority") or ""

    title = f"V4.1P1 {asset_display} {direction} | 质量 {quality}/12 ({label}) | 预期波动 {em_str}"

    body = (
        f"进场价： {_fmt(signal['entry'])}\n"
        f"止损价： {_fmt(signal['stop_loss'])}\n"
        f"止盈1 (1R): {_fmt(signal.get('tp1'))}\n"
        f"止盈2 (2R): {_fmt(signal.get('tp2'))}\n"
        f"盈亏比： {signal.get('rr', 0):.2f}\n"
        f"触发条件： {triggers_str}\n"
        f"\n"
        f"资金流向图:\n"
        f"  上方： {na_label} @ {_fmt(na_price)} [{na_prio}]\n"
        f"  下方： {nb_label} @ {_fmt(nb_price)} [{nb_prio}]\n"
        f"  目标： {tgt_label} [{tgt_prio}]\n"
        f"  预期波动： {em_str}\n"
        f"\n"
        f"时段： {signal.get('session', 'N/A')}"
    )
    return title, body


def send_v41p1_signal_alert_ntfy(ntfy_topic: str, signal: dict) -> bool:
    title, body = format_v41p1_signal_alert_plain(signal)
    return ntfy_bot.send_message(ntfy_topic, title, body)


# ============================================================
# 观察列表预警（复用 V4.1 格式并附加优先级评分）
# ============================================================

def format_v41p1_watchlist_alert(asset: str, level: dict) -> str:
    asset_display = asset.replace("_", " ")
    direction = "SELL" if level["kind"] == "high" else "BUY"
    emoji = "🟢" if direction == "BUY" else "🔴"
    pe = _priority_emoji(level.get("priority_label", ""))

    lines = [
        f"👀 *观察列表 — V4.1 第一阶段*",
        "",
        f"资产： *{asset_display}*",
        "",
        f"档位： *{level['label']}*",
        f"价格： `{_fmt(level['price'])}`",
        f"距离： *{level['distance_pct']*100:.2f}%*",
        f"优先级： {pe} *{level.get('priority_label','N/A')}* "
        f"({level.get('priority_score', 0):.2f})",
        f"历史触碰 (30天): {level.get('historical_touches', 0)}",
        "",
        f"潜在情景： {emoji} *{direction}*",
        "",
        "_预备预警：尚未出现触发器确认。_",
    ]
    return "\n".join(lines)


def send_v41p1_watchlist_alert(bot_token: str, chat_id: str,
                                asset: str, level: dict) -> bool:
    text = format_v41p1_watchlist_alert(asset, level)
    return send_message(bot_token, chat_id, text)
