"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, Clock3, FileText, RefreshCw } from "lucide-react";
import { getHistory } from "@/lib/api/client";
import type { ComparisonHistoryItem } from "@/lib/types/api";
import { formatDate } from "@/lib/utils";

export function HistoryList({ compact = false, query = "" }: { compact?: boolean; query?: string }) {
  const [items, setItems] = useState<ComparisonHistoryItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await getHistory(compact ? 4 : 100);
      setItems(response.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "History could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [compact]);

  useEffect(() => { void load(); }, [load]);

  const visibleItems = items.filter((item) =>
    `${item.old_document.filename} ${item.new_document.filename}`.toLowerCase().includes(query),
  );

  if (loading) return <div className="space-y-2" aria-label="Loading comparison history"><div className="shimmer h-[68px] rounded-xl" /><div className="shimmer h-[68px] rounded-xl" /></div>;

  if (error) return <div className="rounded-xl border border-subtle bg-[var(--surface-muted)] p-4"><p className="text-xs leading-5 text-muted">{error}</p><button onClick={() => void load()} className="focus-ring mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--accent-strong)]"><RefreshCw size={13} /> Retry</button></div>;

  if (items.length === 0) return <div className="rounded-xl border border-dashed border-[var(--line-strong)] bg-[var(--surface-muted)] px-5 py-8 text-center"><span className="mx-auto mb-2 flex h-9 w-9 items-center justify-center rounded-full bg-[var(--surface)] text-muted"><Clock3 size={16} /></span><p className="text-sm font-medium">No comparisons yet</p><p className="mt-1 text-xs text-muted">Your completed document analyses will appear here.</p></div>;
  if (visibleItems.length === 0) return <div className="py-10 text-center text-xs text-muted">No comparisons match “{query}”.</div>;

  return (
    <div className="divide-y divide-[var(--line)]">
      {visibleItems.map((item) => <Link key={item.comparison_id} href={`/compare/${encodeURIComponent(item.comparison_id)}`} className="focus-ring group flex items-center gap-3 rounded-lg py-3.5">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-subtle bg-[var(--surface-muted)] text-muted"><FileText size={16} /></span>
        <span className="min-w-0 flex-1"><span className="block truncate text-xs font-semibold">{item.old_document.filename} <span className="font-normal text-muted">to</span> {item.new_document.filename}</span><span className="mt-1 block text-[10px] text-muted">{formatDate(item.created_at)}</span></span>
        <span className="hidden whitespace-nowrap text-right sm:block"><span className="block text-xs font-semibold">{item.summary.total_changes} changes</span><span className="mt-1 block text-[10px] text-muted">{item.summary.additions} added · {item.summary.deletions} removed</span></span>
        <ArrowRight size={15} className="text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--accent-strong)]" />
      </Link>)}
    </div>
  );
}
