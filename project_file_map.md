# crypto-signal-engine 项目文件功能清单

> 项目根目录：`D:\feng\crypto-signal-engine-main`
> 路径列均相对根目录。⚠️ 标记「CI 未接入」的文件存在但当前 `scan.yml` 不调用（需手动加入工作流才会运行）。

## 一、CI 调度与总入口

| 文件名 | 功能（主要负责哪一块） | 路径 |
|--------|----------------------|------|
| scan.yml | GitHub Actions 工作流：每 5 分钟定时调度各扫描器、生成看板、提交 DB | .github/workflows/scan.yml |
| main.py | 旧框架 V2.1 离线入口（一次性 / `--loop`）：读配置→bootstrap→跑 signal_engine 全流程 | main.py |
| candles_runner.py | 增量拉取 H4/H1 K 线并入库（CI 第一步，按 config.ASSETS） | candles_runner.py |
| v3_scanner_runner.py | CI 薄包装：读 config+注入密钥→调 `core.v3_runner.run_v3_scan` | v3_scanner_runner.py |
| v41_scanner_runner.py | CI 薄包装→调 `core.v41_runner.run_v41_scan` | v41_scanner_runner.py |
| v41p1_scanner_runner.py | CI 薄包装→调 `core.v41p1_runner.run_v41p1_scan` | v41p1_scanner_runner.py |
| lh_scanner_runner.py | CI 薄包装→调 `core.lh_runner.run_lh_scan` | lh_scanner_runner.py |
| tt_scanner_runner.py | CI 薄包装→调 `core.tt_runner.run_tt_scan` | tt_scanner_runner.py |
| edge_lab_runner.py | CI 薄包装→调 `core.edge_lab_runner.run_edge_lab_scan` | edge_lab_runner.py |
| ote_scanner_runner.py | CI 薄包装→调 `core.ote_runner.run_ote_scan` | ote_scanner_runner.py |
| market_radar_scanner_runner.py | CI 薄包装→调 `core.market_radar_runner.run_radar_scan` | market_radar_scanner_runner.py |
| v4_scanner_runner.py | ⚠️ CI 未接入：薄包装→`core.v4_runner.run_v4_scan`（需 config.V4_SCANNER.enabled 并加入 scan.yml） | v4_scanner_runner.py |
| v3d_scanner_runner.py | ⚠️ CI 未接入：薄包装→`core.v3d_runner.run_v3d_scan`（实验版） | v3d_scanner_runner.py |
| daily_brief_runner.py | 每日简报入口（扫描条件：08:00 UTC 触发） | daily_brief_runner.py |
| lh_digest_runner.py | LH 隔夜计划（重启区域摘要）入口（19:00 UTC 触发） | lh_digest_runner.py |
| cleanup_snapshots.py | 清理过期/冗余快照表，控制 DB 体积 | cleanup_snapshots.py |

## 二、行情数据源

| 文件名 | 功能（主要负责哪一块） | 路径 |
|--------|----------------------|------|
| core/data_source.py | 数据源路由 + 限频：`BTC/ETH/SOL→OKX`、`XAU_USD→Twelve Data`；选 provider、判定是否该抓取 | core/data_source.py |
| core/exchange.py | Crypto.com 公共行情 provider（H4/H1 历史与增量 K 线） | core/exchange.py |
| core/exchange_okx.py | 欧易公共行情 provider（永续 `ETH-USDT-SWAP` 等），替代 Crypto.com；`_request`/`_inst_id`/`PERP_MAP` | core/exchange_okx.py |
| core/exchange_twelvedata.py | Twelve Data provider（黄金 XAU_USD，带每日预算限频） | core/exchange_twelvedata.py |
| core/v3_exchange.py | V3 族专属行情 provider（D1/M30/M15，原 Crypto.com `_request_candlestick`） | core/v3_exchange.py |
| storage/db.py | SQLite 连接、K 线缓存表、信号/交易表读写（统一 DB 访问层） | storage/db.py |

## 三、核心扫描 Runner（实际执行扫描 + 推送）

| 文件名 | 功能（主要负责哪一块） | 路径 |
|--------|----------------------|------|
| core/v3_runner.py | Institutional Scanner V3 扫描（D1/M30/M15/H4/H1 多级结构与 OTE 评估） | core/v3_runner.py |
| core/v3d_runner.py | V3 Dynamic 实验版扫描（H4 作质量因子） | core/v3d_runner.py |
| core/v41_runner.py | Institutional Scanner V4.1 Intraday Wave 扫描 | core/v41_runner.py |
| core/v41p1_runner.py | V4.1 Phase 1 资金流 / 盘中边沿扫描（含 MFM 与 context 富化） | core/v41p1_runner.py |
| core/v4_runner.py | Institutional Scanner V4 Daily Edition 扫描 | core/v4_runner.py |
| core/lh_runner.py | Liquidity Hunter 重启区域扫描 + 区域临近/到达/信号推送 + 隔夜摘要（中文已汉化） | core/lh_runner.py |
| core/tt_runner.py | TT（Turtle/Trend Trigger）POI 触发确认扫描 | core/tt_runner.py |
| core/ote_runner.py | OTE（最优入场区）候选/信号扫描与盯盘 | core/ote_runner.py |
| core/edge_lab_runner.py | Edge Lab（OTE-SC + Trend Rider，共享 market context）扫描 | core/edge_lab_runner.py |
| core/trend_rider_runner.py | Trend Rider 均衡版扫描（趋势 + H1/H4 + ADX + 保本移动） | core/trend_rider_runner.py |
| core/market_radar_runner.py | Market Radar V1 区域登记与特征计算（MAE/MFE/速度/耗尽） | core/market_radar_runner.py |
| core/daily_brief.py | 每日简报文案构建与发送（宏观事件 + H4 偏向 + 订单区块 + 支撑阻力） | core/daily_brief.py |
| core/signal_engine.py | 旧框架核心：bootstrap_all / update_candles / run_scan_cycle（main.py 走它） | core/signal_engine.py |

## 四、策略算法（strategies/）

| 文件名 | 功能（主要负责哪一块） | 路径 |
|--------|----------------------|------|
| strategies/base.py | 信号基类 `Signal` + 策略基类 `BaseStrategy` | strategies/base.py |
| strategies/institutional_scanner_v3.py | V3 多级结构 / OTE / 动量 / 目标排序评估算法 | strategies/institutional_scanner_v3.py |
| strategies/institutional_scanner_v3_dynamic.py | V3 Dynamic 评估算法 | strategies/institutional_scanner_v3_dynamic.py |
| strategies/institutional_scanner_v41.py | V4.1 流动性扫描 / 动量 / SR 反应 / Fibonacci / 止损算法 | strategies/institutional_scanner_v41.py |
| strategies/institutional_scanner_v4.py | V4 EMA 趋势评估算法 | strategies/institutional_scanner_v4.py |
| strategies/liquidity_hunter.py | LH 重启区域 / 冲动 / OB / 评分 / 重复次数算法 | strategies/liquidity_hunter.py |
| strategies/liquidity_sweep.py | 流动性扫荡策略类 `LiquiditySweep` | strategies/liquidity_sweep.py |
| strategies/money_flow_map.py | 资金流地图构建（V4.1 Phase1 用） | strategies/money_flow_map.py |
| strategies/ote/confluence_engine.py | OTE 多源汇聚区检测（LH/OB/FVG/摆动/反应图/会话） | strategies/ote/confluence_engine.py |
| strategies/tt/direction_engine.py | TT 方向引擎（4H 摆动 / BOS / HH-HL） | strategies/tt/direction_engine.py |
| strategies/tt/liquidity_engine.py | TT 流动性引擎（POI 上下文 / 扫荡 / 反应 / 动态目标） | strategies/tt/liquidity_engine.py |
| strategies/tt/location_engine.py | TT 位置引擎（活跃均衡区 / FVG / 优选区选择） | strategies/tt/location_engine.py |
| strategies/edge_lab/fibonacci_engine.py | Edge Lab Fibonacci 水平计算 | strategies/edge_lab/fibonacci_engine.py |
| strategies/edge_lab/liquidity_engine.py | Edge Lab 流动性地图构建 | strategies/edge_lab/liquidity_engine.py |
| strategies/edge_lab/market_context_engine.py | Edge Lab 市场上下文构建 | strategies/edge_lab/market_context_engine.py |
| strategies/edge_lab/session_engine.py | Edge Lab 会话（欧洲综合 / OTE 区 / 罗马时区）引擎 | strategies/edge_lab/session_engine.py |
| strategies/edge_lab/sr_engine.py | Edge Lab 支撑/阻力地图构建 | strategies/edge_lab/sr_engine.py |
| strategies/edge_lab/trend_engine.py | Edge Lab 趋势（Dow+EMA 对齐 / H1/H4）引擎 | strategies/edge_lab/trend_engine.py |
| strategies/edge_lab/trend_rider.py | Edge Lab Trend Rider 信号生成算法 | strategies/edge_lab/trend_rider.py |
| strategies/edge_lab/ote_sc.py | Edge Lab OTE-SC 信号检测与生成 | strategies/edge_lab/ote_sc.py |
| strategies/edge_lab/volatility_macro_engine.py | Edge Lab 波动率 / 宏观上下文引擎 | strategies/edge_lab/volatility_macro_engine.py |
| strategies/breakout_retest.py | 突破回踩策略类 `BreakoutRetest` | strategies/breakout_retest.py |
| strategies/compression_breakout.py | 压缩突破策略类 `CompressionBreakout` | strategies/compression_breakout.py |
| strategies/pivot_reversal.py | 枢轴反转策略类 `PivotReversal` | strategies/pivot_reversal.py |
| strategies/pullback_ema_frozen.py | EMA 回调冻结策略类 `PullbackEMAFrozen` | strategies/pullback_ema_frozen.py |
| strategies/zone_confirmation.py | 区域确认策略类 `ZoneConfirmation` | strategies/zone_confirmation.py |

## 五、通用引擎 / 指标（core/）

| 文件名 | 功能（主要负责哪一块） | 路径 |
|--------|----------------------|------|
| core/indicators.py | EMA / ATR / 枢轴 / 水平聚类等基础技术指标 | core/indicators.py |
| core/structure_engine.py | 市场结构引擎（BOS/CHoCH/摆点/回调/位移） | core/structure_engine.py |
| core/structure_engine_v2.py | 市场结构引擎 v2（最新版，含趋势健康/置信度） | core/structure_engine_v2.py |
| core/structure_db.py | 结构状态 / 快照存储 | core/structure_db.py |
| core/order_block_engine.py | 订单区块（OB）检测引擎 | core/order_block_engine.py |
| core/fvg_engine.py | 公允价值缺口（FVG）检测引擎 | core/fvg_engine.py |
| core/liquidity_engine_v2.py | 流动性水平 / 扫荡检测引擎 | core/liquidity_engine_v2.py |
| core/session_sweep_engine.py | 交易时段扫荡快照引擎 | core/session_sweep_engine.py |
| core/reaction_map.py | 反应地图（多源区域合并）引擎 | core/reaction_map.py |
| core/candlestick_engine.py | K 线形态（锤子/吞没/十字星/pin bar）快照引擎 | core/candlestick_engine.py |
| core/market_regime.py | 市场状态（ADX 趋势）判定 | core/market_regime.py |
| core/market_state_model.py | 市场状态问答模型（where/why/who/going/strong/when） | core/market_state_model.py |
| core/macro.py | 宏观事件 provider（YAML / 默认）工厂 | core/macro.py |
| core/macro_context_engine.py | 宏观上下文（新闻情绪 / 跨市场）快照引擎 | core/macro_context_engine.py |
| core/volatility_engine.py | 波动率（ATR 百分位 / 扩张收缩 / 24h 区间）快照引擎 | core/volatility_engine.py |
| core/correlation_engine.py | 多资产相关性过滤 | core/correlation_engine.py |
| core/scoring.py | 信号评分与分级（compute_score / classify_score） | core/scoring.py |
| core/trade_manager.py | 持仓 / 信号盯盘与冷却（v1） | core/trade_manager.py |
| core/trade_manager_v2.py | 持仓 / 信号盯盘与冷却（v2） | core/trade_manager_v2.py |
| core/strategy.py | 旧框架策略评估（long/short） | core/strategy.py |
| core/strategy_registry.py | 旧框架策略注册表 | core/strategy_registry.py |
| core/replay_engine.py | 历史回放（策略验证） | core/replay_engine.py |

## 六、数据库层（core/*_db.py，各信号/区域表）

| 文件名 | 功能（主要负责哪一块） | 路径 |
|--------|----------------------|------|
| core/v3_db.py | V3 蜡烛缓存 + 信号表读写 | core/v3_db.py |
| core/v41_db.py | V4.1 信号 / 看板状态表读写 | core/v41_db.py |
| core/v41p1_db.py | V4.1 Phase1 信号 / MFM 快照 / 看板状态表读写 | core/v41p1_db.py |
| core/v4_db.py | V4 信号表读写 | core/v4_db.py |
| core/lh_db.py | LH 信号 / 区域告警 / 重复次数表读写 | core/lh_db.py |
| core/tt_db.py | TT 信号 / POI 等待状态表读写 | core/tt_db.py |
| core/ote_db.py | OTE 候选 / 信号表读写 | core/ote_db.py |
| core/edge_lab_db.py | Edge Lab 市场上下文 / 信号表读写 | core/edge_lab_db.py |
| core/trend_rider_db.py | Trend Rider 信号 / 区域引用表读写 | core/trend_rider_db.py |
| core/market_radar_db.py | Market Radar 区域 / 转换状态表读写 | core/market_radar_db.py |

## 七、决策账本（decision_ledger）

| 文件名 | 功能（主要负责哪一块） | 路径 |
|--------|----------------------|------|
| core/decision_ledger/decision_collector.py | 汇总各维度快照（结构/趋势/波动/OB/FVG/流动性/宏观…）生成决策记录 | core/decision_ledger/decision_collector.py |
| core/decision_ledger/ledger_writer.py | 决策账本 DB 连接 / 写入 / 结果回写 / 过期清理 | core/decision_ledger/ledger_writer.py |
| core/decision_ledger/lh_integration.py | LH 决策 ↔ 账本对接（执行/拒绝/结果） | core/decision_ledger/lh_integration.py |
| core/decision_ledger/ote_integration.py | OTE 候选/执行 ↔ 账本对接 | core/decision_ledger/ote_integration.py |
| core/decision_ledger/tt_integration.py | TT 决策 ↔ 账本对接 | core/decision_ledger/tt_integration.py |
| core/decision_ledger/trb_integration.py | Trend Rider 决策 ↔ 账本对接 | core/decision_ledger/trb_integration.py |
| core/decision_ledger/v41p1_integration.py | V4.1 Phase1 决策 ↔ 账本对接 | core/decision_ledger/v41p1_integration.py |
| core/decision_ledger/edge_lab_integration.py | Edge Lab 执行/拒绝/结果 ↔ 账本对接 | core/decision_ledger/edge_lab_integration.py |

## 八、推送通知（notifications/）

| 文件名 | 功能（主要负责哪一块） | 路径 |
|--------|----------------------|------|
| notifications/telegram_bot.py | Telegram 发送 + 通用信号/区域告警格式化（中文已汉化） | notifications/telegram_bot.py |
| notifications/ntfy_bot.py | ntfy 发送 + 格式化（中文已汉化） | notifications/ntfy_bot.py |
| notifications/v3_telegram.py | V3 信号告警格式化与发送（活跃 formatter） | notifications/v3_telegram.py |
| notifications/v4_telegram.py | V4 信号告警格式化与发送（活跃 formatter） | notifications/v4_telegram.py |
| notifications/v41_telegram.py | V4.1 信号/看板告警格式化（⚠️ 死代码，runner 未引用） | notifications/v41_telegram.py |
| notifications/v41p1_telegram.py | V4.1 Phase1 信号/看板告警格式化与发送（活跃 formatter） | notifications/v41p1_telegram.py |

## 九、看板生成（generate_*.py）

| 文件名 | 功能（主要负责哪一块） | 路径 |
|--------|----------------------|------|
| generate_unified_dashboard.py | 统一看板（未平仓信号：TT/OTE/V41p1/TRB/LH 各表，含信号时间列） | generate_unified_dashboard.py |
| generate_analytics_dashboard.py | 分析看板（历史信号绩效统计） | generate_analytics_dashboard.py |
| generate_engine_edge_dashboard.py | 引擎边沿 / 策略胜率看板 | generate_engine_edge_dashboard.py |
| generate_radar_lab_dashboard.py | Radar Lab 看板（区域速度 / 首次触发 / MFE / MAE） | generate_radar_lab_dashboard.py |
| generate_dashboard.py | ⚠️ CI 未调用：旧版看板生成器 | generate_dashboard.py |
| generate_edge_lab_dashboard.py | ⚠️ CI 未调用：Edge Lab 旧看板生成器 | generate_edge_lab_dashboard.py |

## 十、工具 / 测试 / 配置

| 文件名 | 功能（主要负责哪一块） | 路径 |
|--------|----------------------|------|
| probe_okx.py | 一次性探针：验证 exchange_okx 能拉到 ETH-USDT-SWAP K 线 | probe_okx.py |
| test_exchange.py | 行情接口测试（计数 / 翻页） | test_exchange.py |
| test_telegram.py | Telegram 推送测试 | test_telegram.py |
| config.yaml | 主配置：资产列表 / 各策略开关 / 阈值 / API 基址 / 密钥注入 | config.yaml |
| macro_events.yaml | 宏观高影响事件日历配置 | macro_events.yaml |
| requirements.txt | Python 依赖清单 | requirements.txt |
| docs/ | 生成的 HTML 看板静态页（`docs_it_backup/` 为旧意大利语备份） | docs/ |
| data/ | 运行时 SQLite 数据库（signals.db / decision_ledger.db 等） | data/ |
| logs/ | 运行日志 | logs/ |
