"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Zap, ShieldAlert, Shield } from "lucide-react";
import type { AnalysisResult } from "@/lib/api";

interface SignalPanelProps {
  analyses: Record<string, AnalysisResult | null>;
}

export function SignalPanel({ analyses }: SignalPanelProps) {
  const pairs = Object.entries(analyses);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-accent-400" />
          <CardTitle>สัญญาณเทรด</CardTitle>
        </div>
      </CardHeader>

      <div className="flex flex-col gap-3">
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

          return (
            <div key={pair} className="p-3 rounded-xl bg-bg-surface/50">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-sm">{pair}</span>
                <div className="flex items-center gap-2">
                  {isKilled ? (
                    <Badge variant="danger">
                      <ShieldAlert className="w-3 h-3 mr-1" />
                      KILL SWITCH
                    </Badge>
                  ) : (
                    <Badge variant={dir === "BUY" ? "buy" : dir === "SELL" ? "sell" : "neutral"}>
                      {dir}
                    </Badge>
                  )}
                </div>
              </div>

              {!isKilled && (
                <>
                  <div className="flex items-center gap-2 text-xs text-text-muted mb-1">
                    <span>{result.strength}</span>
                    <span>•</span>
                    <span>{(conf * 100).toFixed(0)}%</span>
                    <span>•</span>
                    <span className="capitalize">{result.regime.regime}</span>
                  </div>

                  {result.suggested_sl && result.suggested_tp && (
                    <div className="flex gap-4 mt-2 text-xs font-mono">
                      <span className="text-sell">SL: {result.suggested_sl.toFixed(pair.includes("JPY") ? 3 : 5)}</span>
                      <span className="text-buy">TP: {result.suggested_tp.toFixed(pair.includes("JPY") ? 3 : 5)}</span>
                      {result.risk_reward && (
                        <span className="text-text-secondary">R:R 1:{result.risk_reward.toFixed(1)}</span>
                      )}
                    </div>
                  )}
                </>
              )}

              {isKilled && result.kill_switch.triggers.length > 0 && (
                <p className="text-xs text-danger mt-1">
                  {result.kill_switch.triggers[0].message}
                </p>
              )}

              {/* Health badge */}
              <div className="flex items-center gap-1 mt-2">
                <Shield className="w-3 h-3 text-text-muted" />
                <span
                  className={`text-xs ${
                    result.diagnosis.overall_health === "HEALTHY"
                      ? "text-success"
                      : result.diagnosis.overall_health === "WARNING"
                        ? "text-warning"
                        : "text-danger"
                  }`}
                >
                  {result.diagnosis.overall_health} ({result.diagnosis.issues} issues)
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
