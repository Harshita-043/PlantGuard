import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Leaf, LoaderCircle } from "lucide-react";

import { AuthApiError } from "@/lib/auth-api";
import { getReturnPath } from "@/lib/auth-navigation";
import { useAuth } from "@/auth/AuthContext";

type AuthPageProps = { mode: "login" | "register" };

export default function AuthPage({ mode }: AuthPageProps) {
  const isRegister = mode === "register";
  const location = useLocation();
  const navigate = useNavigate();
  const auth = useAuth();
  const routeState = typeof location.state === "object" && location.state !== null ? location.state : {};
  const initialEmail = "email" in routeState && typeof routeState.email === "string" ? routeState.email : "";
  const registered = "registered" in routeState && routeState.registered === true;
  const sessionExpired = auth.sessionExpired || ("sessionExpired" in routeState && routeState.sessionExpired === true);

  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (isRegister) {
        await auth.register(email, password);
        navigate("/login", {
          replace: true,
          state: { from: getReturnPath(location.state), registered: true, email },
        });
      } else {
        await auth.login(email, password);
        navigate(getReturnPath(location.state), { replace: true });
      }
    } catch (requestError) {
      setError(
        requestError instanceof AuthApiError
          ? requestError.message
          : "Could not connect to the authentication service. Check that the backend is running and try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-background px-4 py-10">
      <section className="w-full max-w-md rounded-[28px] border border-border/80 bg-card p-7 shadow-sm sm:p-9">
        <Link to="/login" className="mx-auto flex w-fit items-center gap-3" aria-label="PlantGuard sign in">
          <span className="grid size-11 place-items-center rounded-xl bg-primary text-primary-foreground">
            <Leaf size={22} />
          </span>
          <span className="text-lg font-bold tracking-tight">PlantGuard</span>
        </Link>

        <div className="mt-8 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">
            {isRegister ? "Create your account" : "Welcome back"}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {isRegister ? "Register with your email to get started." : "Sign in to continue to PlantGuard."}
          </p>
        </div>

        {registered && !isRegister && (
          <p className="mt-6 rounded-xl border border-primary/20 bg-primary/5 p-3 text-sm" role="status">
            Account created. Sign in with your new credentials.
          </p>
        )}
        {sessionExpired && !isRegister && (
          <p className="mt-6 rounded-xl border border-warning/30 bg-warning/10 p-3 text-sm" role="status">
            Your session expired. Sign in again to continue.
          </p>
        )}
        {auth.error && (
          <p className="mt-6 rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm" role="alert">
            The saved session could not be verified: {auth.error}
          </p>
        )}
        {error && (
          <p className="mt-6 rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive" role="alert">
            {error}
          </p>
        )}

        <form className="mt-7 space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              maxLength={320}
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              minLength={isRegister ? 12 : 1}
              maxLength={128}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            {isRegister && <p className="text-xs text-muted-foreground">Use 12 to 128 characters.</p>}
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting && <LoaderCircle size={16} className="animate-spin" />}
            {isSubmitting ? (isRegister ? "Creating account…" : "Signing in…") : isRegister ? "Create account" : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          {isRegister ? "Already have an account? " : "New to PlantGuard? "}
          <Link
            to={isRegister ? "/login" : "/register"}
            state={{ from: getReturnPath(location.state) }}
            className="font-semibold text-primary hover:underline"
          >
            {isRegister ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </section>
    </main>
  );
}
