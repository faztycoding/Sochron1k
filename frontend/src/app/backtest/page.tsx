"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Play,
  TrendingDown,
  TrendingUp,
  XCircle,
} from "lucide-react";

import { api } from "@/lib/api";
import type { BacktestResponse, StrategyMetadata } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PAIRS, TIMEFRAMES } from "@/lib/constants";
import { EquityCurve } from "@/components/backtest/equity-curve";

export default function BacktestPage() {
  const [strategies, setStrategies] = useState<StrategyMetadata[]>([]);
  const [pair, setPair] = useState("EUR/USD");
  const [timeframe, setTimeframe] = useState("1h");
  const [strategy, setStrategy] = useState("ema_crossover");
  const [lookback, setLookback] = useState("500");
  const [balance, setBalance] = useState("1000");
  const [riskPct, setRiskPct] = useState("1.0");
  const [slMult, setSlMult] = useState("1.5");
  const [tpMult, setTpMult] = useState("3.0");
  const [spread, setSpread] = useState("1.5");

  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.backtest.strategies().then(setStrategies).catch(() => {});
  }, []);

  const currentStrategy = useMemo(
    () => strategies.find((s) => s.name === strategy),
    [strategies, strategy],
  );

  const handleRun = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.backtest.run(pair, {
        strategy,
        timeframe,
        lookback: parseInt(lookback),
        initial_balance: parseFloat(balance),
        risk_percent: parseFloat(riskPct),
        sl_atr_mult: parseFloat(slMult),
        tp_atr_mult: parseFloat(tpMult),
        spread_pips: parseFloat(spread),
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "รัน backtest ล้มเหลว");
    }
    setLoading(false);
  }, [pair, strategy, timeframe, lookback, balance, riskPct, slMult, tpMult, spread]);

  const isProfitable = result && result.total_return_pct > 0;
  const isJPY = pair.includes("JPY");
  const fmtPrice = (v: number | null) => (v !== null ? v.toFixed(isJPY ? 3 : 5) : "—");

  return (
    <main className="min-h-screen p-4 sm:p-6 max-w-7xl mx-auto animate-fade-in">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="p-2 rounded-lg hover:bg-bg-surface transition-colors">
          <ArrowLeft className="w-5 h-5 text-text-muted" />
        </Link>
        <BarChart3 className="w-5 h-5 text-accent-400" />
        <h1 className="text-xl font-bold gradient-text">Backtest</h1>
        <span className="ml-2 text-xs text-text-muted">ทดสอบกลยุทธ์กับแท่งเทียนย้อนหลัง</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-5">
        {/* ========== Form ========== */}
        <Card>
          <CardHeader>
            <CardTitle>ตั้งค่า</CardTitle>
          </CardHeader>

          <div className="flex flex-col gap-4">
            {/* Strategy */}
            <div>
              <label className="text-xs text-text-muted mb-1 block">กลยุทธ์</label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-border text-sm focus:border-primary-500 focus:outline-none transition-colors"
              >
                {strategies.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.display_name}
                  </option>
                ))}
              </select>
              {currentStrategy && (
                <p className="text-xs text-text-muted mt-1.5">{currentStrategy.description}</p>
              )}
            </div>

            {/* Pair */}
            <div>
              <label className="text-xs text-text-muted mb-1 block">คู่เงิน</label>
              <div className="grid grid-cols-3 gap-1 p-1 rounded-xl bg-bg-surface">
                {PAIRS.map((p) => (
                  <button
                    key={p}
                    onClick={() => setPair(p)}
                    className={`px-2 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      pair === p
                        ? "bg-primary-600 text-white"
                        : "text-text-secondary hover:bg-bg-elevated"
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {/* Timeframe */}
            <div>
              <label className="text-xs text-text-muted mb-1 block">Timeframe</label>
              <div className="flex gap-1 p-1 rounded-xl bg-bg-surface">
                {TIMEFRAMES.map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setTimeframe(tf)}
                    className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      timeframe === tf
                        ? "bg-accent-500 text-white"
                        : "text-text-secondary hover:bg-bg-elevated"
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>

            {/* Lookback + Balance */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-text-muted mb-1 block">แท่งย้อนหลัง</label>
                <input
                  type="number"
                  value={lookback}
                  onChange={(e) => setLookback(e.target.value)}
                  min={50}
                  max={5000}
                  className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-border text-sm font-mono focus:border-primary-500 focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-text-muted mb-1 block">ทุนเริ่ม ($)</label>
                <input
                  type="number"
                  value={balance}
                  onChange={(e) => setBalance(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-border text-sm font-mono focus:border-primary-500 focus:outline-none transition-colors"
                />
              </div>
            </div>

            {/* Risk + Spread */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-text-muted mb-1 block">ความเสี่ยง (%)</label>
                <input
                  type="number"
                  value={riskPct}
                  onChange={(e) => setRiskPct(e.target.value)}
                  step="0.1"
                  min="0.1"
                  max="10"
                  className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-border text-sm font-mono focus:border-primary-500 focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-text-muted mb-1 block">Spread (pips)</label>
                <input
                  type="number"
                  value={spread}
                  onChange={(e) => setSpread(e.target.value)}
                  step="0.1"
                  min="0"
                  className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-border text-sm font-mono focus:border-primary-500 focus:outline-none transition-colors"
                />
              </div>
            </div>

            {/* SL/TP ATR multipliers */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-sell mb-1 block">SL x ATR</label>
                <input
                  type="number"
                  value={slMult}
                  onChange={(e) => setSlMult(e.target.value)}
                  step="0.1"
                  min="0.5"
                  max="5"
                  className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-sell/30 text-sm font-mono focus:border-sell focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-buy mb-1 block">TP x ATR</label>
                <input
                  type="number"
                  value={tpMult}
                  onChange={(e) => setTpMult(e.target.value)}
                  step="0.1"
                  min="0.5"
                  max="10"
                  className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-buy/30 text-sm font-mono focus:border-buy focus:outline-none transition-colors"
                />
              </div>
            </div>

            <button
              onClick={handleRun}
              disabled={loading}
              className="flex items-center justify-center gap-2 py-3 rounded-xl bg-primary-600 hover:bg-primary-500 text-white font-semibold text-sm transition-colors disabled:opacity-50"
            >
              <Play className={`w-4 h-4 ${loading ? "animate-pulse" : ""}`} />
              {loading ? "กำลังคำนวณ..." : "รัน Backtest"}
            </button>

            {error && (
              <div className="flex items-start gap-2 text-xs text-danger">
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                {error}
              </div>
            )}
          </div>
        </Card>

        {/* ========== Results ========== */}
        <div className="flex flex-col gap-5">
          {/* Summary cards */}
          {result ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard
                  label="ผลตอบแทน"
                  value={`${result.total_return_pct > 0 ? "+" : ""}${result.total_return_pct.toFixed(2)}%`}
                  sub={`$${result.initial_balance.toLocaleString()} → $${result.final_balance.toLocaleString()}`}
                  tone={isProfitable ? "up" : "down"}
                  icon={isProfitable ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                />
                <StatCard
                  label="Win Rate"
                  value={`${result.win_rate.toFixed(1)}%`}
                  sub={`W ${result.wins} / L ${result.losses}`}
                  tone={result.win_rate >= 50 ? "up" : "down"}
                />
                <StatCard
                  label="Profit Factor"
                  value={result.profit_factor.toFixed(2)}
                  sub={`Pips: ${result.total_pips > 0 ? "+" : ""}${result.total_pips}`}
                  tone={result.profit_factor >= 1.5 ? "up" : result.profit_factor >= 1 ? "neutral" : "down"}
                />
                <StatCard
                  label="Max Drawdown"
                  value={`${result.max_drawdown_pct.toFixed(2)}%`}
                  sub={`Sharpe ${result.sharpe.toFixed(2)}`}
                  tone={result.max_drawdown_pct > -10 ? "up" : result.max_drawdown_pct > -20 ? "neutral" : "down"}
                />
              </div>

              {/* Equity curve */}
              <Card>
                <CardHeader>
                  <CardTitle>Equity Curve</CardTitle>
                  <span className="text-xs text-text-muted">
                    {result.candle_count} แท่ง · {result.start?.slice(0, 10)} → {result.end?.slice(0, 10)}
                  </span>
                </CardHeader>
                <EquityCurve data={result.equity_curve} initialBalance={result.initial_balance} height={280} />
              </Card>

              {/* Trade table */}
              <Card>
                <CardHeader>
                  <CardTitle>รายการเทรด ({result.trades.length})</CardTitle>
                </CardHeader>

                {result.trades.length === 0 ? (
                  <p className="text-sm text-text-muted text-center py-6">
                    กลยุทธ์ไม่มีสัญญาณในช่วงนี้ — ลองเปลี่ยน TF หรือเพิ่ม lookback
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="text-text-muted">
                        <tr className="border-b border-border">
                          <th className="text-left py-2 px-2 font-medium">#</th>
                          <th className="text-left py-2 px-2 font-medium">Entry</th>
                          <th className="text-left py-2 px-2 font-medium">Exit</th>
                          <th className="text-left py-2 px-2 font-medium">Dir</th>
                          <th className="text-right py-2 px-2 font-medium">Entry $</th>
                          <th className="text-right py-2 px-2 font-medium">Exit $</th>
                          <th className="text-right py-2 px-2 font-medium">Pips</th>
                          <th className="text-right py-2 px-2 font-medium">P&amp;L</th>
                          <th className="text-left py-2 px-2 font-medium">Reason</th>
                        </tr>
                      </thead>
                      <tbody className="font-mono">
                        {result.trades.map((t, i) => {
                          const win = (t.pnl ?? 0) > 0;
                          return (
                            <tr key={i} className="border-b border-border/40 hover:bg-bg-surface/40">
                              <td className="py-1.5 px-2 text-text-muted">{i + 1}</td>
                              <td className="py-1.5 px-2">{t.entry_time?.slice(5, 16).replace("T", " ")}</td>
                              <td className="py-1.5 px-2">{t.exit_time?.slice(5, 16).replace("T", " ") ?? "—"}</td>
                              <td className="py-1.5 px-2">
                                <Badge variant={t.direction === "BUY" ? "buy" : "sell"}>{t.direction}</Badge>
                              </td>
                              <td className="py-1.5 px-2 text-right">{fmtPrice(t.entry_price)}</td>
                              <td className="py-1.5 px-2 text-right">{fmtPrice(t.exit_price)}</td>
                              <td className={`py-1.5 px-2 text-right font-semibold ${win ? "text-buy" : "text-sell"}`}>
                                {t.pips && t.pips > 0 ? "+" : ""}
                                {t.pips?.toFixed(1) ?? "—"}
                              </td>
                              <td className={`py-1.5 px-2 text-right font-semibold ${win ? "text-buy" : "text-sell"}`}>
                                {t.pnl && t.pnl > 0 ? "+" : ""}${t.pnl?.toFixed(2) ?? "—"}
                              </td>
                              <td className="py-1.5 px-2 text-text-muted">
                                <div className="flex items-center gap-1.5">
                                  {win ? (
                                    <CheckCircle2 className="w-3 h-3 text-buy" />
                                  ) : (
                                    <XCircle className="w-3 h-3 text-sell" />
                                  )}
                                  <span className="truncate max-w-[160px]">{t.reason_out}</span>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
            </>
          ) : (
            <Card>
              <div className="flex flex-col items-center justify-center text-center py-16 gap-3">
                <BarChart3 className="w-12 h-12 text-text-muted/40" />
                <p className="text-sm text-text-muted max-w-sm">
                  เลือกกลยุทธ์และคู่เงิน แล้วกด <span className="font-medium">รัน Backtest</span> <br />
                  เพื่อทดสอบผลตอบแทนกับข้อมูลย้อนหลัง ก่อนจะเทรดด้วยเงินจริง
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </main>
  );
}

function StatCard({
  label,
  value,
  sub,
  tone,
  icon,
}: {
  label: string;
  value: string;
  sub?: string;
  tone: "up" | "down" | "neutral";
  icon?: React.ReactNode;
}) {
  const toneClasses = {
    up: "text-buy border-buy/20 bg-buy/5",
    down: "text-sell border-sell/20 bg-sell/5",
    neutral: "text-text-secondary border-border bg-bg-surface/40",
  }[tone];

  return (
    <div className={`rounded-xl border p-3 ${toneClasses}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-text-muted">{label}</span>
        {icon}
      </div>
      <div className="text-xl font-bold font-mono mt-1">{value}</div>
      {sub && <div className="text-xs text-text-muted mt-0.5">{sub}</div>}
    </div>
  );
}
