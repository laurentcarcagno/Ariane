import { UserManager, WebStorageStateStore, type User } from "oidc-client-ts";

export interface PublicConfig { authDisabled: boolean; authority: string; clientId: string }

let manager: UserManager | null = null;
let current: User | null = null;

/** Bearer token for API calls; empty when authentication is disabled (development). */
export const accessToken = (): string | null => current?.access_token ?? null;

export async function loadConfig(): Promise<PublicConfig> {
  const res = await fetch("/api/v1/config");
  if (!res.ok) throw new Error(`config: HTTP ${res.status}`);
  return (await res.json()) as PublicConfig;
}

/** Authorization-code flow with PKCE. Returns the signed-in user, or null after redirecting to the login page. */
export async function signIn(cfg: PublicConfig): Promise<User | null> {
  manager = new UserManager({
    authority: cfg.authority,
    client_id: cfg.clientId,
    redirect_uri: `${window.location.origin}/`,
    post_logout_redirect_uri: `${window.location.origin}/`,
    response_type: "code",
    scope: "openid profile email",
    automaticSilentRenew: false,
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
  });
  const params = new URLSearchParams(window.location.search);
  if (params.has("code") && params.has("state")) {
    current = await manager.signinRedirectCallback();
    window.history.replaceState({}, "", window.location.pathname);
    return current;
  }
  const user = await manager.getUser();
  if (user && !user.expired) { current = user; return user; }
  await manager.signinRedirect();
  return null;
}

export async function signOut(): Promise<void> {
  current = null;
  await manager?.signoutRedirect();
}
