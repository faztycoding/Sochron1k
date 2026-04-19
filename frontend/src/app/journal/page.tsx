"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, BookOpen, ChevronLeft, ChevronRight, Trash2 } from "lucide-react";

import { tradeApi } from "@/lib/api-trade";
import type { TradeItem } from "@/lib/api-trade";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PAIRS as ALL_PAIRS } from "@/lib/constants";

const PAIRS = ["ทั้งหมด", ...ALL_PAIRS];
const STATUSES = ["ทั้งหมด", "open", "closed"];

export default function JournalPage() {
  const [trades, setTrades] = useState<TradeItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filterPair, setFilterPair] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const loadTrades = useCallback(async () => {
    setLoading(true);
    try {
      const res = await tradeApi.trades.list(
        page,
        filterPair || undefined,
        filterStatus || undefined,
      );
      setTrades(res.items);
      setTotal(res.total);
    } catch {
      // silent
    }
    setLoading(false);
  }, [page, filterPair, filterStatus]);

  useEffect(() => {
    loadTrades();
  }, [loadTrades]);

  const handleDelete = async (id: number) => {
    if (!confirm("ลบเทรดนี้?")) return;
    try {
      await tradeApi.trades.delete(id);
      loadTrades();
    } catch {
      // silent
    }
  };

  const totalPages = Math.ceil(total / 20);
  const isJPY = (pair: string) => pair.includes("JPY");
  const fmt = (pair: string, v: number | null) =>
    v !== null ? v.toFixed(isJPY(pair) ? 3 : 5) : "—";

  return (
    <main className="min-h-screen p-4 sm:p-6 max-w-7xl mx-auto animate-fade-in">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/" className="p-2 rounded-lg hover:bg-bg-surface transition-colors">
          <ArrowLeft className="w-5 h-5 text-text-muted" />
        </Link>
        <BookOpen className="w-5 h-5 text-primary-400" />
        <h1 className="text-xl font-bold gradient-text">บันทึกการเทรด</h1>
        <span className="text-sm text-text-muted ml-auto">{total} รายการ</span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="flex gap-1 p-1 rounded-xl bg-bg-surface">
          {PAIRS.map((p) => (
            <button
              key={p}
              onClick={() => { setFilterPair(p === "ทั้งหมด" ? "" : p); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                (p === "ทั้งหมด" && !filterPair) || filterPair === p
                  ? "bg-primary-600 text-white"
                  : "text-text-secondary hover:bg-bg-elevated"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        <div className="flex gap-1 p-1 rounded-xl bg-bg-surface">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => { setFilterStatus(s === "ทั้งหมด" ? "" : s); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                (s === "ทั้งหมด" && !filterStatus) || filterStatus === s
                  ? "bg-accent-500 text-white"
                  : "text-text-secondary hover:bg-bg-elevated"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-text-muted text-xs">
                <th className="text-left p-3">คู่เงิน</th>
                <th className="text-left p-3">ทิศทาง</th>
                <th className="text-right p-3">Entry</th>
                <th className="text-right p-3">SL</th>
                <th className="text-right p-3">TP</th>
                <th className="text-right p-3">Exit</th>
                <th className="text-right p-3">Pips</th>
                <th className="text-center p-3">ผล</th>
                <th className="text-center p-3">ระบบ</th>
                <th className="text-right p-3">วันที่</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={11} className="text-center py-8 text-text-muted">กำลังโหลด...</td>
                </tr>
              )}
              {!loading && trades.length === 0 && (
                <tr>
                  <td colSpan={11} className="text-center py-8 text-text-muted">ยังไม่มีรายการเทรด</td>
                </tr>
              )}
              {trades.map((t) => (
                <tr key={t.id} className="border-b border-border/50 hover:bg-bg-surface/30 transition-colors">
                  <td className="p-3 font-medium">{t.pair}</td>
                  <td className="p-3">
                    <Badge variant={t.direction === "BUY" ? "buy" : "sell"} className="text-xs">
                      {t.direction}
                    </Badge>
                  </td>
                  <td className="p-3 text-right font-mono">{fmt(t.pair, t.entry_price)}</td>
                  <td className="p-3 text-right font-mono text-sell">{fmt(t.pair, t.sl_price)}</td>
                  <td className="p-3 text-right font-mono text-buy">{fmt(t.pair, t.tp_price)}</td>
                  <td className="p-3 text-right font-mono">{fmt(t.pair, t.exit_price)}</td>
                  <td className={`p-3 text-right font-mono font-semibold ${
                    t.actual_pips && t.actual_pips > 0 ? "text-buy" : t.actual_pips && t.actual_pips < 0 ? "text-sell" : ""
                  }`}>
                    {t.actual_pips !== null ? `${t.actual_pips > 0 ? "+" : ""}${t.actual_pips}` : "—"}
                  </td>
                  <td className="p-3 text-center">
                    {t.result === "win" ? (
                      <Badge variant="success">WIN</Badge>
                    ) : t.result === "loss" ? (
                      <Badge variant="danger">LOSS</Badge>
                    ) : (
                      <Badge variant="neutral">{t.status}</Badge>
                    )}
                  </td>
                  <td className="p-3 text-center">
                    {t.system_correct !== null ? (
                      <span className={t.system_correct ? "text-success" : "text-danger"}>
                        {t.system_correct ? "✓" : "✗"}
                      </span>
                    ) : (
                      <span className="text-text-muted">—</span>
                    )}
                  </td>
                  <td className="p-3 text-right text-text-muted text-xs whitespace-nowrap">
                    {new Date(t.opened_at).toLocaleDateString("th-TH", { month: "short", day: "numeric" })}
                  </td>
                  <td className="p-3">
                    <button onClick={() => handleDelete(t.id)} className="p-1 rounded hover:bg-danger/10 transition-colors">
                      <Trash2 className="w-3.5 h-3.5 text-text-muted hover:text-danger" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 p-3 border-t border-border">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded-lg hover:bg-bg-surface disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm text-text-secondary">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages}
              className="p-1.5 rounded-lg hover:bg-bg-surface disabled:opacity-30"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </Card>
    </main>
  );
}
