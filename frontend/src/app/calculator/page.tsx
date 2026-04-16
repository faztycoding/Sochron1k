"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Calculator, Sparkles, AlertTriangle } from "lucide-react";

import { tradeApi } from "@/lib/api-trade";
import type { CalculateResult, AutoSLTPResult } from "@/lib/api-trade";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const PAIRS = ["EUR/USD", "USD/JPY", "EUR/JPY"];

export default function CalculatorPage() {
  const [pair, setPair] = useState("EUR/USD");
  const [direction, setDirection] = useState<"BUY" | "SELL">("BUY");
  const [balance, setBalance] = useState("1000");
  const [riskPct, setRiskPct] = useState("2");
  const [entryPrice, setEntryPrice] = useState("");
  const [slPrice, setSlPrice] = useState("");
  const [tpPrice, setTpPrice] = useState("");
  const [result, setResult] = useState<CalculateResult | null>(null);
  const [autoResult, setAutoResult] = useState<AutoSLTPResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCalculate = async () => {
    if (!entryPrice) { setError("กรุณาใส่ราคา Entry"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await tradeApi.calculate({
        pair,
        direction,
        account_balance: parseFloat(balance),
        risk_percent: parseFloat(riskPct),
        entry_price: parseFloat(entryPrice),
        sl_price: slPrice ? parseFloat(slPrice) : undefined,
        tp_price: tpPrice ? parseFloat(tpPrice) : undefined,
      });
      setResult(res);
      setAutoResult(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "คำนวณล้มเหลว");
    }
    setLoading(false);
  };

  const handleAutoSL = async () => {
    if (!entryPrice) { setError("กรุณาใส่ราคา Entry"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await tradeApi.autoSL({
        pair,
        direction,
        entry_price: parseFloat(entryPrice),
      });
      setAutoResult(res);
      setSlPrice(String(res.sl_price));
      setTpPrice(String(res.tp_price));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Auto SL/TP ล้มเหลว");
    }
    setLoading(false);
  };

  const isJPY = pair.includes("JPY");
  const fmt = (v: number) => v.toFixed(isJPY ? 3 : 5);

  return (
    <main className="min-h-screen p-4 sm:p-6 max-w-4xl mx-auto animate-fade-in">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="p-2 rounded-lg hover:bg-bg-surface transition-colors">
          <ArrowLeft className="w-5 h-5 text-text-muted" />
        </Link>
        <Calculator className="w-5 h-5 text-accent-400" />
        <h1 className="text-xl font-bold gradient-text">คำนวณเทรด</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Input Form */}
        <Card>
          <CardHeader>
            <CardTitle>ข้อมูลเทรด</CardTitle>
          </CardHeader>

          <div className="flex flex-col gap-4">
            {/* Pair */}
            <div>
              <label className="text-xs text-text-muted mb-1 block">คู่เงิน</label>
              <div className="flex gap-1 p-1 rounded-xl bg-bg-surface">
                {PAIRS.map((p) => (
                  <button
                    key={p}
                    onClick={() => setPair(p)}
                    className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                      pair === p ? "bg-primary-600 text-white" : "text-text-secondary hover:bg-bg-elevated"
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {/* Direction */}
            <div>
              <label className="text-xs text-text-muted mb-1 block">ทิศทาง</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setDirection("BUY")}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                    direction === "BUY"
                      ? "bg-buy/20 text-buy border border-buy/40"
                      : "bg-bg-surface text-text-muted border border-border"
                  }`}
                >
                  BUY
                </button>
                <button
                  onClick={() => setDirection("SELL")}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                    direction === "SELL"
                      ? "bg-sell/20 text-sell border border-sell/40"
                      : "bg-bg-surface text-text-muted border border-border"
                  }`}
                >
                  SELL
                </button>
              </div>
            </div>

            {/* Balance + Risk */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-text-muted mb-1 block">ทุน ($)</label>
                <input
                  type="number"
                  value={balance}
                  onChange={(e) => setBalance(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-border text-sm font-mono focus:border-primary-500 focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-text-muted mb-1 block">ความเสี่ยง (%)</label>
                <input
                  type="number"
                  value={riskPct}
                  onChange={(e) => setRiskPct(e.target.value)}
                  step="0.5"
                  className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-border text-sm font-mono focus:border-primary-500 focus:outline-none transition-colors"
                />
              </div>
            </div>

            {/* Entry */}
            <div>
              <label className="text-xs text-text-muted mb-1 block">ราคา Entry</label>
              <input
                type="number"
                value={entryPrice}
                onChange={(e) => setEntryPrice(e.target.value)}
                step={isJPY ? "0.01" : "0.00001"}
                placeholder={isJPY ? "150.000" : "1.08500"}
                className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-border text-sm font-mono focus:border-primary-500 focus:outline-none transition-colors"
              />
            </div>

            {/* SL / TP */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-sell mb-1 block">SL ราคา</label>
                <input
                  type="number"
                  value={slPrice}
                  onChange={(e) => setSlPrice(e.target.value)}
                  step={isJPY ? "0.01" : "0.00001"}
                  className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-sell/30 text-sm font-mono focus:border-sell focus:outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-buy mb-1 block">TP ราคา</label>
                <input
                  type="number"
                  value={tpPrice}
                  onChange={(e) => setTpPrice(e.target.value)}
                  step={isJPY ? "0.01" : "0.00001"}
                  className="w-full px-3 py-2.5 rounded-xl bg-bg-surface border border-buy/30 text-sm font-mono focus:border-buy focus:outline-none transition-colors"
                />
              </div>
            </div>

            {/* Buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleCalculate}
                disabled={loading}
                className="flex-1 py-3 rounded-xl bg-primary-600 hover:bg-primary-500 text-white font-semibold text-sm transition-colors disabled:opacity-50"
              >
                คำนวณ
              </button>
              <button
                onClick={handleAutoSL}
                disabled={loading}
                className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-accent-500/20 hover:bg-accent-500/30 text-accent-400 font-medium text-sm transition-colors border border-accent-500/30"
              >
                <Sparkles className="w-4 h-4" />
                Auto SL/TP
              </button>
            </div>

            {error && (
              <p className="text-sm text-danger">{error}</p>
            )}
          </div>
        </Card>

        {/* Result */}
        <Card>
          <CardHeader>
            <CardTitle>ผลคำนวณ</CardTitle>
          </CardHeader>

          {!result && !autoResult && (
            <p className="text-sm text-text-muted text-center py-12">กรอกข้อมูลแล้วกดคำนวณ</p>
          )}

          {autoResult && !result && (
            <div className="flex flex-col gap-3">
              <Badge variant="default">
                <Sparkles className="w-3 h-3 mr-1" />
                Auto SL/TP ({autoResult.method})
              </Badge>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="p-3 rounded-xl bg-bg-surface">
                  <span className="text-text-muted block text-xs">SL</span>
                  <span className="font-mono text-sell">{fmt(autoResult.sl_price)}</span>
                  <span className="text-xs text-text-muted ml-1">({autoResult.sl_pips} pips)</span>
                </div>
                <div className="p-3 rounded-xl bg-bg-surface">
                  <span className="text-text-muted block text-xs">TP</span>
                  <span className="font-mono text-buy">{fmt(autoResult.tp_price)}</span>
                  <span className="text-xs text-text-muted ml-1">({autoResult.tp_pips} pips)</span>
                </div>
              </div>
              <div className="text-xs text-text-muted">
                ATR: {autoResult.atr_used.toFixed(5)} | R:R 1:{autoResult.risk_reward}
              </div>
            </div>
          )}

          {result && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2 mb-1">
                <Badge variant={result.direction === "BUY" ? "buy" : "sell"}>
                  {result.direction} {result.pair}
                </Badge>
                <Badge variant="default">R:R 1:{result.risk_reward}</Badge>
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm">
                {[
                  ["Entry", fmt(result.entry_price), ""],
                  ["SL", fmt(result.sl_price), `${result.sl_pips} pips`],
                  ["TP", fmt(result.tp_price), `${result.tp_pips} pips`],
                  ["Lot Size", String(result.lot_size), "lots"],
                  ["ความเสี่ยง", `$${result.risk_amount}`, ""],
                  ["กำไรเป้า", `$${result.potential_profit}`, ""],
                ].map(([label, value, sub]) => (
                  <div key={label} className="p-3 rounded-xl bg-bg-surface">
                    <span className="text-text-muted block text-xs">{label}</span>
                    <span className="font-mono font-semibold">{value}</span>
                    {sub && <span className="text-xs text-text-muted ml-1">{sub}</span>}
                  </div>
                ))}
              </div>

              {result.warnings.length > 0 && (
                <div className="flex flex-col gap-1.5 mt-2">
                  {result.warnings.map((w, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-warning">
                      <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                      {w}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </main>
  );
}
