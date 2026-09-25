import { describe, expect, it } from "vitest";

import {
  AUTH_SESSION_KEY,
  clearAuthSession,
  readAuthSession,
  writeAuthSession,
  type SessionStorageLike,
} from "./auth-session";

function createStorage(): SessionStorageLike {
  const values = new Map<string, string>();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

describe("auth session storage", () => {
  it("writes, reads, and clears the token session", () => {
    const storage = createStorage();
    const session = { accessToken: "signed-token", expiresAt: 1_800_000_000_000 };

    writeAuthSession(storage, session);

    expect(readAuthSession(storage)).toEqual(session);
    clearAuthSession(storage);
    expect(readAuthSession(storage)).toBeNull();
  });

  it("discards malformed saved session data", () => {
    const storage = createStorage();
    storage.setItem(AUTH_SESSION_KEY, JSON.stringify({ accessToken: "", expiresAt: "later" }));

    expect(readAuthSession(storage)).toBeNull();
    expect(storage.getItem(AUTH_SESSION_KEY)).toBeNull();
  });
});
