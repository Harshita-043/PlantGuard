import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle, Leaf, Loader, Plus, Sprout, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/AuthContext";
import { ApiError, plantsApi } from "@/lib/api";
import type { PlantDetailResponse, PlantPayload, PlantResponse } from "@shared/api";

const emptyForm: PlantPayload = { name: "", species: null, location: null, notes: null };

export default function PlantsPage() {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const [plants, setPlants] = useState<PlantResponse[]>([]);
  const [details, setDetails] = useState<Record<string, PlantDetailResponse>>({});
  const [expandedPlant, setExpandedPlant] = useState<string | null>(null);
  const [editingPlant, setEditingPlant] = useState<string | null>(null);
  const [form, setForm] = useState<PlantPayload>(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPlants = useCallback(async () => {
    if (!accessToken) {
      setError("Sign in to manage your plants.");
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      setPlants(await plantsApi.getPlants(accessToken));
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        navigate("/login", { replace: true });
        return;
      }
      setError(caught instanceof Error ? caught.message : "Plants could not be loaded.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, logout, navigate]);

  useEffect(() => {
    void loadPlants();
  }, [loadPlants]);

  const submitForm = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!accessToken || isSaving) return;
    setIsSaving(true);
    setError(null);
    const payload: PlantPayload = {
      name: form.name.trim(),
      species: form.species?.trim() || null,
      location: form.location?.trim() || null,
      notes: form.notes?.trim() || null,
    };
    try {
      if (editingPlant) {
        const updated = await plantsApi.updatePlant(editingPlant, payload, accessToken);
        setPlants((current) => current.map((plant) => plant.id === updated.id ? updated : plant));
      } else {
        const created = await plantsApi.createPlant(payload, accessToken);
        setPlants((current) => [created, ...current]);
      }
      setForm(emptyForm);
      setEditingPlant(null);
      setShowForm(false);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        navigate("/login", { replace: true });
        return;
      }
      setError(caught instanceof Error ? caught.message : "The plant could not be saved.");
    } finally {
      setIsSaving(false);
    }
  };

  const editPlant = (plant: PlantResponse) => {
    setEditingPlant(plant.id);
    setForm({
      name: plant.name,
      species: plant.species,
      location: plant.location,
      notes: plant.notes,
    });
    setShowForm(true);
  };

  const deletePlant = async (plant: PlantResponse) => {
    if (!accessToken || !window.confirm(`Remove "${plant.name}"? Its scan records will remain.`)) return;
    try {
      await plantsApi.deletePlant(plant.id, accessToken);
      setPlants((current) => current.filter((item) => item.id !== plant.id));
      setDetails((current) => {
        const next = { ...current };
        delete next[plant.id];
        return next;
      });
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        navigate("/login", { replace: true });
        return;
      }
      setError(caught instanceof Error ? caught.message : "The plant could not be removed.");
    }
  };

  const toggleDetails = async (plantId: string) => {
    if (expandedPlant === plantId) {
      setExpandedPlant(null);
      return;
    }
    setExpandedPlant(plantId);
    if (details[plantId] || !accessToken) return;
    try {
      const detail = await plantsApi.getPlant(plantId, accessToken);
      setDetails((current) => ({ ...current, [plantId]: detail }));
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        navigate("/login", { replace: true });
        return;
      }
      setError(caught instanceof Error ? caught.message : "Plant scan history could not be loaded.");
    }
  };

  return (
    <section className="mx-auto max-w-5xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold">My plants</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Track plants you name and associate them with saved scans.
          </p>
        </div>
        <Button
          onClick={() => {
            setEditingPlant(null);
            setForm(emptyForm);
            setShowForm((open) => !open);
          }}
        >
          <Plus size={16} className="mr-2" />Add plant
        </Button>
      </header>

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-destructive/40 p-4 text-sm text-destructive" role="alert">
          <AlertTriangle size={18} />{error}
        </div>
      )}

      {showForm && (
        <form onSubmit={submitForm} className="grid gap-4 rounded-2xl border border-border bg-card p-5 sm:grid-cols-2">
          <h3 className="font-semibold sm:col-span-2">{editingPlant ? "Edit plant details" : "Add a plant"}</h3>
          <label className="grid gap-1 text-sm">
            Plant name
            <input required maxLength={128} value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} className="rounded-lg border border-border bg-background px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">
            Species (optional)
            <input maxLength={128} value={form.species ?? ""} onChange={(event) => setForm((current) => ({ ...current, species: event.target.value }))} className="rounded-lg border border-border bg-background px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">
            Location (optional)
            <input maxLength={128} value={form.location ?? ""} onChange={(event) => setForm((current) => ({ ...current, location: event.target.value }))} className="rounded-lg border border-border bg-background px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">
            Notes (optional)
            <input maxLength={512} value={form.notes ?? ""} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} className="rounded-lg border border-border bg-background px-3 py-2" />
          </label>
          <div className="flex gap-2 sm:col-span-2">
            <Button type="submit" disabled={isSaving || !accessToken}>
              {isSaving && <Loader size={15} className="mr-2 animate-spin" />}
              {editingPlant ? "Save changes" : "Create plant"}
            </Button>
            <Button type="button" variant="outline" onClick={() => { setShowForm(false); setEditingPlant(null); setForm(emptyForm); }}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {isLoading ? (
        <p className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground" role="status">
          <Loader size={18} className="animate-spin" />Loading your plants…
        </p>
      ) : plants.length === 0 ? (
        <div className="rounded-2xl border border-border bg-card p-8 text-center">
          <Sprout size={28} className="mx-auto text-primary" />
          <h3 className="mt-3 font-semibold">No plant records yet</h3>
          <p className="mt-1 text-sm text-muted-foreground">Add a plant to keep related scans together.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {plants.map((plant) => {
            const detail = details[plant.id];
            return (
              <article key={plant.id} className="space-y-4 rounded-2xl border border-border bg-card p-5">
                <div className="flex items-start gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary"><Leaf size={20} /></span>
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate font-semibold">{plant.name}</h3>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {[plant.species, plant.location].filter(Boolean).join(" · ") || "Species and location not specified"}
                    </p>
                  </div>
                  <span className="rounded-full bg-muted px-2.5 py-1 text-xs">{plant.total_scans} scans</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  Latest status: {plant.health_status?.replace(/_/g, " ") ?? "not available"}
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button asChild size="sm">
                    <Link to={`/scan?plant_id=${encodeURIComponent(plant.id)}`}>Scan this plant</Link>
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => void toggleDetails(plant.id)}>
                    {expandedPlant === plant.id ? "Hide history" : "View history"}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => editPlant(plant)}>Edit</Button>
                  <Button size="sm" variant="outline" onClick={() => void deletePlant(plant)} aria-label={`Delete ${plant.name}`}>
                    <Trash2 size={15} />
                  </Button>
                  {plant.latest_analysis && (
                    <Button asChild size="sm" variant="ghost">
                      <Link to={`/scan/results/${encodeURIComponent(plant.latest_analysis.analysis_id)}`}>Latest result</Link>
                    </Button>
                  )}
                </div>
                {expandedPlant === plant.id && (
                  <div className="border-t border-border pt-3">
                    {detail ? (
                      detail.recent_scans.length ? (
                        <ul className="space-y-2">
                          {detail.recent_scans.map((scan) => (
                            <li key={scan.analysis_id}>
                              <Link className="flex justify-between gap-3 text-sm hover:text-primary" to={`/scan/results/${encodeURIComponent(scan.analysis_id)}`}>
                                <span>Scan {scan.analysis_id.slice(0, 8)}</span>
                                <span className="text-muted-foreground">{scan.status} · {new Date(scan.created_at).toLocaleDateString()}</span>
                              </Link>
                            </li>
                          ))}
                        </ul>
                      ) : <p className="text-sm text-muted-foreground">No scans are associated with this plant.</p>
                    ) : <p className="text-sm text-muted-foreground">Loading plant history…</p>}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
