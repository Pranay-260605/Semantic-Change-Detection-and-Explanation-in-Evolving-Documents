"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { BookOpenText, Clock3, FileDiff, Moon, PanelLeftClose, PanelLeftOpen, Plus, Sun, Workflow } from "lucide-react";
import { useTheme } from "@/components/layout/theme-provider";
import { cn } from "@/lib/utils";

const navigation = [
  { href: "/", label: "Overview", icon: Workflow },
  { href: "/compare", label: "Compare", icon: FileDiff },
  { href: "/history", label: "History", icon: Clock3 },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="app-bg">
      <aside className={cn("fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-subtle bg-[var(--surface)] py-5 transition-[width,padding] duration-200 lg:flex", collapsed ? "w-[72px] px-2.5" : "w-[228px] px-4")}>
        <div className={cn("mb-10 flex items-center", collapsed ? "justify-center" : "justify-between")}>
        <Link href="/" className="focus-ring flex items-center gap-3 rounded-xl px-2 py-1" aria-label="Semantiq home">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--accent-strong)] text-white"><BookOpenText size={19} /></span>
          {!collapsed && <span><span className="block text-[15px] font-semibold tracking-[-.03em]">semantiq</span><span className="text-[10px] uppercase tracking-[.15em] text-muted">Document intelligence</span></span>}
        </Link>
        {!collapsed && <button onClick={() => setCollapsed(true)} className="focus-ring rounded-md p-1.5 text-muted hover:bg-[var(--surface-muted)]" title="Collapse sidebar" aria-label="Collapse sidebar"><PanelLeftClose size={16} /></button>}
        </div>
        {!collapsed && <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[.17em] text-muted">Workspace</p>}
        {collapsed && <button onClick={() => setCollapsed(false)} className="focus-ring mb-3 flex justify-center rounded-md p-2 text-muted hover:bg-[var(--surface-muted)]" title="Expand sidebar" aria-label="Expand sidebar"><PanelLeftOpen size={16} /></button>}
        <nav className="space-y-1" aria-label="Main navigation">
          {navigation.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link key={href} href={href} title={collapsed ? label : undefined} className={cn("focus-ring group flex items-center rounded-lg py-2.5 text-[13px] transition-colors", collapsed ? "justify-center px-2" : "gap-3 px-3", active ? "bg-[var(--accent-soft)] font-semibold text-[var(--accent-strong)]" : "text-muted hover:bg-[var(--surface-muted)] hover:text-[var(--ink)]")}>
                <Icon size={17} strokeWidth={active ? 2.2 : 1.8} />{!collapsed && label}
              </Link>
            );
          })}
        </nav>
        {!collapsed && <div className="mt-auto rounded-xl border border-subtle bg-[var(--surface-muted)] p-3.5">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold"><span className="h-2 w-2 rounded-full bg-[#6b9b78]" /> Analysis service</div>
          <p className="text-[11px] leading-5 text-muted">Semantic comparison runs securely through your configured backend.</p>
        </div>}
      </aside>

      <div className={cn("min-h-screen transition-[padding] duration-200", collapsed ? "lg:pl-[72px]" : "lg:pl-[228px]")}>
        <header className="sticky top-0 z-20 flex h-[62px] items-center justify-between border-b border-subtle bg-[var(--surface)]/95 px-4 backdrop-blur-md sm:px-7">
          <Link href="/" className="focus-ring flex items-center gap-2 rounded-lg lg:hidden"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-strong)] text-white"><BookOpenText size={17} /></span><span className="text-sm font-semibold">semantiq</span></Link>
          <div className="hidden items-center gap-2 text-xs text-muted lg:flex"><span>Workspace</span><span className="text-[var(--line-strong)]">/</span><span className="font-medium text-[var(--ink)]">{pathname.startsWith("/history") ? "History" : pathname.startsWith("/compare/") ? "Comparison" : pathname.startsWith("/compare") ? "New comparison" : "Overview"}</span></div>
          <div className="ml-auto flex items-center gap-2">
            <Link href="/compare" className="button-primary focus-ring inline-flex h-9 items-center gap-2 rounded-lg px-3.5 text-xs font-semibold"><Plus size={15} /> <span className="hidden sm:inline">New comparison</span><span className="sm:hidden">Compare</span></Link>
            <button onClick={toggleTheme} className="button-secondary focus-ring flex h-9 w-9 items-center justify-center rounded-lg" aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`} title="Toggle appearance">{theme === "light" ? <Moon size={16} /> : <Sun size={16} />}</button>
          </div>
        </header>

        <nav className="flex border-b border-subtle bg-[var(--surface)] px-3 py-2 lg:hidden" aria-label="Mobile navigation">
          {navigation.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return <Link key={href} href={href} className={cn("focus-ring mx-1 flex flex-1 items-center justify-center gap-2 rounded-lg px-2 py-2 text-xs", active ? "bg-[var(--accent-soft)] font-semibold text-[var(--accent-strong)]" : "text-muted")}><Icon size={15} />{label}</Link>;
          })}
        </nav>
        <main>{children}</main>
      </div>
    </div>
  );
}
