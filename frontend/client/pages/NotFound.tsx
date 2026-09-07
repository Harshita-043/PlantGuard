import { Link } from "react-router-dom";
import { ArrowLeft, Leaf } from "lucide-react";

export default function NotFound() {
  return <div className="mx-auto flex min-h-[70vh] max-w-xl items-center justify-center"><div className="w-full rounded-[28px] border border-border/80 bg-card p-10 text-center shadow-sm"><span className="mx-auto grid size-16 place-items-center rounded-2xl bg-[hsl(var(--sage))] text-primary"><Leaf size={29} /></span><p className="mt-6 text-xs font-bold uppercase tracking-[0.18em] text-[hsl(var(--ai-accent))]">404 / leaf not found</p><h1 className="mt-3 text-3xl font-semibold tracking-[-0.05em]">This path has gone dormant.</h1><p className="mt-3 text-sm leading-6 text-muted-foreground">The page you’re looking for doesn’t exist in this garden.</p><Link to="/dashboard" className="mt-7 inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground"><ArrowLeft size={16} /> Back to dashboard</Link></div></div>;
}
