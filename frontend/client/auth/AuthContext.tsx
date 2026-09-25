import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import type { AuthUserResponse } from "@shared/api";
import { AuthApiError, authApi } from "@/lib/auth-api";
import {
  clearAuthSession,
  readAuthSession,
  writeAuthSession,
  type AuthSession,
} from "@/lib/auth-session";

type AuthStatus = "loading" | "anonymous" | "authenticated" | "unavailable";

interface AuthState {
  status: AuthStatus;
  user: AuthUserResponse | null;
  session: AuthSession | null;
  error: string | null;
  sessionExpired: boolean;
}

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUserResponse | null;
  accessToken: string | null;
  error: string | null;
  sessionExpired: boolean;
  login(email: string, password: string): Promise<void>;
  register(email: string, password: string): Promise<AuthUserResponse>;
  logout(): void;
  retrySession(): Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const initialState: AuthState = {
  status: "loading",
  user: null,
  session: null,
  error: null,
  sessionExpired: false,
};

function storage(): Storage {
  return window.sessionStorage;
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof AuthApiError && error.status === 401;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Authentication request failed. Please try again.";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(initialState);

  const retrySession = useCallback(async () => {
    setState((current) => ({ ...current, status: "loading", error: null }));

    let session: AuthSession | null;
    try {
      session = readAuthSession(storage());
    } catch {
      setState({
        status: "unavailable",
        user: null,
        session: null,
        error: "Browser session storage is unavailable. Sign-in cannot be persisted in this tab.",
        sessionExpired: false,
      });
      return;
    }

    if (!session) {
      setState({ ...initialState, status: "anonymous" });
      return;
    }

    if (session.expiresAt <= Date.now()) {
      try {
        clearAuthSession(storage());
      } catch {
        // The in-memory identity is still discarded below.
      }
      setState({ ...initialState, status: "anonymous", sessionExpired: true });
      return;
    }

    try {
      const user = await authApi.currentUser(session.accessToken);
      setState({ status: "authenticated", user, session, error: null, sessionExpired: false });
    } catch (error) {
      if (isUnauthorized(error)) {
        try {
          clearAuthSession(storage());
        } catch {
          // The backend rejected the token; do not restore the identity in memory.
        }
        setState({ ...initialState, status: "anonymous", sessionExpired: true });
        return;
      }

      setState({
        status: "unavailable",
        user: null,
        session,
        error: errorMessage(error),
        sessionExpired: false,
      });
    }
  }, []);

  useEffect(() => {
    void retrySession();
  }, [retrySession]);

  useEffect(() => {
    if (state.status !== "authenticated" || !state.session) return;

    const timeout = window.setTimeout(() => {
      try {
        clearAuthSession(storage());
      } catch {
        // Expiration still clears the in-memory identity.
      }
      setState({ ...initialState, status: "anonymous", sessionExpired: true });
    }, Math.max(0, state.session.expiresAt - Date.now()));

    return () => window.clearTimeout(timeout);
  }, [state.status, state.session]);

  const login = useCallback(async (email: string, password: string) => {
    const token = await authApi.login({ email, password });
    if (token.token_type !== "bearer" || !token.access_token || token.expires_in <= 0) {
      throw new Error("The authentication service returned an invalid session.");
    }

    const session = { accessToken: token.access_token, expiresAt: Date.now() + token.expires_in * 1000 };
    try {
      writeAuthSession(storage(), session);
    } catch {
      throw new Error("Could not save the sign-in in this tab. Check browser storage settings and try again.");
    }

    try {
      const user = await authApi.currentUser(session.accessToken);
      setState({ status: "authenticated", user, session, error: null, sessionExpired: false });
    } catch (error) {
      if (isUnauthorized(error)) {
        try {
          clearAuthSession(storage());
        } catch {
          // The rejected token will not be accepted by the API.
        }
        setState({ ...initialState, status: "anonymous", sessionExpired: true });
      } else {
        setState({
          status: "unavailable",
          user: null,
          session,
          error: errorMessage(error),
          sessionExpired: false,
        });
      }
      throw error;
    }
  }, []);

  const register = useCallback(
    (email: string, password: string) => authApi.register({ email, password }),
    [],
  );

  const logout = useCallback(() => {
    let error: string | null = null;
    try {
      clearAuthSession(storage());
    } catch {
      error = "This tab could not clear its saved session. Close the tab to discard it.";
    }
    setState({ ...initialState, status: "anonymous", error });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status: state.status,
      user: state.user,
      accessToken: state.status === "authenticated" ? state.session?.accessToken ?? null : null,
      error: state.error,
      sessionExpired: state.sessionExpired,
      login,
      register,
      logout,
      retrySession,
    }),
    [state, login, register, logout, retrySession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
