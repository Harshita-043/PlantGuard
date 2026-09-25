export function getReturnPath(state: unknown): string {
  if (typeof state !== "object" || state === null || !("from" in state)) return "/dashboard";
  const path = state.from;
  if (typeof path !== "string" || !path.startsWith("/") || path.startsWith("//")) return "/dashboard";
  return path;
}
