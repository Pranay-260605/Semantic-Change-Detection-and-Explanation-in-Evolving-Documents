import { ArrowLeft, FileDiff } from "lucide-react";
import Link from "next/link";
import { UploadPanel } from "@/components/upload/upload-panel";

export default function NewComparisonPage() {
  return <div className="mx-auto max-w-[980px] px-4 py-8 sm:px-7 sm:py-11"><Link href="/" className="focus-ring inline-flex items-center gap-1.5 rounded text-xs text-muted hover:text-[var(--ink)]"><ArrowLeft size={14} /> Back to overview</Link><div className="mb-6 mt-7"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent-strong)]"><FileDiff size={18} /></span><h1 className="mt-4 text-3xl font-semibold tracking-[-.045em]">Start a comparison</h1><p className="mt-2 text-sm text-muted">Add the earlier and updated versions. Semantiq will return the detected changes and source context.</p></div><UploadPanel compact /></div>;
}
