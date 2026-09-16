import { afterEach, expect, it, vi } from "vitest";
import { createOwnerAuth } from "./owner-auth";
// The SDK module probes storage support before a session exists. Load that module
// during setup; the assertion below covers every client/session lifecycle write.
import "@supabase/supabase-js";

afterEach(() => vi.restoreAllMocks());

it("uses the real pinned SDK for memory-only sign-in and local logout", async () => {
  const exp = Math.floor(Date.now() / 1000) + 3600;
  const token = [btoa(JSON.stringify({ alg: "HS256", typ: "JWT" })),
    btoa(JSON.stringify({ sub: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", exp, aud: "authenticated", role: "authenticated" })),
    btoa("synthetic-signature")].map(part => part.replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_")).join(".");
  const storageWrite = vi.spyOn(Storage.prototype, "setItem");
  const request = vi.spyOn(globalThis, "fetch").mockImplementation(async input => {
    const url = String(input);
    if (url.includes("/token?grant_type=password")) return new Response(JSON.stringify({
      access_token: token, refresh_token: "synthetic-refresh-only", token_type: "bearer", expires_in: 3600,
      user: { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", aud: "authenticated", role: "authenticated", email: "owner@sochron.test" },
    }), { status: 200, headers: { "Content-Type": "application/json" } });
    if (url.includes("/logout?scope=local")) return new Response(null, { status: 204 });
    throw new Error("Unexpected SDK request");
  });
  const auth = await createOwnerAuth({ enabled: true, supabase_url: "https://auth.fixture.invalid", public_key: "sb_publishable_" + "fixture".repeat(4) });
  const observed: (string | null)[] = [];
  const stop = auth.watch(value => observed.push(value));
  try {
    await auth.signIn("owner@sochron.test", "synthetic-password");
    expect(observed).toContain(token);
    await auth.signOut();
    expect(observed.at(-1)).toBeNull();
    expect(request.mock.calls.some(([url]) => String(url).includes("/logout?scope=local"))).toBe(true);
    expect(storageWrite).not.toHaveBeenCalled();
    expect(request.mock.calls.every(([, options]) => options?.credentials === "omit" && options?.redirect === "error")).toBe(true);
  } finally { stop(); auth.dispose(); }
});
