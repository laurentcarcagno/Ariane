"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { me, type Me } from "@/lib/api";
import { loadConfig, signIn, signOut } from "@/lib/auth";

interface Session { user: Me | null; logout: (() => void) | null }
const SessionContext = createContext<Session>({ user: null, logout: null });
export const useSession = (): Session => useContext(SessionContext);

/** Signs the user in (Keycloak, PKCE) before rendering the app; passes straight through when auth is disabled. */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let dead = false;
    (async () => {
      try {
        const cfg = await loadConfig();
        if (!cfg.authDisabled && (await signIn(cfg)) === null) return; // redirected to the login page
        const user = await me();
        if (!dead) setSession({ user, logout: cfg.authDisabled ? null : () => void signOut() });
      } catch (e) { if (!dead) setError((e as Error).message); }
    })();
    return () => { dead = true; };
  }, []);

  if (error) return <p role="alert" className="m-8 border border-danger bg-danger-bg p-4 text-danger">Connexion impossible : {error}</p>;
  if (!session) return <p className="m-8 text-mute">Connexion…</p>;
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}
