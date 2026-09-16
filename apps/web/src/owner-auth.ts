import type { AuthConfig } from "./owner-api";

export interface OwnerAuth {
  signIn(email: string, password: string): Promise<void>;
  signOut(): Promise<void>;
  watch(callback: (token: string | null) => void): () => void;
  dispose(): void;
}
export type AuthFactory = (config: Extract<AuthConfig, { enabled: true }>) => Promise<OwnerAuth>;

export const createOwnerAuth: AuthFactory = async (config) => {
  const { createClient } = await import("@supabase/supabase-js");
  const client = createClient(config.supabase_url, config.public_key, {
    auth: { persistSession: false, autoRefreshToken: true, detectSessionInUrl: false },
    global: { fetch: (input, init) => fetch(input, {
      ...init, redirect: "error", credentials: "omit",
      signal: AbortSignal.any([...(init?.signal ? [init.signal] : []), AbortSignal.timeout(10000)]),
    }) },
  });
  return {
    async signIn(email, password) {
      const { error } = await client.auth.signInWithPassword({ email, password });
      if (error) throw new Error("Sign-in failed");
    },
    async signOut() {
      const { error } = await client.auth.signOut({ scope: "local" });
      if (error) throw new Error("Sign-out not confirmed");
    },
    watch(callback) {
      const { data } = client.auth.onAuthStateChange((_event, session) => callback(session?.access_token ?? null));
      return () => data.subscription.unsubscribe();
    },
    dispose() { void client.auth.dispose(); },
  };
};
