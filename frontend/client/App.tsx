import { useState } from "react";
import "./global.css";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, NavLink, Outlet, Route, Routes, useLocation } from "react-router-dom";
import {
  Bell,
  Bot,
  Moon,
  Sun,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  CloudSun,
  FileText,
  History,
  LayoutDashboard,
  Leaf,
  LogOut,
  Menu,
  MessageCircle,
  MoreHorizontal,
  Plus,
  ScanLine,
  Settings,
  Sprout,
  UserRound,
  X,
} from "lucide-react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { ThemeProvider } from "@/components/theme-provider";
import { useTheme } from "next-themes";
import Index from "./pages/Index";
import PlantsPage from "./pages/PlantsPage";
import NotFound from "./pages/NotFound";
import ScanPage from "./pages/ScanPage";
import ScanResultsPage from "./pages/ScanResultsPage";
import HistoryPage from "./pages/HistoryPage";
import SettingsPage from "./pages/SettingsPage";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard" },
  { label: "My plants", icon: Sprout, to: "/plants" },
  { label: "Scan plant", icon: ScanLine, to: "/scan", emphasis: true },
  { label: "History", icon: History, to: "/history" },
  { label: "Recommendations", icon: FileText, to: "/recommendations" },
  { label: "Weather", icon: CloudSun, to: "/weather" },
  { label: "AI assistant", icon: MessageCircle, to: "/chat" },
];

const secondaryItems = [
  { label: "Profile", icon: UserRound, to: "/profile" },
  { label: "Settings", icon: Settings, to: "/settings" },
];

const titles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/plants": "My plants",
  "/scan": "Scan plant",
  "/history": "History",
  "/recommendations": "Recommendations",
  "/weather": "Weather",
  "/chat": "AI assistant",
  "/profile": "Profile",
  "/settings": "Settings",
};

function Brand({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <Link to="/dashboard" className="flex items-center gap-3 px-2" aria-label="PlantGuard AI dashboard">
      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground shadow-[0_7px_20px_-8px_hsl(var(--primary))]">
        <Leaf size={19} strokeWidth={2.4} />
      </span>
      {!collapsed && (
        <span className="leading-none">
          <span className="block text-[15px] font-bold tracking-[-0.03em] text-foreground">PlantGuard</span>
          <span className="mt-1 block text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">AI / plant health</span>
        </span>
      )}
    </Link>
  );
}

function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  return <button onClick={() => setTheme(isDark ? "light" : "dark")} className={`flex items-center gap-2 rounded-xl text-muted-foreground transition hover:bg-muted hover:text-foreground ${compact ? "grid size-10 place-items-center" : "px-3 py-2.5 text-xs font-semibold"}`} aria-label={`Switch to ${isDark ? "light" : "dark"} mode`} title={`Switch to ${isDark ? "light" : "dark"} mode`}>{isDark ? <Sun size={17} /> : <Moon size={17} />}{!compact && <span>{isDark ? "Light mode" : "Dark mode"}</span>}</button>;
}

function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <aside className={`hidden min-h-screen shrink-0 border-r border-border/70 bg-card transition-all duration-300 lg:flex lg:flex-col ${collapsed ? "w-[84px]" : "w-[252px]"}`}>
      <div className="flex h-[82px] items-center justify-between border-b border-border/60 px-4">
        <Brand collapsed={collapsed} />
        {!collapsed && (
          <button onClick={onToggle} className="grid size-8 place-items-center rounded-lg text-muted-foreground transition hover:bg-muted hover:text-foreground" aria-label="Collapse sidebar">
            <ChevronLeft size={17} />
          </button>
        )}
        {collapsed && (
          <button onClick={onToggle} className="absolute left-[68px] top-6 grid size-8 place-items-center rounded-lg bg-card text-muted-foreground shadow-sm ring-1 ring-border/80 transition hover:text-foreground" aria-label="Expand sidebar">
            <ChevronRight size={17} />
          </button>
        )}
      </div>
      <nav className="flex-1 px-3 py-7" aria-label="Primary navigation">
        <p className={`mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground/80 ${collapsed ? "sr-only" : ""}`}>Workspace</p>
        <div className="space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                title={collapsed ? item.label : undefined}
                className={({ isActive }) => `group flex items-center gap-3 rounded-xl px-3 py-3 text-[13px] font-medium transition ${isActive ? "bg-primary text-primary-foreground shadow-[0_8px_22px_-12px_hsl(var(--primary))]" : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"} ${item.emphasis && !isActive ? "text-primary" : ""}`}
              >
                <Icon size={19} strokeWidth={1.9} />
                {!collapsed && <span>{item.label}</span>}
                {!collapsed && item.emphasis && <span className="ml-auto size-1.5 rounded-full bg-[hsl(var(--ai-accent))]" />}
              </NavLink>
            );
          })}
        </div>
        <div className="my-7 h-px bg-border/70" />
        <p className={`mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground/80 ${collapsed ? "sr-only" : ""}`}>Account</p>
        <div className="space-y-1.5">
          {secondaryItems.map((item) => {
            const Icon = item.icon;
            return <NavLink key={item.to} to={item.to} title={collapsed ? item.label : undefined} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-3 text-[13px] font-medium transition ${isActive ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"}`}><Icon size={19} strokeWidth={1.9} />{!collapsed && <span>{item.label}</span>}</NavLink>;
          })}
        </div>
      </nav>
      <div className={`border-t border-border/70 p-4 ${collapsed ? "flex justify-center" : ""}`}>
        <div className={`flex items-center gap-3 rounded-xl bg-muted/70 p-2.5 ${collapsed ? "w-11 justify-center" : ""}`}>
          <div className="grid size-8 shrink-0 place-items-center rounded-full bg-[hsl(var(--sage))] text-xs font-bold text-primary">SC</div>
          {!collapsed && <div className="min-w-0 flex-1"><p className="truncate text-xs font-semibold text-foreground">Guest</p><p className="truncate text-[11px] text-muted-foreground">Authentication unavailable</p></div>}
          {!collapsed && <LogOut size={16} className="text-muted-foreground" />}
        </div>
      </div>
    </aside>
  );
}

function MobileNav({ onMore }: { onMore: () => void }) {
  const items = navItems.slice(0, 2).concat(navItems[3], { label: "More", icon: MoreHorizontal, to: "#" });
  return <nav className="fixed inset-x-0 bottom-0 z-40 flex h-[74px] items-end justify-around border-t border-border/80 bg-card/95 px-2 pb-[env(safe-area-inset-bottom)] shadow-[0_-8px_30px_-24px_rgba(0,0,0,.3)] backdrop-blur lg:hidden" aria-label="Mobile navigation">
    {items.map((item) => {
      const Icon = item.icon;
      if (item.label === "More") return <button key={item.label} onClick={onMore} className="flex min-w-[60px] flex-col items-center gap-1 py-2 text-muted-foreground"><Icon size={21} /><span className="text-[10px] font-medium">More</span></button>;
      if (item.label === "Scan plant") return <NavLink key={item.label} to={item.to} className="-mt-7 flex size-[58px] flex-col items-center justify-center gap-1 rounded-full border-[5px] border-background bg-primary text-primary-foreground shadow-lg"><Icon size={22} /><span className="text-[10px] font-semibold">Scan</span></NavLink>;
      return <NavLink key={item.label} to={item.to} className={({ isActive }) => `flex min-w-[60px] flex-col items-center gap-1 py-2 ${isActive ? "text-primary" : "text-muted-foreground"}`}><Icon size={20} /><span className="text-[10px] font-medium">{item.label === "Dashboard" ? "Home" : item.label === "My plants" ? "Plants" : item.label}</span></NavLink>;
    })}
  </nav>;
}

function MoreSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return <div className="fixed inset-0 z-50 bg-foreground/20 backdrop-blur-sm lg:hidden" onClick={onClose}><div className="absolute inset-x-0 bottom-0 rounded-t-[28px] bg-card p-5 pb-8 shadow-2xl" onClick={(e) => e.stopPropagation()}><div className="mx-auto mb-5 h-1 w-10 rounded-full bg-border" /><div className="mb-5 flex items-center justify-between"><div><h2 className="text-lg font-semibold">More from PlantGuard</h2><p className="text-xs text-muted-foreground">Tools to help your plants thrive</p></div><button onClick={onClose} className="grid size-9 place-items-center rounded-full bg-muted text-muted-foreground" aria-label="Close menu"><X size={18} /></button></div><div className="grid grid-cols-2 gap-2">{[...navItems.slice(4), ...secondaryItems].map((item) => { const Icon = item.icon; return <NavLink key={item.to} to={item.to} onClick={onClose} className="flex items-center gap-3 rounded-xl border border-border/70 p-3 text-sm font-medium text-foreground transition hover:bg-muted"><span className="grid size-9 place-items-center rounded-lg bg-muted text-primary"><Icon size={18} /></span>{item.label}</NavLink>; })}</div><div className="mt-3 flex items-center justify-between rounded-xl bg-muted/60 p-1"><span className="pl-3 text-xs font-semibold text-muted-foreground">Appearance</span><ThemeToggle compact /></div><button className="mt-3 flex w-full items-center gap-3 rounded-xl p-3 text-sm font-medium text-muted-foreground"><LogOut size={18} /> Log out</button></div></div>;
}

function AppHeader({ onMore }: { onMore: () => void }) {
  const location = useLocation();
  const title = titles[location.pathname] ?? (location.pathname.startsWith("/plants/") ? "Plant details" : "PlantGuard AI");
  return <header className="sticky top-0 z-30 flex h-[72px] items-center justify-between border-b border-border/70 bg-background/90 px-4 backdrop-blur-md sm:px-8 lg:px-10"><div className="flex items-center gap-3"><button onClick={onMore} className="grid size-10 place-items-center rounded-xl bg-card text-muted-foreground shadow-sm ring-1 ring-border/70 lg:hidden" aria-label="Open menu"><Menu size={19} /></button><div><p className="hidden text-[11px] font-medium text-muted-foreground sm:block">{new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" })}</p><h1 className="text-[19px] font-semibold tracking-[-0.03em] text-foreground sm:text-[21px]">{title}</h1></div></div><div className="flex items-center gap-2 sm:gap-4"><ThemeToggle compact /><Link to="/scan" className="hidden items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-semibold text-primary-foreground shadow-[0_8px_18px_-12px_hsl(var(--primary))] transition hover:-translate-y-0.5 sm:flex"><ScanLine size={16} /> Scan plant</Link><Link to="/profile" className="grid size-10 place-items-center rounded-full bg-[hsl(var(--sage))] text-xs font-bold text-primary ring-2 ring-card sm:size-9" aria-label="Profile">G</Link></div></header>;
}

function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  return <div className="min-h-screen bg-background"><div className="flex min-h-screen"><Sidebar collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} /><div className="min-w-0 flex-1"><AppHeader onMore={() => setMoreOpen(true)} /><main className="mx-auto w-full max-w-[1440px] px-4 pb-28 pt-7 sm:px-8 lg:px-10 lg:pb-10"><Outlet /></main></div></div><MobileNav onMore={() => setMoreOpen(true)} /><MoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} /></div>;
}

function PlaceholderPage({ title, icon: Icon = CircleHelp }: { title: string; icon?: typeof CircleHelp }) {
  return <div className="mx-auto flex min-h-[60vh] max-w-2xl items-center justify-center"><div className="w-full rounded-[28px] border border-border/80 bg-card p-10 text-center shadow-sm"><span className="mx-auto mb-5 grid size-16 place-items-center rounded-2xl bg-[hsl(var(--sage))] text-primary"><Icon size={29} /></span><p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-[hsl(var(--ai-accent))]">Coming next</p><h2 className="text-2xl font-semibold tracking-[-0.04em]">{title} is ready for your next prompt</h2><p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted-foreground">This route is wired into the PlantGuard shell. The next step is connecting its full data experience to the API contract.</p><Link to="/dashboard" className="mt-7 inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground">Back to dashboard <ChevronRight size={16} /></Link></div></div>;
}

export default function App() {
  return <ThemeProvider attribute="class" defaultTheme="system" enableSystem storageKey="plantguard-theme"><BrowserRouter><Toaster /><Sonner /><Routes><Route element={<AppShell />}><Route path="/" element={<Index />} /><Route path="/dashboard" element={<Index />} /><Route path="/plants" element={<PlantsPage />} /><Route path="/scan" element={<ScanPage />} />
<Route path="/scan/results/:scanId" element={<ScanResultsPage />} /><Route path="/history" element={<PlaceholderPage title="Scan history" icon={History} />} /><Route path="/recommendations" element={<PlaceholderPage title="Recommendations" icon={FileText} />} /><Route path="/weather" element={<PlaceholderPage title="Weather insights" icon={CloudSun} />} /><Route path="/chat" element={<PlaceholderPage title="AI assistant" icon={Bot} />} /><Route path="/profile" element={<PlaceholderPage title="Your profile" icon={UserRound} />} /><Route path="/settings" element={<PlaceholderPage title="Settings" icon={Settings} />} /><Route path="*" element={<NotFound />} /></Route></Routes></BrowserRouter></ThemeProvider>;
}

createRoot(document.getElementById("root")!).render(<App />);
