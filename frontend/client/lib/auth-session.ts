export const AUTH_SESSION_KEY = "plantguard.auth.session";

export interface AuthSession {
  accessToken: string;
  expiresAt: number;
}

export type SessionStorageLike = Pick<
  Storage,
  "getItem" | "setItem" | "removeItem"
>;

export function readAuthSession(
  storage: SessionStorageLike,
): AuthSession | null {
  const serialized = storage.getItem(AUTH_SESSION_KEY);
  if (!serialized) return null;

  try {
    const value: unknown = JSON.parse(serialized);
    if (
      typeof value === "object" &&
      value !== null &&
      "accessToken" in value &&
      "expiresAt" in value &&
      typeof value.accessToken === "string" &&
      value.accessToken.length > 0 &&
      typeof value.expiresAt === "number" &&
      Number.isFinite(value.expiresAt)
    ) {
      return { accessToken: value.accessToken, expiresAt: value.expiresAt };
    }
  } catch {
    // A corrupt local session is discarded; the backend remains authoritative.
  }

  storage.removeItem(AUTH_SESSION_KEY);
  return null;
}

export function writeAuthSession(
  storage: SessionStorageLike,
  session: AuthSession,
): void {
  storage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
}

export function clearAuthSession(storage: SessionStorageLike): void {
  storage.removeItem(AUTH_SESSION_KEY);
}
