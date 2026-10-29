import { useEffect, useState } from "react";

export interface LeafVisualizationMode {
  id: string;
  label: string;
  source: string | null;
}

interface LeafOverlayProps {
  leafId: number;
  modes: LeafVisualizationMode[];
  onImageError?: (source: string) => void;
}

export default function LeafOverlay({
  leafId,
  modes,
  onImageError,
}: LeafOverlayProps) {
  const [selectedMode, setSelectedMode] = useState(modes[0]?.id ?? "");
  const [failedSource, setFailedSource] = useState<string | null>(null);

  useEffect(() => {
    if (!modes.some((mode) => mode.id === selectedMode)) {
      setSelectedMode(modes[0]?.id ?? "");
    }
  }, [modes, selectedMode]);

  const selected = modes.find((mode) => mode.id === selectedMode);
  const imageFailed = selected?.source === failedSource;

  return (
    <section
      className="space-y-3"
      aria-label={`Visualizations for leaf ${leafId + 1}`}
    >
      {modes.length === 0 ? (
        <p
          className="grid min-h-40 place-items-center rounded-lg border border-dashed border-border px-4 text-center text-sm text-muted-foreground"
          role="status"
        >
          No visualizations were generated for this leaf.
        </p>
      ) : (
        <>
          <div
            className="flex flex-wrap gap-2"
            role="group"
            aria-label="Visualization mode"
          >
            {modes.map((mode) => (
              <button
                key={mode.id}
                type="button"
                aria-pressed={selectedMode === mode.id}
                onClick={() => setSelectedMode(mode.id)}
                className={`rounded-lg border px-3 py-1.5 text-xs transition ${
                  selectedMode === mode.id
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-background text-muted-foreground hover:text-foreground"
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>
          <figure className="rounded-xl border border-border bg-muted/20 p-3">
            <figcaption className="mb-2 text-sm font-medium">
              {selected?.label ?? "Visualization"}
            </figcaption>
            {selected?.source && !imageFailed ? (
              <img
                key={selected.source}
                src={selected.source}
                alt={`${selected.label} for leaf ${leafId + 1}`}
                onError={() => {
                  setFailedSource(selected.source);
                  onImageError?.(selected.source);
                }}
                className="max-h-[28rem] min-h-40 w-full rounded-lg object-contain"
              />
            ) : (
              <p
                className="grid min-h-40 place-items-center rounded-lg border border-dashed border-border px-4 text-center text-sm text-muted-foreground"
                role="status"
              >
                {imageFailed
                  ? "This saved visualization could not be loaded."
                  : "This visualization was saved but could not be loaded."}
              </p>
            )}
          </figure>
        </>
      )}
      {selected?.id.startsWith("attention") && (
        <p className="text-xs text-muted-foreground">
          Attention rollout shows model attention, not causal evidence for the
          predicted class.
        </p>
      )}
    </section>
  );
}
