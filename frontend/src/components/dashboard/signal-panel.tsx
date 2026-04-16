"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogHeader, DialogBody } from "@/components/ui/dialog";
import {
  Zap,
  ShieldAlert,
  TrendingUp,
  TrendingDown,
  Minus,
  Target,
  BarChart3,
  Newspaper,
  AlertTriangle,
  ChevronRight,
  Activity,
} from "lucide-react";
import type { AnalysisResult, NewsItem } from "@/lib/api";

interface SignalPanelProps {
  analyses: Record<string, AnalysisResult | null>;
  news?: NewsItem[];
}

const dirIcon = (dir: string) => {
  if (dir === "BUY") return <TrendingUp className="w-3.5 h-3.5" />;
  if (dir === "SELL") return <TrendingDown className="w-3.5 h-3.5" />;
  return <Minus className="w-3.5 h-3.5" />;
};

const confColor = (conf: number) => {
  if (conf >= 0.7) return "text-success";
  if (conf >= 0.4) return "text-warning";
  return "text-danger";
};

const confBar = (conf: number) => {
  const pct = Math.round(conf * 100);
  return (
    <div className="flex items-center gap-2 flex-1">
      <div className="flex-1 h-1.5 rounded-full bg-bg-surface overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            conf >= 0.7
              ? "bg-gradient-to-r from-emerald-600 to-emerald-400"
              : conf >= 0.4
                ? "bg-gradient-to-r from-amber-600 to-amber-400"
                : "bg-gradient-to-r from-red-600 to-red-400"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-[11px] font-mono ${confColor(conf)}`}>{pct}%</span>
    </div>
  );
};

export function SignalPanel({ analyses, news = [] }: SignalPanelProps) {
  const [selectedPair, setSelectedPair] = useState<string | null>(null);
  const pairs = Object.entries(analyses);
  const selectedResult = selectedPair ? analyses[selectedPair] : null;
  const pairNews = news.filter(
    (n) => !selectedPair || n.pair === selectedPair || n.currency?.includes(selectedPair.split("/")[0]) || n.currency?.includes(selectedPair.split("/")[1])
  );

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-accent-400" />
            <CardTitle>สัญญาณเทรด</CardTitle>
          </div>
        </CardHeader>
        <p className="text-[11px] text-text-muted -mt-1 mb-2">
          วิเคราะห์ 5 ชั้น: Regime → ข่าว → เทคนิคอล → Correlation → Risk Gate
          <span className="text-text-muted/60 ml-1">• กดเพื่อดูรายละเอียด</span>
        </p>

        <div className="flex flex-col gap-2.5">
          {pairs.map(([pair, result]) => {
            if (!result) {
              return (
                <div key={pair} className="flex items-center justify-between p-3 rounded-xl bg-bg-surface/50">
                  <span className="font-medium text-sm">{pair}</span>
                  <Badge variant="neutral">รอวิเคราะห์</Badge>
                </div>
              );
            }

            const isKilled = result.kill_switch.kill_switch_active;
            const conf = result.confidence;
            const dir = result.direction;
            const isJPY = pair.includes("JPY");
            const decimals = isJPY ? 3 : 5;

            return (
              <button
                key={pair}
                onClick={() => setSelectedPair(pair)}
                className="w-full text-left p-3 rounded-xl bg-bg-surface/50 hover:bg-bg-surface/80 border border-transparent hover:border-primary-700/30 transition-all cursor-pointer group"
              >
                {/* Row 1: Pair + Direction + Kill Switch */}
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">{pair}</span>
                    <Badge variant={dir === "BUY" ? "buy" : dir === "SELL" ? "sell" : "neutral"} className="text-[10px] px-2 py-0">
                      {dirIcon(dir)}
                      <span className="ml-1">{dir}</span>
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {isKilled && (
                      <Badge variant="danger" className="text-[10px] px-1.5 py-0">
                        <ShieldAlert className="w-3 h-3 mr-0.5" />
                        KILL
                      </Badge>
                    )}
                    <ChevronRight className="w-3.5 h-3.5 text-text-muted group-hover:text-primary-400 transition-colors" />
                  </div>
                </div>

                {/* Row 2: Confidence bar + Regime */}
                <div className="flex items-center gap-2 mb-1.5">
                  {confBar(conf)}
                  <Badge variant="neutral" className="text-[10px] px-1.5 py-0 capitalize">
                    {result.regime.regime}
                  </Badge>
                </div>

                {/* Row 3: Entry / SL / TP */}
                {result.suggested_sl && result.suggested_tp ? (
                  <div className="flex items-center gap-3 text-[11px] font-mono">
                    <span className="text-text-muted">
                      <Target className="w-3 h-3 inline mr-0.5 -mt-px" />
                      {result.price?.toFixed(decimals)}
                    </span>
                    <span className="text-sell">SL {result.suggested_sl.toFixed(decimals)}</span>
                    <span className="text-buy">TP {result.suggested_tp.toFixed(decimals)}</span>
                    {result.risk_reward && (
                      <span className="text-text-secondary ml-auto">R:R 1:{result.risk_reward.toFixed(1)}</span>
                    )}
                  </div>
                ) : (
                  <div className="text-[11px] text-text-muted">ยังไม่มี SL/TP — รอข้อมูลเพิ่ม</div>
                )}

                {/* Row 4: Kill switch reason (short) */}
                {isKilled && result.kill_switch.triggers.length > 0 && (
                  <div className="flex items-center gap-1 mt-1.5 text-[11px] text-danger/80">
                    <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                    <span className="truncate">{result.kill_switch.triggers[0].message}</span>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </Card>

      {/* Detail Popup */}
      <Dialog open={!!selectedPair} onClose={() => setSelectedPair(null)} className="max-w-md">
        {selectedResult && selectedPair && (
          <>
            <DialogHeader>
              <div className="flex items-center gap-2 mb-1">
                <Zap className="w-5 h-5 text-accent-400" />
                <h2 className="text-lg font-bold">{selectedPair}</h2>
                <Badge variant={selectedResult.direction === "BUY" ? "buy" : selectedResult.direction === "SELL" ? "sell" : "neutral"}>
                  {dirIcon(selectedResult.direction)}
                  <span className="ml-1">{selectedResult.direction}</span>
                </Badge>
              </div>
              <p className="text-xs text-text-muted">
                วิเคราะห์เมื่อ {new Date(selectedResult.analyzed_at).toLocaleTimeString("th-TH")}
                {" "}• ใช้เวลา {selectedResult.analysis_duration?.toFixed(1)}s
              </p>
            </DialogHeader>

            <DialogBody>
              {/* Kill Switch Warning */}
              {selectedResult.kill_switch.kill_switch_active && (
                <div className="mb-4 p-3 rounded-xl bg-danger/10 border border-danger/20">
                  <div className="flex items-center gap-2 mb-1">
                    <ShieldAlert className="w-4 h-4 text-danger" />
                    <span className="text-sm font-semibold text-danger">Kill Switch — ห้ามเทรด</span>
                  </div>
                  {selectedResult.kill_switch.triggers.map((t, i) => (
                    <p key={i} className="text-xs text-danger/80 mt-1">• {t.message}</p>
                  ))}
                </div>
              )}

              {/* Confidence */}
              <div className="mb-4">
                <div className="text-xs text-text-muted mb-1.5 font-medium">ความมั่นใจ</div>
                <div className="flex items-center gap-3">
                  {confBar(selectedResult.confidence)}
                  <span className="text-xs text-text-muted">({selectedResult.strength})</span>
                </div>
              </div>

              {/* 5-Layer Analysis */}
              <div className="mb-4">
                <div className="text-xs text-text-muted mb-2 font-medium flex items-center gap-1">
                  <BarChart3 className="w-3.5 h-3.5" />
                  การวิเคราะห์ 5 ชั้น
                </div>
                <div className="space-y-2">
                  {[
                    { name: "Regime", score: selectedResult.regime.regime_score, label: selectedResult.regime.regime, details: selectedResult.regime.details },
                    { name: "ข่าว", score: selectedResult.news.news_score, label: selectedResult.news.sentiment, details: selectedResult.news.details },
                    { name: "เทคนิคอล", score: selectedResult.technical.technical_score, label: `${selectedResult.technical.agreements}/${selectedResult.technical.total_checks}`, details: selectedResult.technical.signals },
                    { name: "Correlation", score: selectedResult.correlation.correlation_score, label: "", details: [] },
                    { name: "Risk Gate", score: selectedResult.risk_gate.risk_gate_score, label: "", details: selectedResult.risk_gate.details },
                  ].map((layer) => (
                    <div key={layer.name} className="p-2.5 rounded-lg bg-bg-surface/70">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium">{layer.name}</span>
                        <div className="flex items-center gap-2">
                          {layer.label && <span className="text-[10px] text-text-muted capitalize">{layer.label}</span>}
                          <span className={`text-xs font-mono ${layer.score > 0.5 ? "text-buy" : layer.score < -0.5 ? "text-sell" : "text-text-muted"}`}>
                            {layer.score > 0 ? "+" : ""}{layer.score.toFixed(2)}
                          </span>
                        </div>
                      </div>
                      {layer.details && layer.details.length > 0 && (
                        <div className="mt-1 space-y-0.5">
                          {layer.details.slice(0, 3).map((d, i) => (
                            <p key={i} className="text-[10px] text-text-muted leading-tight">• {d}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Entry / SL / TP */}
              {selectedResult.suggested_sl && selectedResult.suggested_tp && (
                <div className="mb-4 p-3 rounded-xl bg-bg-surface/70">
                  <div className="text-xs text-text-muted mb-2 font-medium flex items-center gap-1">
                    <Target className="w-3.5 h-3.5" />
                    ระดับราคา
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div>
                      <div className="text-[10px] text-text-muted">Entry</div>
                      <div className="text-sm font-mono font-semibold">
                        {selectedResult.price?.toFixed(selectedPair.includes("JPY") ? 3 : 5)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-sell">SL ({selectedResult.sl_pips?.toFixed(0)}p)</div>
                      <div className="text-sm font-mono font-semibold text-sell">
                        {selectedResult.suggested_sl.toFixed(selectedPair.includes("JPY") ? 3 : 5)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-buy">TP ({selectedResult.tp_pips?.toFixed(0)}p)</div>
                      <div className="text-sm font-mono font-semibold text-buy">
                        {selectedResult.suggested_tp.toFixed(selectedPair.includes("JPY") ? 3 : 5)}
                      </div>
                    </div>
                  </div>
                  {selectedResult.risk_reward && (
                    <div className="text-center mt-2 text-xs text-text-secondary">
                      Risk:Reward = 1:{selectedResult.risk_reward.toFixed(1)}
                    </div>
                  )}
                </div>
              )}

              {/* Diagnosis */}
              <div className="mb-4">
                <div className="text-xs text-text-muted mb-2 font-medium flex items-center gap-1">
                  <Activity className="w-3.5 h-3.5" />
                  สุขภาพระบบ: {selectedResult.diagnosis.overall_health}
                  <span className="text-text-muted/60">({selectedResult.diagnosis.issues}/{selectedResult.diagnosis.total_checks})</span>
                </div>
                {selectedResult.diagnosis.diagnostics
                  .filter((d) => d.severity !== "ok")
                  .slice(0, 5)
                  .map((d, i) => (
                    <div key={i} className="flex items-start gap-1.5 mb-1">
                      <span className={`text-[10px] mt-0.5 ${d.severity === "error" ? "text-danger" : d.severity === "warning" ? "text-warning" : "text-text-muted"}`}>●</span>
                      <span className="text-[11px] text-text-muted">{d.message}</span>
                    </div>
                  ))}
              </div>

              {/* Related News */}
              <div>
                <div className="text-xs text-text-muted mb-2 font-medium flex items-center gap-1">
                  <Newspaper className="w-3.5 h-3.5" />
                  ข่าวที่เกี่ยวข้อง
                </div>
                {pairNews.length === 0 ? (
                  <p className="text-[11px] text-text-muted">ยังไม่มีข่าว — กด ↻ ที่การ์ดข่าวเพื่อดึงข่าวล่าสุด</p>
                ) : (
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {pairNews.slice(0, 5).map((n, i) => (
                      <div key={i} className="p-2 rounded-lg bg-bg-surface/70">
                        <p className="text-xs font-medium leading-snug line-clamp-2">
                          {n.title_th || n.title_original}
                        </p>
                        {n.summary_th && (
                          <p className="text-[10px] text-text-muted mt-1 line-clamp-2">{n.summary_th}</p>
                        )}
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant={n.impact_level === "high" ? "danger" : n.impact_level === "medium" ? "warning" : "neutral"} className="text-[9px] px-1.5 py-0">
                            {n.impact_level}
                          </Badge>
                          <span className="text-[10px] text-text-muted">{n.source}</span>
                          {n.sentiment_score !== undefined && n.sentiment_score !== null && (
                            <span className={`text-[10px] ${n.sentiment_score > 0 ? "text-buy" : n.sentiment_score < 0 ? "text-sell" : "text-text-muted"}`}>
                              {n.sentiment_score > 0 ? "+" : ""}{n.sentiment_score.toFixed(2)}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </DialogBody>
          </>
        )}
      </Dialog>
    </>
  );
}
