"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowDown, ArrowLeft, ArrowRight, CalendarDays, Check, ChevronDown,
  CircleAlert, FileText, Filter, Hash, Search,
} from "lucide-react";
import { getChanges, getComparison, getSummary } from "@/lib/api/client";
import type { ChangeRecord, ChangeType, ComparisonResult, ComparisonSummary } from "@/lib/types/api";
import { changeTone, formatDate, titleForChange } from "@/lib/utils";
import { Label } from "@/components/ui/primitives";

const filters: Array<{ type: ChangeType | "ALL"; label: string }> = [
  { type: "ALL", label: "All changes" },
  { type: "ADDITION", label: "Added" },
  { type: "DELETION", label: "Removed" },
  { type: "MODIFICATION", label: "Modified" },
  { type: "NUMERICAL_CHANGE", label: "Numerical" },
  { type: "TEMPORAL_CHANGE", label: "Temporal" },
  { type: "ENTITY_CHANGE", label: "Entity" },
  { type: "CONTRADICTION", label: "Contradictions" },
  { type: "REFINEMENT", label: "Refinements" },
];

function Skeleton() {
  return <div className="mx-auto max-w-[1500px] space-y-5 px-4 py-8 sm:px-7"><div className="shimmer h-8 w-64 rounded-lg" /><div className="grid grid-cols-2 gap-3 sm:grid-cols-4"><div className="shimmer h-24 rounded-xl" /><div className="shimmer h-24 rounded-xl" /><div className="shimmer h-24 rounded-xl" /><div className="shimmer h-24 rounded-xl" /></div><div className="grid gap-4 xl:grid-cols-[1fr_330px]"><div className="shimmer h-[560px] rounded-2xl" /><div className="shimmer h-[560px] rounded-2xl" /></div></div>;
}

export function ComparisonWorkspace() {
  const params = useParams<{ comparisonId: string }>();
  const id = params.comparisonId;
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [summary, setSummary] = useState<ComparisonSummary | null>(null);
  const [changes, setChanges] = useState<ChangeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<ChangeType | "ALL">("ALL");
  const [section, setSection] = useState("ALL");
  const [search, setSearch] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [comparison, changeList, comparisonSummary] = await Promise.all([
        getComparison(id), getChanges(id, true), getSummary(id),
      ]);
      setResult(comparison);
      setChanges(changeList);
      setSummary(comparisonSummary);
      setSelectedId(changeList.find((item) => item.type !== "UNCHANGED")?.id ?? changeList[0]?.id ?? null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "This comparison could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
      if (event.key === "Escape") searchRef.current?.blur();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const meaningful = useMemo(() => changes.filter((change) => change.type !== "UNCHANGED"), [changes]);
  const sections = useMemo(() => Array.from(new Set(meaningful.map((change) => change.new_section ?? change.old_section).filter((item): item is string => Boolean(item)))), [meaningful]);
  const visible = useMemo(() => {
    const normalized = search.trim().toLowerCase();
    return meaningful.filter((change) => {
      const matchesType = filter === "ALL" || change.type === filter;
      const matchesSection = section === "ALL" || (change.new_section ?? change.old_section) === section;
      const matchesSearch = !normalized || [change.old_text, change.new_text, change.old_section, change.new_section, change.explanation].some((text) => text?.toLowerCase().includes(normalized));
      return matchesType && matchesSection && matchesSearch;
    });
  }, [filter, meaningful, search, section]);
  const selected = changes.find((change) => change.id === selectedId) ?? null;

  function selectChange(change: ChangeRecord) {
    setSelectedId(change.id);
    document.getElementById(`change-${change.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  if (loading) return <Skeleton />;
  if (error || !result || !summary) return <div className="mx-auto max-w-[720px] px-4 py-16 text-center"><span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#f8eded] text-[#a45252]"><CircleAlert size={20} /></span><h1 className="mt-4 text-xl font-semibold">Comparison unavailable</h1><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">{error || "The comparison response was incomplete."}</p><div className="mt-5 flex justify-center gap-2"><button onClick={() => void load()} className="button-primary focus-ring rounded-lg px-4 py-2 text-xs font-semibold">Retry</button><Link href="/history" className="button-secondary focus-ring rounded-lg px-4 py-2 text-xs font-semibold">History</Link></div></div>;

  const summaryCards: Array<{ label: string; value: number; color: string }> = [
    { label: "Meaningful changes", value: summary.total_changes, color: "text-[var(--ink)]" },
    { label: "Modifications", value: summary.modifications, color: "text-[#9b7733]" },
    { label: "Numeric & dates", value: summary.numerical_changes + summary.temporal_changes, color: "text-[#426b9b]" },
    { label: "Added / removed", value: summary.additions + summary.deletions, color: "text-[#43805b]" },
  ];

  return (
    <div className="mx-auto max-w-[1600px] px-3 py-5 sm:px-6 sm:py-7 xl:px-8">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3"><Link href="/history" className="focus-ring inline-flex items-center gap-1.5 rounded text-xs text-muted hover:text-[var(--ink)]"><ArrowLeft size={14} /> History</Link><span className="inline-flex items-center gap-1.5 text-[10px] text-muted"><CalendarDays size={13} />{formatDate(result.created_at)}</span></div>
      <div className="mb-5 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div className="min-w-0"><Label>Semantic comparison</Label><h1 className="mt-2 truncate text-2xl font-semibold tracking-[-.04em] sm:text-3xl">{result.old_document.filename} <span className="font-normal text-muted">→</span> {result.new_document.filename}</h1><div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted"><span>Original · {result.old_document.pages} {result.old_document.pages === 1 ? "page" : "pages"}</span><span>Updated · {result.new_document.pages} {result.new_document.pages === 1 ? "page" : "pages"}</span><span className="rounded-full bg-[var(--accent-soft)] px-2 py-0.5 font-medium text-[var(--accent-strong)]">{result.status.toLowerCase()}</span></div></div>
      </div>

      <section className="mb-5 grid grid-cols-2 gap-2.5 sm:grid-cols-4" aria-label="Comparison summary">
        {summaryCards.map((card) => <div key={card.label} className="surface-flat rounded-xl px-3.5 py-3 sm:px-4"><p className={`text-2xl font-semibold tracking-[-.04em] ${card.color}`}>{card.value}</p><p className="mt-1 text-[10px] leading-4 text-muted sm:text-[11px]">{card.label}</p></div>)}
      </section>

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_340px] 2xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="surface min-w-0 overflow-hidden rounded-2xl" aria-label="Document comparison">
          <div className="sticky top-[62px] z-10 grid grid-cols-2 border-b border-subtle bg-[var(--surface)]">
            <div className="border-r border-subtle px-3 py-3 sm:px-5"><p className="text-[9px] font-semibold uppercase tracking-[.16em] text-muted">Original</p><p className="mt-1 truncate text-xs font-semibold">{result.old_document.filename}</p></div>
            <div className="px-3 py-3 sm:px-5"><p className="text-[9px] font-semibold uppercase tracking-[.16em] text-muted">Updated</p><p className="mt-1 truncate text-xs font-semibold">{result.new_document.filename}</p></div>
          </div>
          <div className="max-h-[calc(100vh-245px)] min-h-[240px] overflow-y-auto" aria-label="Aligned sentences">
            {changes.map((change) => <DocumentRow key={change.id} change={change} selected={change.id === selectedId} onSelect={() => setSelectedId(change.id)} />)}
            {changes.length === 0 && <p className="p-8 text-center text-sm text-muted">No sentence-level results were returned.</p>}
          </div>
          <div className="flex items-center justify-between border-t border-subtle bg-[var(--surface-muted)] px-4 py-2.5 text-[10px] text-muted"><span>{changes.length - meaningful.length} unchanged sentences hidden from the change explorer</span><span className="hidden items-center gap-1 sm:flex"><Hash size={11} /> Select a change to inspect it</span></div>
        </section>

        <aside className="space-y-4">
          <section className="surface overflow-hidden rounded-2xl">
            <div className="border-b border-subtle px-4 py-3.5"><div className="flex items-center justify-between"><div><h2 className="text-sm font-semibold">Change explorer</h2><p className="mt-1 text-[11px] text-muted">{visible.length} of {meaningful.length} meaningful changes</p></div><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-strong)]"><Filter size={15} /></span></div>
              <label className="mt-3 flex h-9 items-center gap-2 rounded-lg border border-subtle bg-[var(--surface-muted)] px-2.5"><Search size={14} className="shrink-0 text-muted" /><input ref={searchRef} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search text, section, explanation…" className="min-w-0 flex-1 bg-transparent text-[11px] outline-none placeholder:text-muted" aria-label="Search changes" /><kbd className="hidden rounded border border-subtle px-1 py-0.5 text-[9px] text-muted sm:block">⌘ K</kbd></label>
              <div className="mt-2 grid grid-cols-2 gap-2"><label className="relative"><span className="sr-only">Filter by type</span><select value={filter} onChange={(event) => setFilter(event.target.value as ChangeType | "ALL")} className="h-8 w-full appearance-none rounded-lg border border-subtle bg-[var(--surface)] px-2.5 pr-7 text-[10px] outline-none focus:border-[var(--accent)]">{filters.map((item) => <option key={item.type} value={item.type}>{item.label}</option>)}</select><ChevronDown size={13} className="pointer-events-none absolute right-2 top-2.5 text-muted" /></label><label className="relative"><span className="sr-only">Filter by section</span><select value={section} onChange={(event) => setSection(event.target.value)} className="h-8 w-full appearance-none rounded-lg border border-subtle bg-[var(--surface)] px-2.5 pr-7 text-[10px] outline-none focus:border-[var(--accent)]"><option value="ALL">All sections</option>{sections.map((item) => <option key={item} value={item}>{item}</option>)}</select><ChevronDown size={13} className="pointer-events-none absolute right-2 top-2.5 text-muted" /></label></div>
            </div>
            <div className="max-h-[330px] overflow-y-auto px-2.5 py-2" aria-label="Filtered changes">
              {visible.length === 0 ? <p className="px-3 py-8 text-center text-xs text-muted">No changes match these filters.</p> : visible.map((change, index) => <button key={change.id} onClick={() => selectChange(change)} className={`focus-ring mb-1 w-full rounded-xl border p-3 text-left transition-colors ${selectedId === change.id ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "border-transparent hover:border-subtle hover:bg-[var(--surface-muted)]"}`}>
                <span className="flex items-center justify-between gap-2"><span className={`change-badge rounded-full px-2 py-1 text-[9px] font-semibold ${changeTone(change.type)}`}>{titleForChange(change.type)}</span><span className="text-[9px] tabular-nums text-muted">{Math.round(change.confidence * 100)}% conf.</span></span>
                <span className="mt-2 block line-clamp-2 text-[11px] font-medium leading-4">{change.explanation || change.new_text || change.old_text || "Changed sentence"}</span>
                <span className="mt-2 flex items-center gap-1 truncate text-[10px] text-muted">{change.old_text ? <span className="max-w-[42%] truncate">{change.old_text}</span> : <span className="italic">No previous text</span>}<ArrowRight size={11} className="shrink-0" />{change.new_text ? <span className="truncate">{change.new_text}</span> : <span className="italic">Removed</span>}</span>
                <span className="mt-2 block truncate text-[9px] text-muted">{change.new_section ?? change.old_section ?? `Change ${index + 1}`}{change.new_page || change.old_page ? ` · page ${change.new_page ?? change.old_page}` : ""}</span>
              </button>)}
            </div>
          </section>

          <AnimatePresence mode="wait">
            {selected && <motion.section key={selected.id} initial={{ opacity: 0, y: 7 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} transition={{ duration: .16 }} className="surface rounded-2xl p-4" aria-live="polite">
              <div className="flex items-start justify-between gap-3"><div><Label>Change explanation</Label><h2 className="mt-1.5 text-base font-semibold">{titleForChange(selected.type)}</h2></div><span className={`change-badge rounded-full px-2 py-1 text-[9px] font-semibold ${changeTone(selected.type)}`}>{Math.round(selected.confidence * 100)}% confidence</span></div>
              <p className="mt-3 text-xs leading-5 text-[var(--ink)]">{selected.explanation || "The backend did not return an explanation for this change."}</p>
              <div className="mt-4 space-y-2.5 border-t border-subtle pt-3">
                <DetailQuote label="Original" text={selected.old_text} page={selected.old_page} tone="tone-deletion" />
                <DetailQuote label="Updated" text={selected.new_text} page={selected.new_page} tone="tone-addition" />
              </div>
              {Object.keys(selected.details).length > 0 && <div className="mt-4 border-t border-subtle pt-3"><Label>Analysis details</Label><dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-2">{Object.entries(selected.details).filter(([key, value]) => key !== "alignment_confidence" && value !== null && typeof value !== "object").map(([key, value]) => <div key={key} className="min-w-0"><dt className="truncate text-[9px] uppercase tracking-wide text-muted">{humanize(key)}</dt><dd className="mt-0.5 truncate text-[11px] font-medium">{typeof value === "number" ? value.toLocaleString() : String(value)}</dd></div>)}</dl></div>}
              <div className="mt-4 flex items-center justify-between border-t border-subtle pt-3 text-[10px] text-muted"><span>{selected.old_section ?? selected.new_section ?? "Document"}</span><span className="flex items-center gap-1"><Check size={11} /> Source linked</span></div>
            </motion.section>}
          </AnimatePresence>
        </aside>
      </div>
    </div>
  );
}

function DocumentRow({ change, selected, onSelect }: { change: ChangeRecord; selected: boolean; onSelect: () => void }) {
  const tone = changeTone(change.type);
  const unchanged = change.type === "UNCHANGED";
  return <div id={`change-${change.id}`} className={`grid scroll-mt-40 grid-cols-2 border-b border-subtle transition-colors ${selected ? "bg-[var(--accent-soft)]/45" : ""}`}>
    <button onClick={onSelect} className={`focus-ring min-h-[75px] border-r border-subtle p-3 text-left sm:p-4 ${change.old_text && !unchanged ? "change-mark" : ""} ${changeTone(change.type)} ${selected ? "outline-none" : "hover:bg-[var(--surface-muted)]"}`} aria-label={`Select ${titleForChange(change.type)}: ${change.old_text ?? "No original sentence"}`}>
      {change.old_section && <p className="mb-2 truncate text-[9px] font-semibold uppercase tracking-[.1em] text-muted">{change.old_section}</p>}
      {change.old_text ? <p className={`text-xs leading-5 sm:text-[13px] ${unchanged ? "text-muted" : "text-[var(--ink)]"}`}>{change.old_text}</p> : <p className="flex min-h-8 items-center gap-1.5 text-[10px] italic text-muted"><ArrowDown size={12} className="text-[#5f9a6e]" /> Added in updated version</p>}
    </button>
    <button onClick={onSelect} className={`focus-ring min-h-[75px] p-3 text-left sm:p-4 ${change.new_text && !unchanged ? "change-mark" : ""} ${changeTone(change.type)} ${selected ? "outline-none" : "hover:bg-[var(--surface-muted)]"}`} aria-label={`Select ${titleForChange(change.type)}: ${change.new_text ?? "No updated sentence"}`}>
      {change.new_section && <p className="mb-2 truncate text-[9px] font-semibold uppercase tracking-[.1em] text-muted">{change.new_section}</p>}
      {change.new_text ? <p className={`text-xs leading-5 sm:text-[13px] ${unchanged ? "text-muted" : "text-[var(--ink)]"}`}>{change.new_text}</p> : <p className="flex min-h-8 items-center gap-1.5 text-[10px] italic text-muted"><ArrowDown size={12} className="rotate-180 text-[#ad6060]" /> Removed from updated version</p>}
      {!unchanged && <span className={`mt-2 inline-flex rounded-full px-1.5 py-0.5 text-[8px] font-semibold ${tone} change-badge`}>{titleForChange(change.type)}</span>}
    </button>
  </div>;
}

function DetailQuote({ label, text, page, tone }: { label: string; text: string | null; page: number | null; tone: string }) {
  return <div className={`rounded-r-lg border-l-2 px-3 py-2 ${text ? `change-mark ${tone}` : "bg-[var(--surface-muted)]"}`}><div className="flex items-center justify-between"><p className="text-[9px] font-semibold uppercase tracking-[.12em] text-muted">{label}</p>{page && <span className="inline-flex items-center gap-1 text-[9px] text-muted"><FileText size={10} /> p. {page}</span>}</div><p className={`mt-1 text-[11px] leading-4 ${text ? "" : "italic text-muted"}`}>{text ?? "No sentence on this side"}</p></div>;
}

function humanize(key: string) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
