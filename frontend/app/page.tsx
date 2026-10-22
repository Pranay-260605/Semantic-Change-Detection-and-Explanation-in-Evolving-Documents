import Link from "next/link";
import { ArrowRight, Braces, ScanText, ShieldCheck } from "lucide-react";
import { UploadPanel } from "@/components/upload/upload-panel";
import { HistoryList } from "@/components/history/history-list";
import { Label } from "@/components/ui/primitives";

const capabilities = [
  { icon: ScanText, title: "Meaning-aware alignment", detail: "Connects sentences across rewrites and changed structure." },
  { icon: Braces, title: "Specific change signals", detail: "Surfaces numeric, temporal, and entity changes separately." },
  { icon: ShieldCheck, title: "Traceable explanations", detail: "Every result links back to the exact source sentence." },
];

export default function Home() {
  return (
    <div className="mx-auto max-w-[1440px] px-4 py-8 sm:px-7 sm:py-10 xl:px-10">
      <section className="mb-8 grid gap-6 lg:grid-cols-[1fr_300px] lg:items-end">
        <div className="max-w-3xl">
          <Label>Document change intelligence</Label>
          <h1 className="mt-3 text-[clamp(2.1rem,5vw,3.8rem)] font-semibold leading-[1.06] tracking-[-.055em]">See what changed.<br /><span className="font-normal text-[var(--accent-strong)]">Understand why it matters.</span></h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-muted sm:text-base">Compare evolving documents by meaning, not just matching words. Semantiq finds the shifts that deserve a closer look.</p>
          <Link href="/history" className="focus-ring mt-4 inline-flex items-center gap-1.5 rounded-md text-xs font-semibold text-[var(--accent-strong)]">View comparison history <ArrowRight size={14} /></Link>
        </div>
        <div className="hidden rounded-xl border border-subtle bg-[var(--surface)] p-4 lg:block"><div className="mb-3 flex items-center gap-2 text-xs font-semibold"><span className="h-2 w-2 rounded-full bg-[#659b74]" /> Analysis at a glance</div><div className="space-y-2.5">{capabilities.map(({ icon: Icon, title, detail }) => <div key={title} className="flex gap-2.5"><Icon size={15} className="mt-0.5 shrink-0 text-[var(--accent-strong)]" /><div><p className="text-[11px] font-semibold">{title}</p><p className="mt-0.5 text-[10px] leading-4 text-muted">{detail}</p></div></div>)}</div></div>
      </section>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,.75fr)]">
        <UploadPanel />
        <section className="surface rounded-2xl px-5 py-4 sm:px-6">
          <div className="mb-2 flex items-center justify-between"><div><h2 className="text-sm font-semibold">Recent comparisons</h2><p className="mt-1 text-xs text-muted">Your latest document analyses</p></div><Link href="/history" className="focus-ring inline-flex items-center gap-1 rounded text-[11px] font-semibold text-[var(--accent-strong)]">All history <ArrowRight size={13} /></Link></div>
          <HistoryList compact />
        </section>
      </div>

      <footer className="mt-9 flex flex-col justify-between gap-2 border-t border-subtle pt-4 text-[10px] text-muted sm:flex-row sm:items-center"><span>Semantiq · Version-aware document intelligence</span><span>PDF · DOCX · TXT</span></footer>
    </div>
  );
}
