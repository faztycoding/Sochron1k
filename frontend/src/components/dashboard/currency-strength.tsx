"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart3 } from "lucide-react";
import type { CurrencyStrength } from "@/lib/api";

interface CurrencyStrengthBarProps {
  data: CurrencyStrength | null;
}

export function CurrencyStrengthBar({ data }: CurrencyStrengthBarProps) {
  if (!data?.currencies) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-primary-400" />
            <CardTitle>ความแข็งแกร่งสกุลเงิน</CardTitle>
          </div>
        </CardHeader>
        <p className="text-sm text-text-muted text-center py-4">รอข้อมูล</p>
      </Card>
    );
  }

  const currencies = Object.entries(data.currencies).sort((a, b) => b[1] - a[1]);
  const maxAbs = Math.max(...currencies.map(([, v]) => Math.abs(v)), 1);

  const flagEmoji: Record<string, string> = { EUR: "🇪🇺", USD: "🇺🇸", JPY: "🇯🇵", GBP: "🇬🇧", AUD: "🇦🇺" };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary-400" />
          <CardTitle>ความแข็งแกร่งสกุลเงิน</CardTitle>
        </div>
      </CardHeader>
      <p className="text-[11px] text-text-muted -mt-1 mb-2">
        เปรียบเทียบแรงซื้อ-ขายใน 24 ชม. ยิ่งบวกมาก = สกุลเงินแข็งแกร่ง
      </p>

      <div className="flex flex-col gap-3">
        {currencies.map(([currency, value]) => {
          const width = Math.abs(value) / maxAbs * 100;
          const isPositive = value >= 0;

          return (
            <div key={currency}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium flex items-center gap-1.5">
                  <span>{flagEmoji[currency] || ""}</span>
                  {currency}
                  {currency === data.strongest && (
                    <span className="text-xs text-buy">💪</span>
                  )}
                </span>
                <span
                  className={`text-sm font-mono ${isPositive ? "text-buy" : "text-sell"}`}
                >
                  {isPositive ? "+" : ""}
                  {value.toFixed(1)}
                </span>
              </div>
              <div className="h-2 rounded-full bg-bg-surface overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${Math.max(width, 4)}%`,
                    background: isPositive
                      ? "linear-gradient(90deg, var(--color-primary-600), var(--color-buy))"
                      : "linear-gradient(90deg, var(--color-sell), var(--color-danger-dim))",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
