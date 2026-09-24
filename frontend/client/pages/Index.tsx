import { Link } from "react-router-dom";
import { ScanLine, Sprout } from "lucide-react";

export default function Index() {
  return (
    <section className="mx-auto flex min-h-[55vh] max-w-3xl flex-col items-center justify-center rounded-[28px] border border-border bg-card p-8 text-center shadow-sm">
      <span className="grid size-16 place-items-center rounded-2xl bg-[hsl(var(--sage))] text-primary">
        <Sprout size={30} />
      </span>
      <h2 className="mt-5 text-2xl font-semibold tracking-[-0.04em]">PlantGuard AI</h2>
      <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">
        This repository currently has no account, plant, scan-history, or weather data services. Plant analysis is unavailable until real ML inference is integrated.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Link to="/scan" className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground">
          <ScanLine size={16} /> Try image upload
        </Link>
        <Link to="/plants" className="rounded-xl border border-border px-4 py-2.5 text-sm font-semibold">Plant records</Link>
      </div>
    </section>
  );
}
