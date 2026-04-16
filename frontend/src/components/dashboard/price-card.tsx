"use client";

import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardValue } from "@/components/ui/card";
import type { PriceData, AnalysisResult } from "@/lib/api";

interface PriceCardProps {
  pair: string;
  price?: PriceData | null;
  analysis?: AnalysisResult | null;
}

export function PriceCard({ pair, price, analysis }: PriceCardProps) {
  const direction = analysis?.direction;
  const confidence = analysis?.confidence ?? 0;
  const regime = analysis?.regime?.regime ?? "—";

  const changePercent =
    price?.previous_close && price.price
      ? ((price.price - price.previous_close) / price.previous_close) * 100
      : null;

  const isUp = changePercent !== null && changePercent > 0;
  const isDown = changePercent !== null && changePercent < 0;

  return (
    <Card className="hover:border-primary-500/50 group">
      <CardHeader>
        <CardTitle>{pair}</CardTitle>
        {direction && direction !== "NO_TRADE" ? (
          <Badge variant={direction === "BUY" ? "buy" : "sell"}>
            {direction === "BUY" ? (
              <ArrowUp className="w-3 h-3 mr-1" />
            ) : (
              <ArrowDown className="w-3 h-3 mr-1" />
            )}
            {direction}
          </Badge>
        ) : (
          <Badge variant="neutral">
            <Minus className="w-3 h-3 mr-1" />
            {direction === "NO_TRADE" ? "STOP" : "รอข้อมูล"}
          </Badge>
        )}
      </CardHeader>

      <CardValue className={isUp ? "text-buy" : isDown ? "text-sell" : "text-accent-400"}>
        {price?.price ? price.price.toFixed(pair.includes("JPY") ? 3 : 5) : "—"}
      </CardValue>

      <div className="flex items-center gap-3 mt-3 text-sm">
        {changePercent !== null && (
          <span className={isUp ? "text-buy" : isDown ? "text-sell" : "text-text-muted"}>
            {isUp ? "+" : ""}
            {changePercent.toFixed(3)}%
          </span>
        )}
        <span className="text-text-muted">|</span>
        <span className="text-text-secondary capitalize">{regime}</span>
      </div>

      {confidence > 0 && (
        <div className="mt-3">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-text-muted">ความมั่นใจ</span>
            <span className="text-text-secondary">{(confidence * 100).toFixed(0)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-bg-surface overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${confidence * 100}%`,
                background:
                  confidence >= 0.75
                    ? "var(--color-buy)"
                    : confidence >= 0.5
                      ? "var(--color-warning)"
                      : "var(--color-sell)",
              }}
            />
          </div>
        </div>
      )}
    </Card>
  );
}
