"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { HistoryList } from "@/components/history/history-list";

export default function HistoryPage() {
  const [query, setQuery] = useState("");
  const normalized = useMemo(() => query.trim().toLowerCase(), [query]);
  return <div className="mx-auto max-w-[1050px] px-4 py-8 sm:px-7 sm:py-11"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-[10px] font-semibold uppercase tracking-[.16em] text-[var(--accent-strong)]">Workspace</p><h1 className="mt-2 text-3xl font-semibold tracking-[-.045em]">Comparison history</h1><p className="mt-2 text-sm text-muted">Revisit completed analyses and their change summaries.</p></div><label className="flex h-10 w-full items-center gap-2 rounded-lg border border-subtle bg-[var(--surface)] px-3 sm:max-w-[300px]"><Search size={15} className="text-muted" /><input className="w-full bg-transparent text-xs outline-none placeholder:text-muted" placeholder="Search files…" value={query} onChange={(event) => setQuery(event.target.value)} aria-label="Search history" /></label></div><div className="surface mt-6 rounded-2xl px-5 sm:px-7"><HistoryList query={normalized} /></div></div>;
}
