# ADR-006 Browser owner login and runtime public configuration

SCN-005 AC-07; 2026-09-17. Keep React/Vite, Sarabun/Inter and Charcoal Gold.

Use the official `@supabase/supabase-js` SDK, exactly pinned with its lockfile,
for password/session lifecycle. The browser obtains a small public configuration
from `/api/auth/config`, generated from the same validated API owner settings.
This avoids a second, potentially mismatched build-time Auth project or embedded
credentials. Only origin and publishable/legacy-anon key are public. No owner UUID
or executor credential is part of that configuration.

Admission: SDK 2.116.0, registry publication 2026-09-07; Node >=22 requirement met
by pinned Node 24.21.0. Installed with `--save-exact --ignore-scripts
--min-release-age=7`; nine new dependencies and their integrity hashes are locked.
`npm audit` found zero vulnerabilities. Production signature audit verified 14
registry signatures and 13 attestations. The whole-tree signature audit remains
incomplete because the registry returned 404 for the pre-existing dev dependency
`whatwg-url@17.1.1` attestation; no bypass or claimed full-tree PASS.
Lazy-load the SDK only when runtime Auth is enabled. The current build adds a
separate approximately 55 kB gzip SDK chunk; no analytics or new UI framework.

Keep sessions in memory (`persistSession=false`), allow SDK auto refresh and disable
URL session detection. Reload closes the browser's session context and requires
another sign-in; it does not claim remote revocation. Logout explicitly uses local
scope, hides data immediately and reports failed remote revocation for retry.
This single-owner prototype trades persistent login convenience for no tokens in
localStorage/sessionStorage. Passwords go directly to the configured Auth service,
not through the application API. HTTPS is required except explicit local loopback.

Keep the SDK behind a small adapter to exercise state races without mocking broker
truth. Serial telemetry polling uses a request deadline and generation guard.
An independent display clock ages retained quotes even when refresh is stalled.
The API, not a decoded browser JWT or metadata, decides owner access. Monitoring
does not unlock execution. No Next.js, hosting change or database migration.

## Visual plan and review

Palette: canvas #0d1117, panel #171d25, gold #d6b46a, text #f1f3f5,
muted #98a2b3, warning #f1b84b. Sarabun for Thai; Inter for numbers.
Left-align labels and account facts. Keep one account workspace below the safety
banner, followed by existing readiness/risk panels. On mobile the form stacks.

```text
[ Demo safety lock                                 ]
[ Account access / connection state                ]
[ Email                 Password          Sign in  ]
              after authorized API response
[ Broker identity                      Sign out   ]
[ Equity     Balance     Bid     Ask    Data age   ]
[ UTC event / received time; Bangkok display       ]
```

Review: reuse the project's established palette rather than redesigning unrelated
cards. Avoid an ornamental login hero, invented P/L, readiness percentage or price
chart. The distinctive feature is clear broker evidence and time, not decoration.

Official sources: [password sign-in](https://supabase.com/docs/reference/javascript/auth-signinwithpassword),
[Auth events](https://supabase.com/docs/reference/javascript/auth-onauthstatechange),
[local logout scope](https://supabase.com/docs/reference/javascript/auth-signout),
[npm security](https://supabase.com/docs/guides/security/npm-security).

## Browser integration verifier admission

Dev-only `playwright@1.63.0` is exactly pinned with `playwright-core@1.63.0` and
registry integrity hashes; installed with ignore-scripts and minimum release age
seven days. Use its matching Chromium headless shell (revision 1243,
153.0.8010.12), not an assumed system Chrome path. No new production dependency,
test framework, hosted browser service or global browser installation is added.
This reproducible local verifier uses generated credentials inside one Node process
and deliberately does not record traces or credential-bearing CLI commands.

Mobile review found that exact decimal strings wrapped across lines in the original
two-column account grid. Preserve the existing palette/type and exact values; use
content-sized columns (minimum 14rem, capped by available width), left-aligned
tabular digits and cell-local horizontal scrolling for unusually long decimals.
At 390px the fixture values each fit one line, without truncation or precision loss.
This is a readability fix, not a new visual system or changed account calculation.

Refresh verification follows [Playwright clock control](https://playwright.dev/docs/clock).
The browser clock advances while the Auth server clock remains real; the SDK can
refresh twice before restoration. Acceptance requires that a real successful refresh
response issued the token actually used in a successful private read, not that the
first token in the rotation chain must be the final one. Logout must still revoke
that observed token before its real expiry. This is not hour-long expiry evidence.
