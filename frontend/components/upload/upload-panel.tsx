"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Check, FileDiff, LoaderCircle, ShieldCheck, Sparkles } from "lucide-react";
import { createComparison } from "@/lib/api/client";
import { FileDropzone } from "@/components/upload/file-dropzone";
import { Button } from "@/components/ui/primitives";

export function UploadPanel({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const [oldFile, setOldFile] = useState<File | null>(null);
  const [newFile, setNewFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function compare() {
    if (!oldFile || !newFile || loading) return;
    setError("");
    setLoading(true);
    try {
      const result = await createComparison(oldFile, newFile);
      router.push(`/compare/${encodeURIComponent(result.comparison_id)}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "We couldn't complete this comparison. Please try again.");
      setLoading(false);
    }
  }

  return (
    <motion.section layout className="surface overflow-hidden rounded-2xl">
      <div className="flex items-start justify-between border-b border-subtle px-5 py-4 sm:px-6">
        <div><div className="mb-1 flex items-center gap-2"><span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-strong)]"><FileDiff size={15} /></span><h2 className="text-sm font-semibold">Compare two versions</h2></div><p className="pl-9 text-xs text-muted">Your files are analyzed by the configured Semantiq backend.</p></div>
        <span className="hidden items-center gap-1.5 rounded-full border border-subtle px-2.5 py-1 text-[10px] font-medium text-muted sm:flex"><ShieldCheck size={12} /> Private analysis</span>
      </div>
      <div className="space-y-4 p-5 sm:p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <FileDropzone title="Original document" eyebrow="Version 01" file={oldFile} onChange={setOldFile} disabled={loading} />
          <FileDropzone title="Updated document" eyebrow="Version 02" file={newFile} onChange={setNewFile} disabled={loading} />
        </div>
        <AnimatePresence>
          {error && <motion.div initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="rounded-lg border border-[#e8caca] bg-[#fbf1f0] px-3.5 py-2.5 text-xs leading-5 text-[#8e4141]" role="alert">{error}</motion.div>}
        </AnimatePresence>
        {loading && <div className="rounded-xl border border-subtle bg-[var(--surface-muted)] p-3.5" role="status" aria-live="polite"><div className="flex items-center gap-2 text-xs font-semibold"><LoaderCircle size={15} className="animate-spin text-[var(--accent-strong)]" /> Analyzing documents</div><p className="mt-1 pl-[23px] text-[11px] text-muted">The analysis service is processing both versions. This may take a moment.</p><div className="mt-3 h-1 overflow-hidden rounded-full bg-[var(--line)]"><div className="indeterminate h-full rounded-full bg-[var(--accent)]" /></div></div>}
        <div className="flex flex-col items-start justify-between gap-3 border-t border-subtle pt-4 sm:flex-row sm:items-center">
          <p className="flex items-center gap-1.5 text-[11px] text-muted"><Sparkles size={13} className="text-[var(--accent)]" /> Meaning and context, beyond a word-for-word diff</p>
          <Button className="button-primary min-w-[180px]" onClick={compare} disabled={!oldFile || !newFile || loading}>
            {loading ? <><LoaderCircle size={15} className="animate-spin" /> Comparing…</> : <>{compact ? "Start comparison" : "Compare documents"}<ArrowRight size={15} /></>}
          </Button>
        </div>
        {oldFile && newFile && !loading && <p className="flex items-center gap-1 text-[10px] text-muted sm:justify-end"><Check size={11} /> Files are ready. Nothing is uploaded until you start.</p>}
      </div>
    </motion.section>
  );
}
