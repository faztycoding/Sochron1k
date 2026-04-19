"use client";

import { useCallback, useEffect, useState } from "react";
import { BarChart3, LineChart, RefreshCw, Shield, Zap } from "lucide-react";

import { api } from "@/lib/api";
import type { AnalysisResult, CandleData, IndicatorSnapshot } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { TradingChart } from "@/components/chart/trading-chart";
import { TradingViewWidget } from "@/components/chart/tradingview-widget";
import { PairQuoteCard } from "@/components/chart/pair-quote-card";
import { PAIRS, TIMEFRAMES } from "@/lib/constants";

export default function AnalysisPage() {
  const [pair, setPair] = useState("EUR/USD");
  const [timeframe, setTimeframe] = useState("1h");
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [indicators, setIndicators] = useState<IndicatorSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [chartMode, setChartMode] = useState<"pro" | "analysis">("pro");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // Load candles first (fast)
      const candleRes = await api.prices.candles(pair, timeframe).catch(() => null);
      if (candleRes) setCandles(candleRes.candles);

      // Then analysis + indicators sequentially
      const analysisRes = await api.analysis.run(pair, timeframe).catch(() => null);
      if (analysisRes) setAnalysis(analysisRes);

      const indRes = await api.indicators.get(pair, timeframe).catch(() => null);
      if (indRes) setIndicators(indRes);
    } catch {
      // handled gracefully
    }
    setLoading(false);
  }, [pair, timeframe]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const dir = analysis?.direction;
  const conf = analysis?.confidence ?? 0;

  return (
    <main className="min-h-screen px-4 sm:px-6 py-4 max-w-7xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold gradient-text">วิเคราะห์เชิงลึก</h1>
        <div className="flex items-center gap-2">
          {/* Chart mode toggle */}
          <div className="flex gap-1 p-1 rounded-lg bg-bg-surface">
            <button
              onClick={() => setChartMode("pro")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                chartMode === "pro"
                  ? "bg-accent-500 text-white"
                  : "text-text-muted hover:text-text-primary"
              }`}
              title="กราฟ Pro — ซูม ตีเส้น วาดได้"
            >
              <BarChart3 className="w-3.5 h-3.5" />
              Pro
            </button>
            <button
              onClick={() => setChartMode("analysis")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                chartMode === "analysis"
                  ? "bg-accent-500 text-white"
                  : "text-text-muted hover:text-text-primary"
              }`}
              title="กราฟวิเคราะห์ — ข้อมูลจากระบบ"
            >
              <LineChart className="w-3.5 h-3.5" />
              Analysis
            </button>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-sm font-medium transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            วิเคราะห์ใหม่
          </button>
        </div>
      </div>

      {/* Pair Quote Card — TradingView-style quote with performance grid */}
      <div className="mb-4">
        <PairQuoteCard pair={pair} />
      </div>

      {/* Pair + Timeframe selectors */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex gap-1 p-1 rounded-xl bg-bg-surface">
          {PAIRS.map((p) => (
            <button
              key={p}
              onClick={() => setPair(p)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                pair === p
                  ? "bg-primary-600 text-white"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        <div className="flex gap-1 p-1 rounded-xl bg-bg-surface">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                timeframe === tf
                  ? "bg-accent-500 text-white"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Chart — Pro or Analysis */}
      <div className="mb-5">
        {chartMode === "pro" ? (
          <TradingViewWidget pair={pair} timeframe={timeframe} height={520} />
        ) : (
          <TradingChart candles={candles} pair={pair} height={450} />
        )}
      </div>

      {/* Analysis panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Signal Panel */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-accent-400" />
              <CardTitle>สัญญาณ</CardTitle>
            </div>
            {dir && (
              <Badge variant={dir === "BUY" ? "buy" : dir === "SELL" ? "sell" : "neutral"}>
                {dir}
              </Badge>
            )}
          </CardHeader>

          {analysis ? (
            <div className="flex flex-col gap-3">
              {/* Confidence meter */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-text-muted">ความมั่นใจ</span>
                  <span className="font-mono font-semibold">{(conf * 100).toFixed(0)}%</span>
                </div>
                <div className="h-3 rounded-full bg-bg-surface overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${conf * 100}%`,
                      background:
                        conf >= 0.75
                          ? "linear-gradient(90deg, #22c55e, #06b6d4)"
                          : conf >= 0.5
                            ? "linear-gradient(90deg, #f59e0b, #eab308)"
                            : "linear-gradient(90deg, #ef4444, #dc2626)",
                    }}
                  />
                </div>
              </div>

              <p className="text-sm text-text-secondary">{analysis.recommendation}</p>

              {/* Breakdown */}
              <div className="flex flex-col gap-1.5 text-xs">
                {Object.entries(analysis.confidence_breakdown).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-text-muted capitalize">{key}</span>
                    <span className="font-mono text-text-secondary">{((val as number) * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>

              {/* SL/TP */}
              {analysis.suggested_sl && analysis.suggested_tp && (
                <div className="p-3 rounded-xl bg-bg-surface/50 text-sm font-mono">
                  <div className="flex justify-between mb-1">
                    <span className="text-text-muted">Entry</span>
                    <span>{analysis.suggested_entry?.toFixed(pair.includes("JPY") ? 3 : 5)}</span>
                  </div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sell">SL</span>
                    <span className="text-sell">{analysis.suggested_sl.toFixed(pair.includes("JPY") ? 3 : 5)}</span>
                  </div>
                  <div className="flex justify-between mb-1">
                    <span className="text-buy">TP</span>
                    <span className="text-buy">{analysis.suggested_tp.toFixed(pair.includes("JPY") ? 3 : 5)}</span>
                  </div>
                  {analysis.risk_reward && (
                    <div className="flex justify-between pt-1 border-t border-border">
                      <span className="text-text-muted">R:R</span>
                      <span className="text-accent-400">1:{analysis.risk_reward.toFixed(1)}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-text-muted py-4 text-center">
              {loading ? "กำลังวิเคราะห์..." : "กดปุ่มวิเคราะห์ใหม่"}
            </p>
          )}
        </Card>

        {/* Indicators */}
        <Card>
          <CardHeader>
            <CardTitle>อินดิเคเตอร์</CardTitle>
          </CardHeader>
          {indicators ? (
            <div className="grid grid-cols-2 gap-2 text-sm">
              {[
                ["RSI", indicators.rsi],
                ["ADX", indicators.adx],
                ["MACD", indicators.macd_hist],
                ["CCI", indicators.cci],
                ["ATR", indicators.atr],
                ["Stoch K", indicators.stoch_k],
                ["EMA 9", indicators.ema_9],
                ["EMA 21", indicators.ema_21],
                ["Z-Score", indicators.z_score],
                ["BB Upper", indicators.bb_upper],
                ["BB Lower", indicators.bb_lower],
                ["OBV", indicators.obv],
              ].map(([label, val]) => (
                <div key={label as string} className="flex justify-between p-2 rounded-lg bg-bg-surface/30">
                  <span className="text-text-muted">{label as string}</span>
                  <span className="font-mono text-text-secondary">
                    {val !== undefined && val !== null ? (val as number).toFixed(4) : "—"}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted py-4 text-center">รอข้อมูล</p>
          )}
        </Card>

        {/* Diagnostics */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary-400" />
              <CardTitle>การวินิจฉัย</CardTitle>
            </div>
            {analysis && (
              <Badge
                variant={
                  analysis.diagnosis.overall_health === "HEALTHY"
                    ? "success"
                    : analysis.diagnosis.overall_health === "WARNING"
                      ? "warning"
                      : "danger"
                }
              >
                {analysis.diagnosis.overall_health}
              </Badge>
            )}
          </CardHeader>
          {analysis ? (
            <div className="flex flex-col gap-1.5 max-h-72 overflow-y-auto">
              {analysis.diagnosis.diagnostics
                .filter((d) => d.severity !== "ok")
                .map((d, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 p-2 rounded-lg bg-bg-surface/30 text-xs"
                  >
                    <span
                      className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${
                        d.severity === "critical"
                          ? "bg-danger"
                          : d.severity === "error"
                            ? "bg-warning"
                            : "bg-primary-400"
                      }`}
                    />
                    <div>
                      <p className="text-text-secondary">{d.message}</p>
                      {d.recommendation && (
                        <p className="text-text-muted mt-0.5">{d.recommendation}</p>
                      )}
                    </div>
                  </div>
                ))}
              {analysis.diagnosis.issues === 0 && (
                <p className="text-sm text-success py-4 text-center">ระบบปกติ ✅</p>
              )}

              {/* Regime + Session */}
              <div className="mt-2 pt-2 border-t border-border text-xs text-text-muted">
                <p>Regime: <span className="capitalize text-text-secondary">{analysis.regime.regime}</span></p>
                <p>Session: <span className="text-text-secondary">{analysis.session.session}</span></p>
                <p>วิเคราะห์ใน: <span className="text-text-secondary">{analysis.analysis_duration}s</span></p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-text-muted py-4 text-center">รอข้อมูล</p>
          )}
        </Card>
      </div>
    </main>
  );
}
