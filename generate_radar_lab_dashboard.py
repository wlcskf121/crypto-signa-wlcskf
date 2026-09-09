"""
generate_radar_lab_dashboard.py
雷达实验室 (BETA) — validazione del Market Radar

V1.1: aggiunta sezione "WR Reale" basata su first_hit (chi tra TP e SL
viene toccato per primo). TP alzato a 2 ATR (RR 1:2).

Legge da signals.db → radar_zones + radar_transitions.

Genera docs/radar_lab_dashboard.html
"""

import sqlite3
import os
import json
import statistics
from datetime import datetime, timezone

DB_PATH  = os.environ.get("DB_PATH", "data/signals.db")
OUT_PATH = "docs/radar_lab_dashboard.html"

MIN_SAMPLE = 30


def q(conn, sql, params=()):
    try:
        return conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return []


# ============================================================
# Data loading
# ============================================================

def load_zones(conn):
    rows = q(conn, """
        SELECT zone_id, asset, direction, emit_ts, price, zone_ref,
               features_json, status, mae, mfe, bars_open, time_to_mfe, time_to_mae,
               stop_loss, stop_hit, time_to_stop, mfe_after_stop,
               tp_hit, be_reached, mfe_beyond_tp, first_hit, first_hit_bar
        FROM radar_zones
    """)
    out = []
    for r in rows:
        d = {
            "zone_id": r[0], "asset": r[1], "direction": r[2], "emit_ts": r[3],
            "price": r[4], "zone_ref": r[5], "status": r[7],
            "mae": r[8], "mfe": r[9], "bars_open": r[10],
            "time_to_mfe": r[11], "time_to_mae": r[12],
            "stop_loss": r[13], "stop_hit": r[14], "time_to_stop": r[15],
            "mfe_after_stop": r[16],
            "tp_hit": r[17] if len(r) > 17 else None,
            "be_reached": r[18] if len(r) > 18 else None,
            "mfe_beyond_tp": r[19] if len(r) > 19 else None,
            "first_hit": r[20] if len(r) > 20 else None,
            "first_hit_bar": r[21] if len(r) > 21 else None,
        }
        try:
            d["features"] = json.loads(r[6]) if r[6] else {}
        except Exception:
            d["features"] = {}
        out.append(d)
    return out


def load_transition_funnel(conn):
    rows = q(conn, """
        SELECT from_state, to_state, COUNT(*) FROM radar_transitions
        GROUP BY from_state, to_state
    """)
    return {(r[0], r[1]): r[2] for r in rows}


# ============================================================
# Stats
# ============================================================

def _num(vals):
    return [v for v in vals if isinstance(v, (int, float))]

def _avg(vals):
    v = _num(vals)
    return round(sum(v) / len(v), 3) if v else None

def _median(vals):
    v = _num(vals)
    return round(statistics.median(v), 3) if v else None

def mfe_in_atr(z):
    atr = (z.get("features") or {}).get("atr")
    if atr and atr > 0 and z.get("mfe") is not None:
        return z["mfe"] / atr
    return None

def mae_in_atr(z):
    atr = (z.get("features") or {}).get("atr")
    if atr and atr > 0 and z.get("mae") is not None:
        return z["mae"] / atr
    return None


def summarize(zones):
    closed = [z for z in zones if z["status"] == "CLOSED"]
    stop_hits = [z for z in closed if z.get("stop_hit")]
    return {
        "total":     len(zones),
        "closed":    len(closed),
        "open":      sum(1 for z in zones if z["status"] == "OPEN"),
        "mfe_avg_atr":    _avg([mfe_in_atr(z) for z in closed]),
        "mfe_med_atr":    _median([mfe_in_atr(z) for z in closed]),
        "mae_avg_atr":    _avg([mae_in_atr(z) for z in closed]),
        "bars_to_mfe_avg": _avg([z.get("time_to_mfe") for z in closed]),
        "stop_hit_n":     len(stop_hits),
        "stop_hit_pct":   round(len(stop_hits) / len(closed) * 100, 1) if closed else None,
    }


def by_asset(zones):
    out = {}
    for a in sorted({z["asset"] for z in zones}):
        out[a] = summarize([z for z in zones if z["asset"] == a])
    return out


def velocity_buckets(zones):
    closed = [z for z in zones if z["status"] == "CLOSED"]
    def vel(z):
        f = z.get("features") or {}
        return f.get("impulse_velocity")
    buckets = [
        ("低于阈值 (< 0.6) \u26a0", lambda v: v is not None and v < 0.6),
        ("正常（0.6–0.8）",      lambda v: v is not None and 0.6 <= v < 0.8),
        ("快（0.8–1.0）",       lambda v: v is not None and 0.8 <= v < 1.0),
        ("极快（≥ 1.0）",   lambda v: v is not None and v >= 1.0),
    ]
    out = []
    for label, cond in buckets:
        sub = [z for z in closed if cond(vel(z))]
        out.append((label, len(sub),
                    _avg([mfe_in_atr(z) for z in sub]),
                    _avg([mae_in_atr(z) for z in sub])))
    return out


# ============================================================
# First Hit stats (V1.1)
# ============================================================

def _first_hit_stats(zones):
    """Calcola WR reale e expectancy basati su first_hit."""
    closed = [z for z in zones if z["status"] == "CLOSED"]
    with_hit = [z for z in closed if z.get("first_hit") in ("TP", "SL")]
    if not with_hit:
        return None
    tp_first = sum(1 for z in with_hit if z["first_hit"] == "TP")
    sl_first = sum(1 for z in with_hit if z["first_hit"] == "SL")
    n = len(with_hit)
    wr = round(tp_first / n * 100, 1)
    # Expectancy a RR 1:2: win = +2R, loss = -1R
    exp = round((tp_first * 2 - sl_first) / n, 3)
    avg_bar = _avg([z.get("first_hit_bar") for z in with_hit])
    return {
        "n": n,
        "tp_first": tp_first,
        "sl_first": sl_first,
        "no_hit": len(closed) - n,
        "wr": wr,
        "exp": exp,
        "avg_bar": avg_bar,
    }


# ============================================================
# CSS
# ============================================================

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
:root{--bg:#0d0f14;--surface:#141720;--border:#1e2330;--accent:#4fffb0;--accent2:#ff6b6b;
--accent3:#ffd166;--accent5:#38bdf8;--text:#e2e8f0;--dim:#5a6478;--buy:#4fffb0;--sell:#ff6b6b;}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'IBM Plex Sans','PingFang SC','Microsoft YaHei','Noto Sans SC',sans-serif;font-size:14px;line-height:1.6}
header{border-bottom:1px solid var(--border);padding:18px 32px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
header h1{font-family:'IBM Plex Mono','PingFang SC','Microsoft YaHei','Noto Sans SC',monospace;font-size:13px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--accent5)}
.beta{font-size:9px;padding:2px 7px;border-radius:4px;background:rgba(255,209,102,.15);color:var(--accent3);margin-left:8px;letter-spacing:.08em}
header .meta{font-family:'IBM Plex Mono','PingFang SC','Microsoft YaHei','Noto Sans SC',monospace;font-size:11px;color:var(--dim)}
header a{color:var(--accent5);text-decoration:none;font-family:'IBM Plex Mono','PingFang SC','Microsoft YaHei','Noto Sans SC',monospace;font-size:11px}
.container{max-width:1100px;margin:0 auto;padding:24px 32px}
.intro{font-size:13px;color:var(--dim);max-width:720px;margin-bottom:24px;line-height:1.7}
.intro strong{color:var(--text)}
.summary-grid{display:grid;gap:1px;background:var(--border);border:1px solid var(--border);border-radius:8px;overflow:hidden;margin-bottom:20px}
.summary-grid.c4{grid-template-columns:repeat(4,1fr)}
.summary-grid.c5{grid-template-columns:repeat(5,1fr)}
.summary-grid>div{background:var(--surface);padding:16px 8px;text-align:center}
.big{font-family:'IBM Plex Mono','PingFang SC','Microsoft YaHei','Noto Sans SC',monospace;font-size:20px;font-weight:600}
.big.pos{color:var(--buy)}.big.neg{color:var(--sell)}.big.warn{color:var(--accent3)}
.lbl{font-size:9px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);display:block;margin-top:4px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden;margin-bottom:16px}
.ch{padding:12px 16px;border-bottom:1px solid var(--border);font-family:'IBM Plex Mono','PingFang SC','Microsoft YaHei','Noto Sans SC',monospace;font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--dim)}
.table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse}
th{font-family:'IBM Plex Mono','PingFang SC','Microsoft YaHei','Noto Sans SC',monospace;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);padding:10px 14px;text-align:left;border-bottom:1px solid var(--border);white-space:nowrap}
td{padding:10px 14px;border-bottom:1px solid var(--border);font-size:13px;white-space:nowrap}
tr:last-child td{border-bottom:none}tr:hover td{background:rgba(255,255,255,.02)}
.mono{font-family:'IBM Plex Mono','PingFang SC','Microsoft YaHei','Noto Sans SC',monospace;font-size:12px}
.pos{color:var(--buy);font-weight:600}.neg{color:var(--sell)}.warn{color:var(--accent3)}
.prov{font-size:10px;color:var(--dim);font-style:italic}
.empty{text-align:center;padding:32px 16px;color:var(--dim);font-size:13px;line-height:1.7}
.note{font-size:11px;color:var(--dim);padding:10px 16px;border-top:1px solid var(--border);line-height:1.6}
@media(max-width:640px){
  header{padding:14px 16px}.container{padding:12px}
  .intro{font-size:12px}
  .summary-grid.c4{grid-template-columns:repeat(2,1fr)}
  .summary-grid.c5{grid-template-columns:repeat(2,1fr)}
  .big{font-size:18px}
  .ch{font-size:10px;padding:10px 12px}
  th,td{padding:9px 12px;font-size:12px}
}
"""


# ============================================================
# Rendering
# ============================================================

def metric(val, unit="", cls=""):
    if val is None:
        return '<span class="big">\u2014</span>'
    sign = "+" if (isinstance(val, (int, float)) and val > 0 and unit == "R") else ""
    return f'<span class="big {cls}">{sign}{val}{unit}</span>'


def summary_block(s):
    mfe_cls = "pos" if (s["mfe_avg_atr"] or 0) > 0 else "neg"
    return f"""<div class="summary-grid c4">
  <div>{metric(s['total'])}<span class="lbl">已发出区间</span></div>
  <div>{metric(s['closed'])}<span class="lbl">已结束</span></div>
  <div>{metric(s['mfe_avg_atr'],'', mfe_cls)}<span class="lbl">平均 MFE（ATR）</span></div>
  <div>{metric(s['mae_avg_atr'],'', 'neg')}<span class="lbl">平均 MAE（ATR）</span></div>
</div>"""


def asset_table(rows):
    if not rows:
        return ""
    body = ""
    for a, s in rows.items():
        prov = ' <span class="prov">(provv.)</span>' if s["closed"] < MIN_SAMPLE else ""
        mfe = s["mfe_avg_atr"]; mae = s["mae_avg_atr"]
        mfe_s = f'<span class="pos">+{mfe}</span>' if mfe is not None else "\u2014"
        mae_s = f'<span class="neg">{mae}</span>' if mae is not None else "\u2014"
        body += f"""<tr><td><strong>{a}</strong>{prov}</td>
  <td class="mono">{s['total']}</td><td class="mono">{s['closed']}</td>
  <td class="mono">{mfe_s}</td><td class="mono">{mae_s}</td>
  <td class="mono">{s['bars_to_mfe_avg'] if s['bars_to_mfe_avg'] is not None else '\u2014'}</td></tr>"""
    return f"""<div class="card"><div class="ch">按资产</div>
  <div class="table-scroll"><table><thead><tr>
    <th>资产</th><th>已发出</th><th>已结束</th><th>MFE (ATR)</th><th>MAE (ATR)</th><th>到 MFE 的 K 线数</th>
  </tr></thead><tbody>{body}</tbody></table></div></div>"""


def velocity_table(buckets):
    body = ""
    for label, n, mfe, mae in buckets:
        if n == 0:
            body += f'<tr><td>{label}</td><td class="mono">0</td><td class="empty" colspan="2" style="text-align:left">无数据</td></tr>'
            continue
        prov = ' <span class="prov">(provv.)</span>' if n < MIN_SAMPLE else ""
        mfe_s = f'<span class="pos">+{mfe}</span>' if mfe is not None else "\u2014"
        mae_s = f'<span class="neg">{mae}</span>' if mae is not None else "\u2014"
        body += f'<tr><td>{label}{prov}</td><td class="mono">{n}</td><td class="mono">{mfe_s}</td><td class="mono">{mae_s}</td></tr>'
    return f"""<div class="card"><div class="ch">速度假设 — 按脉冲分档的反弹表现</div>
  <div class="table-scroll"><table><thead><tr>
    <th>脉冲速度</th><th>N</th><th>MFE (ATR)</th><th>MAE (ATR)</th>
  </tr></thead><tbody>{body}</tbody></table></div>
  <div class="note">若雷达在速度上确有 edge，速度越快的分档应显示更高的平均 MFE。样本少于 {MIN_SAMPLE} 个的数字为暂定：是噪声，不是结论。</div></div>"""


def first_hit_card(zones):
    """V1.1: WR reale — chi tra TP (2 ATR) e SL (1 ATR) viene toccato per primo."""
    closed = [z for z in zones if z["status"] == "CLOSED"]
    if not closed:
        return ""

    # Globale
    g = _first_hit_stats(zones)
    if g is None or g["n"] == 0:
        return f"""<div class="card"><div class="ch">真实胜率 — SL 1 ATR vs TP 2 ATR（谁先到达）</div>
  <div class="empty">first_hit 数据暂不可用。<br>
  已有区间使用的是 1 ATR 的 TP。数据会在新的 2 ATR TP 区间出现后填充，或在对历史区间回填之后（比较 time_to_tp 与 time_to_stop）。</div></div>"""

    prov = ' <span class="prov">(provv.)</span>' if g["n"] < MIN_SAMPLE else ""
    wr_cls = "pos" if g["wr"] >= 40 else ("neg" if g["wr"] < 25 else "warn")
    exp_cls = "pos" if g["exp"] > 0 else "neg"

    # Per asset
    asset_body = ""
    for a in sorted({z["asset"] for z in zones}):
        a_stats = _first_hit_stats([z for z in zones if z["asset"] == a])
        if a_stats is None or a_stats["n"] == 0:
            continue
        a_prov = ' <span class="prov">(provv.)</span>' if a_stats["n"] < MIN_SAMPLE else ""
        a_wr_cls = "pos" if a_stats["wr"] >= 40 else ("neg" if a_stats["wr"] < 25 else "warn")
        a_exp_cls = "pos" if a_stats["exp"] > 0 else "neg"
        asset_body += f"""<tr>
  <td><strong>{a}</strong>{a_prov}</td>
  <td class="mono">{a_stats['n']}</td>
  <td class="mono pos">{a_stats['tp_first']}</td>
  <td class="mono neg">{a_stats['sl_first']}</td>
  <td class="mono {a_wr_cls}">{a_stats['wr']}%</td>
  <td class="mono {a_exp_cls}">{a_stats['exp']:+.3f}R</td>
</tr>"""

    return f"""<div class="card"><div class="ch">真实胜率 — SL 1 ATR vs TP 2 ATR（谁先到达）</div>
  <div class="summary-grid c5" style="border:none;margin:0">
    <div>{metric(g['n'])}<span class="lbl">有结果的区间{prov}</span></div>
    <div>{metric(g['tp_first'],'','pos')}<span class="lbl">先到 TP</span></div>
    <div>{metric(g['sl_first'],'','neg')}<span class="lbl">先到 SL</span></div>
    <div>{metric(g['wr'],'%',wr_cls)}<span class="lbl">Win Rate reale</span></div>
    <div>{metric(g['exp'],'R',exp_cls)}<span class="lbl">Expectancy (1:2)</span></div>
  </div>
  {f'<div class="table-scroll"><table><thead><tr><th>资产</th><th>N</th><th>先到 TP</th><th>先到 SL</th><th>WR</th><th>Exp (1:2)</th></tr></thead><tbody>{asset_body}</tbody></table></div>' if asset_body else ''}
  <div class="note">关键数字：若先触及 TP（2 ATR）再触及 SL（1 ATR），该笔交易以 +2R 获利；若先触及 SL，则以 -1R 亏损。胜率 33.3% 时为盈亏平衡。两者都未触及的区间不计入统计。</div></div>"""


def gestione_card(zones):
    closed = [z for z in zones if z["status"] == "CLOSED"]
    if not closed:
        return ""
    tp_hit = [z for z in closed if z.get("tp_hit")]
    be = [z for z in closed if z.get("be_reached")]
    beyond_atr = []
    for z in tp_hit:
        atr = (z.get("features") or {}).get("atr")
        mb = z.get("mfe_beyond_tp")
        if atr and atr > 0 and mb is not None:
            beyond_atr.append(mb / atr)
    tp_pct = round(len(tp_hit) / len(closed) * 100, 1) if closed else 0
    beyond_avg = _avg(beyond_atr)
    return f"""<div class="card"><div class="ch">平仓管理 — TP 目标 / 保本 / 让利润奔跑</div>
  <div class="summary-grid c4" style="border:none;margin:0">
    <div>{metric(tp_pct,'%','pos')}<span class="lbl">触及 TP（2 ATR）的区间</span></div>
    <div>{metric(len(tp_hit))}<span class="lbl">触及 TP / 共 {len(closed)}</span></div>
    <div>{metric(round(len(be)/len(closed)*100,1) if closed else 0,'%')}<span class="lbl">达到保本</span></div>
    <div>{metric(beyond_avg,'', 'pos' if (beyond_avg or 0)>0 else '')}<span class="lbl">超出 TP 的幅度（ATR）</span></div>
  </div>
  <div class="note">关键数字是最后一个：触及之后行情还能延续多远 <strong>oltre</strong> （2 ATR 的 TP 目标）。该值高说明移动止盈优于固定目标；接近 0 则说明在 2 ATR 直接平仓已足够。所有价位都只做记录：不真正平仓，只测量价格的实际行为。</div></div>"""


def stop_card(zones):
    closed = [z for z in zones if z["status"] == "CLOSED"]
    if not closed:
        return ""
    hits = [z for z in closed if z.get("stop_hit")]
    rebounded = 0
    for z in hits:
        atr = (z.get("features") or {}).get("atr")
        mas = z.get("mfe_after_stop")
        if atr and atr > 0 and mas is not None and mas / atr >= 1.0:
            rebounded += 1
    pct = round(len(hits) / len(closed) * 100, 1) if closed else 0
    reb_pct = round(rebounded / len(hits) * 100, 1) if hits else 0
    return f"""<div class="card"><div class="ch">止损 — 「呼吸」与止损的平衡</div>
  <div class="summary-grid c4" style="border:none;margin:0">
    <div>{metric(pct,'%','warn')}<span class="lbl">触及止损的区间</span></div>
    <div>{metric(len(hits))}<span class="lbl">触及 / 共 {len(closed)}</span></div>
    <div>{metric(reb_pct,'%','pos')}<span class="lbl">其中触及后反弹（≥1 ATR）</span></div>
    <div>{metric(rebounded)}<span class="lbl">已收复的幅度</span></div>
  </div>
  <div class="note">若很多区间都触及止损 <strong>但随后反弹</strong>，说明止损过窄，会砍掉利润。若触及后几乎都没有反弹，说明止损设置得当。止损只做记录：不会中断「呼吸」的测量。</div></div>"""


def funnel_card(funnel, zones):
    invalidated = sum(v for (fr, to), v in funnel.items() if to == "RIPOSO" and fr == "OSSERVAZIONE")
    to_observe  = sum(v for (fr, to), v in funnel.items() if to == "OSSERVAZIONE")
    emitted     = len(zones)
    rows = [
        ("进入观察", to_observe),
        ("→ 转为 Entry Zone", emitted),
        ("→ 已作废（回到静默）", invalidated),
    ]
    body = "".join(f'<tr><td>{l}</td><td class="mono">{n}</td></tr>' for l, n in rows)
    return f"""<div class="card"><div class="ch">状态机漏斗</div>
  <div class="table-scroll"><table><tbody>{body}</tbody></table></div>
  <div class="note">有多少观察真正转化为 Entry Zone，又有多少被作废。健康的漏斗不会对每个观察都发信号。</div></div>"""


# ============================================================
# Generate
# ============================================================

def generate():
    os.makedirs("docs", exist_ok=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    try:
        conn = sqlite3.connect(DB_PATH)
        zones = load_zones(conn)
        funnel = load_transition_funnel(conn)
        conn.close()
    except Exception as e:
        zones, funnel = [], {}
        print(f"雷达实验室: errore lettura DB \u2014 {e}")

    if not zones:
        body = """<div class="card"><div class="empty">
        Market Radar 尚未发出任何 Entry Zone。<br>
        雷达开始记录形态后，本页就会填充数据。<br>
        <span class="prov">仅观察模式 · 等待首批数据</span>
        </div></div>"""
        counts = "0 zone"
    else:
        s = summarize(zones)
        body = (summary_block(s)
                + asset_table(by_asset(zones))
                + velocity_table(velocity_buckets(zones))
                + first_hit_card(zones)
                + gestione_card(zones)
                + stop_card(zones)
                + funnel_card(funnel, zones))
        counts = f"{s['total']} zone ({s['closed']} chiuse)"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>雷达实验室（Beta）</title><style>{CSS}</style></head>
<body>
<header>
  <h1>雷达实验室<span class="beta">BETA</span></h1>
  <div class="meta">{generated} &nbsp;|&nbsp; <a href="engine_edge_dashboard.html">&larr; 引擎 Edge 实验室</a></div>
</header>
<div class="container">
  <p class="intro">
    验证 <strong>Market Radar</strong> 仅观察模式。雷达不买入也不卖出：它只在一波过度延伸、开始衰竭的脉冲之后标记「待观察区间」。这里我们测量 <strong>之后价格怎么走</strong> 每个区间——反弹了多少（MFE）、此前又承受了多少回撤（MAE），单位均为 ATR。 <strong>这里没有预设任何成功阈值：</strong>
    原始数据只展示是否存在 edge、以及有多大。结论要等积累 300–500 个区间之后才能下。
  </p>
  {body}
</div>
</body></html>"""

    with open(OUT_PATH, "w") as f:
        f.write(html)
    print(f"雷达实验室 dashboard generata: {OUT_PATH} ({counts})")


if __name__ == "__main__":
    generate()
