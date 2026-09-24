import { Leaf } from "lucide-react";

export default function PlantsPage() {
  return (
    <section className="mx-auto flex min-h-[55vh] max-w-2xl flex-col items-center justify-center rounded-[28px] border border-border bg-card p-8 text-center">
      <span className="grid size-16 place-items-center rounded-2xl bg-[hsl(var(--sage))] text-primary">
        <Leaf size={28} />
      </span>
      <h2 className="mt-5 text-2xl font-semibold">No plant records</h2>
      <p className="mt-3 text-sm text-muted-foreground">
        Plant records cannot be created or loaded because the backend has no plant persistence API.
      </p>
    </section>
  );
}
