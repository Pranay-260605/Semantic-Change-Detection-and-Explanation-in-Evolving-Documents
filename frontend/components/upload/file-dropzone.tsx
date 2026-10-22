"use client";

import { useRef, useState } from "react";
import { FileText, FileType2, FileUp, X } from "lucide-react";
import { configuredUploadLimitMb } from "@/lib/api/client";
import { formatBytes } from "@/lib/utils";
import { cn } from "@/lib/utils";

const accepted = [".pdf", ".docx", ".txt"];

interface FileDropzoneProps {
  title: string;
  eyebrow: string;
  file: File | null;
  onChange: (file: File | null) => void;
  disabled?: boolean;
}

export function FileDropzone({ title, eyebrow, file, onChange, disabled }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");

  function choose(candidate?: File) {
    if (!candidate) return;
    const extension = `.${candidate.name.split(".").pop()?.toLowerCase() ?? ""}`;
    if (!accepted.includes(extension)) {
      setError("Choose a PDF, DOCX, or TXT file.");
      return;
    }
    if (candidate.size > configuredUploadLimitMb * 1024 * 1024) {
      setError(`This file exceeds the ${configuredUploadLimitMb} MB upload limit.`);
      return;
    }
    setError("");
    onChange(candidate);
  }

  const ext = file?.name.split(".").pop()?.toUpperCase() ?? "DOC";
  const Icon = ext === "PDF" ? FileType2 : FileText;

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold">{title}</span>
        <span className="text-[10px] font-semibold uppercase tracking-[.14em] text-muted">{eyebrow}</span>
      </div>
      {file ? (
        <div className="flex min-h-[76px] items-center gap-3 rounded-xl border border-[var(--line-strong)] bg-[var(--surface-muted)] px-3.5 py-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-strong)]"><Icon size={19} /></span>
          <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{file.name}</p><p className="mt-1 text-[11px] text-muted">{ext} · {formatBytes(file.size)}</p></div>
          <span className="hidden items-center gap-1 text-[11px] font-medium text-[#51815f] sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-[#659b74]" /> Ready</span>
          <button type="button" className="focus-ring rounded-md p-1.5 text-muted hover:bg-[var(--line)] hover:text-[var(--ink)]" onClick={() => { onChange(null); setError(""); if (inputRef.current) inputRef.current.value = ""; }} disabled={disabled} aria-label={`Remove ${file.name}`}><X size={16} /></button>
        </div>
      ) : (
        <button
          type="button"
          className={cn("focus-ring flex min-h-[76px] w-full items-center gap-3 rounded-xl border border-dashed border-[var(--line-strong)] bg-[var(--surface-muted)] px-3.5 py-3 text-left transition-colors hover:border-[var(--accent)]", dragging && "drop-active")}
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => { event.preventDefault(); setDragging(false); choose(event.dataTransfer.files[0]); }}
          disabled={disabled}
          aria-label={`Choose ${title.toLowerCase()}`}
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-subtle bg-[var(--surface)] text-muted"><FileUp size={18} /></span>
          <span className="min-w-0 flex-1"><span className="block text-sm font-medium">Drop a file here or <span className="text-[var(--accent-strong)] underline underline-offset-2">browse</span></span><span className="mt-1 block text-[11px] text-muted">PDF, DOCX, or TXT · up to {configuredUploadLimitMb} MB</span></span>
        </button>
      )}
      <input ref={inputRef} type="file" accept={accepted.join(",")} className="sr-only" onChange={(event) => choose(event.target.files?.[0])} disabled={disabled} />
      {error && <p role="alert" className="mt-1.5 text-xs text-[#a24f4f]">{error}</p>}
    </div>
  );
}
