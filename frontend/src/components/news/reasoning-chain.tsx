"use client";

import { useState } from "react";
import { Brain, ChevronDown } from "lucide-react";
import type { ReasoningChain as ReasoningChainType } from "@/lib/api";
import { cn } from "@/lib/utils";

const STEP_META: { key: keyof ReasoningChainType; label: string; emoji: string }[] = [
  { key: "step1_classification", label: "Event Classification", emoji: "🏷️" },
  { key: "step2_historical_precedent", label: "Historical Precedent", emoji: "📚" },
  { key: "step3_market_bias", label: "Current Market Bias", emoji: "🧭" },
  { key: "step4_volatility_forecast", label: "Volatility Forecast", emoji: "📊" },
  { key: "step5_trade_setup_logic", label: "Trade Setup Logic", emoji: "🎯" },
  { key: "step6_self_eval", label: "Self-Evaluation", emoji: "✓" },
];

interface ReasoningChainProps {
  reasoning?: ReasoningChainType;
  confidence?: number;
}

export function ReasoningChain({ reasoning, confidence }: ReasoningChainProps) {
  const [open, setOpen] = useState(false);

  if (!reasoning) return null;

  // Check if any step has content
  const hasContent = STEP_META.some((s) => reasoning[s.key]);
  if (!hasContent) return null;

  const confPct = Math.round((confidence ?? 0) * 100);
  const confColor =
    confPct >= 75 ? "text-buy" : confPct >= 50 ? "text-amber-400" : "text-text-muted";

  return (
    <div className="mb-4 rounded-xl border border-border bg-bg-surface/30">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-bg-elevated/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-accent-400" />
          <span className="text-sm font-medium text-text-primary">AI Reasoning Chain</span>
          <span className="text-[10px] text-text-muted">6 steps</span>
        </div>
        <div className="flex items-center gap-2">
          {confidence !== undefined && (
            <span className={cn("text-xs font-mono", confColor)}>
              confidence: {confPct}%
            </span>
          )}
          <ChevronDown className={cn("w-4 h-4 text-text-muted transition-transform", open && "rotate-180")} />
        </div>
      </button>

      {open && (
        <div className="border-t border-border p-3 space-y-3">
          {STEP_META.map((step, idx) => {
            const content = reasoning[step.key];
            if (!content) return null;
            return (
              <div key={step.key} className="flex gap-3">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-accent-500/15 border border-accent-500/30 flex items-center justify-center text-[10px] font-bold text-accent-300">
                  {idx + 1}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-sm">{step.emoji}</span>
                    <span className="text-[11px] font-semibold text-accent-300 uppercase tracking-wide">
                      {step.label}
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary leading-relaxed">{content}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
