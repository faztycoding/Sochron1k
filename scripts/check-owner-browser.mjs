#!/usr/bin/env node
// SCN-005: real browser/Auth/API, synthetic telemetry, no broker operations.
import assert from "node:assert/strict";
import { spawn, execFileSync } from "node:child_process";
import { createHash, randomBytes, randomUUID } from "node:crypto";
import { mkdtemp, mkdir, readdir, readFile, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
process.chdir(root);
let stage = "prerequisites";
const checks = [];
function command(executable, args) {
  return execFileSync(executable, args, { cwd: root, encoding: "utf8", timeout: 30000,
    stdio: ["ignore", "pipe", "pipe"] }).trim();
}
async function http(url, options = {}) {
  return fetch(url, { ...options, redirect: "error", signal: AbortSignal.timeout(10000) });
}
async function stopChild(child) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  const exited = new Promise(done => child.once("exit", done));
  child.kill("SIGTERM");
  const timer = setTimeout(() => child.kill("SIGKILL"), 3000);
  await exited; clearTimeout(timer);
}
async function run() {
  assert.equal(process.version, "v24.21.0");
  assert(!process.env.DEBUG && !process.env.PWDEBUG && !process.env.NODE_OPTIONS);
  assert.notEqual(process.env.NODE_USE_ENV_PROXY, "1");
  command("bash", ["scripts/supabase-local.sh", "guard"]);
  const containers = command("docker", ["ps", "-q", "--filter", "label=com.supabase.cli.project=sochron1k"]).split(/\s+/);
  assert(containers.length > 0 && containers[0]);
  const runtimeImages = [];
  for (const container of containers) {
    const ports = JSON.parse(command("docker", ["inspect", container, "--format", "{{json .NetworkSettings.Ports}}"]));
    for (const bindings of Object.values(ports)) {
      assert((bindings ?? []).every(binding => binding.HostIp === "127.0.0.1"));
    }
    runtimeImages.push(command("docker", ["inspect", container, "--format", "{{.Name}} {{.Image}}"]));
  }
  assert.equal(command("npm", ["exec", "supabase", "--", "--version"]), "2.117.0");
  const local = JSON.parse(command("npm", ["exec", "supabase", "--", "status", "-o", "json"]));
  const origin = local.API_URL;
  assert.equal(origin, "http://127.0.0.1:54321");
  const admin = { apikey: local.SERVICE_ROLE_KEY, Authorization: `Bearer ${local.SERVICE_ROLE_KEY}` };
  const { chromium } = await import("playwright");
  const { preview } = await import("vite");
  const revision = command("git", ["rev-parse", "HEAD"]);
  stage = "build production artifact";
  command("npm", ["run", "build"]);
  const buildFiles = (await readdir("apps/web/dist", { recursive: true, withFileTypes: true }))
    .filter(entry => entry.isFile()).map(entry => join(entry.parentPath, entry.name)).sort();
  assert(buildFiles.includes("apps/web/dist/index.html"));
  const buildHash = createHash("sha256");
  for (const file of buildFiles) buildHash.update(file).update("\0").update(await readFile(file)).update("\0");
  const buildSha256 = buildHash.digest("hex");
  const output = join(root, "output/playwright", `scn005-${randomUUID()}`);
  await mkdir(output, { recursive: true });
  const temporary = await mkdtemp(join(tmpdir(), "sochron-browser-"));
  const users = [];
  let api;
  let web;
  let browser;
  let pump;
  let pumping = false;
  let feedEnabled = true;
  let pumpFailure = false;
  let cleanupOK = true;
  let creationUnresolved = false;
  let browserVersion;
  let failureStage = null;
  const refreshDiagnostics = { exchanges: 0, used_refreshed_token: false };
  try {
    stage = "create isolated local users";
    for (let index = 0; index < 2; index++) {
      const email = `scn005-browser-${randomUUID()}@sochron.test`;
      const password = randomBytes(32).toString("base64url") + "!aA1";
      creationUnresolved = true;
      const response = await http(`${origin}/auth/v1/admin/users`, {
        method: "POST", headers: { ...admin, "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, email_confirm: true, user_metadata: { role: "owner" } }),
      });
      assert([200, 201].includes(response.status));
      const { id } = await response.json();
      assert.match(id, /^[0-9a-f-]{36}$/);
      users.push({ id, email, password });
      creationUnresolved = false;
    }
    stage = "start isolated API";
    const template = JSON.parse(await readFile("tests/fixtures/mt5-telemetry-v1.json", "utf8"));
    template.identity.account_ref = "synthetic-browser-account";
    template.broker_utc_offset_seconds = 0;
    const bridgeToken = randomBytes(32).toString("base64url");
    const authPath = join(temporary, "owner.json");
    const bridgePath = join(temporary, "bridge.json");
    await writeFile(authPath, JSON.stringify({ supabase_url: origin, public_key: local.ANON_KEY,
      owner_id: users[0].id }), { mode: 0o600, flag: "wx" });
    await writeFile(bridgePath, JSON.stringify({ identity: template.identity, token: bridgeToken,
      broker_utc_offset_seconds: 0 }), { mode: 0o600, flag: "wx" });
    // Bind port 0 in the child and keep that exact socket open: no port-selection race.
    api = spawn(join(root, ".venv/bin/python"), ["-c", [
      "import json,socket,uvicorn",
      "sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128)",
      "print(json.dumps({'port':sock.getsockname()[1]}),flush=True)",
      "uvicorn.run('sochron1k.main:app',fd=sock.fileno(),access_log=False,log_level='critical')",
    ].join("\n")], { cwd: root, stdio: ["ignore", "pipe", "ignore"], env: {
      ...process.env, PYTHONPATH: join(root, "services/api/src"),
      SOCHRON_OWNER_AUTH_CONFIG_FILE: authPath, SOCHRON_BRIDGE_CONFIG_FILE: bridgePath,
    } });
    const port = await new Promise((done, reject) => {
      let text = "";
      const timer = setTimeout(() => reject(new Error("API startup deadline")), 10000);
      api.once("error", reject);
      api.stdout.on("data", chunk => {
        text += chunk;
        if (text.includes("\n")) { clearTimeout(timer); done(JSON.parse(text.split("\n")[0]).port); }
      });
    });
    const apiOrigin = `http://127.0.0.1:${port}`;
    for (let attempt = 0; ; attempt++) {
      assert(attempt < 40 && api.exitCode === null);
      try { if ((await http(`${apiOrigin}/health`)).ok) break; } catch { /* bounded startup */ }
      await delay(100);
    }
    const bridgeHeaders = { Authorization: `Bearer ${bridgeToken}`, "Content-Type": "application/json" };
    const challenge = await http(`${apiOrigin}/bridge/v1/challenge`, { headers: bridgeHeaders });
    assert.equal(challenge.status, 200);
    template.boot_id = (await challenge.json()).boot_id;
    let sequence = 0;
    pumping = true;
    pump = (async () => {
      while (pumping) {
        if (feedEnabled) {
          const now = Date.now();
          const response = await http(`${apiOrigin}/bridge/v1/snapshot`, { method: "POST", headers: bridgeHeaders,
            body: JSON.stringify({ ...template, sequence: ++sequence, observed_at: new Date(now).toISOString(),
              tick_time_server_msc: now }) });
          assert.equal(response.status, 200);
        }
        await delay(400);
      }
    })().catch(() => { pumpFailure = true; pumping = false; });
    stage = "serve production build";
    web = await preview({ root: join(root, "apps/web"), configFile: false, logLevel: "silent",
      preview: { host: "127.0.0.1", port: 0, strictPort: true, proxy: {
        "/api": { target: apiOrigin, rewrite: path => path.replace(/^\/api/, "") },
      } } });
    const webOrigin = `http://127.0.0.1:${web.httpServer.address().port}`;
    stage = "launch isolated pinned Chromium";
    browser = await chromium.launch({ headless: true });
    browserVersion = browser.version();
    const browserManifest = JSON.parse(await readFile("node_modules/playwright-core/browsers.json", "utf8"));
    assert.equal(browserVersion, browserManifest.browsers.find(item => item.name === "chromium-headless-shell").browserVersion);
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, serviceWorkers: "block" });
    // Only these two guarded loopback destinations may receive browser requests.
    await context.route("**/*", route => [webOrigin, origin].includes(new URL(route.request().url()).origin)
      ? route.continue() : route.abort());
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    let pageErrors = 0;
    page.on("pageerror", () => pageErrors++);
    await page.clock.install({ time: Date.now() });
    await page.goto(webOrigin);
    await page.getByLabel("อีเมลเจ้าของ").waitFor();
    assert((await page.locator("body").ariaSnapshot()).includes("อีเมลเจ้าของ"));
    const panel = page.getByRole("region", { name: "บัญชี Demo ของคุณ" });
    const equity = panel.getByText(template.equity, { exact: true });
    const connected = panel.getByText("เชื่อมต่อแล้ว", { exact: true });
    async function login(user) {
      await page.getByLabel("อีเมลเจ้าของ").fill(user.email);
      await page.getByLabel("รหัสผ่าน", { exact: true }).fill(user.password);
      const signed = page.waitForResponse(response => response.request().method() === "POST"
        && response.url() === `${origin}/auth/v1/token?grant_type=password`);
      await page.getByRole("button", { name: "เข้าสู่ระบบ", exact: true }).click();
      const response = await signed;
      assert.equal(response.status(), 200);
      const token = (await response.json()).access_token;
      assert.equal(typeof token, "string");
      assert.equal(token.split(".").length, 3);
      return token;
    }
    async function logout() {
      await page.getByRole("button", { name: "ออกจากระบบ", exact: true }).click();
      await page.getByText("ออกจากระบบแล้ว", { exact: true }).waitFor();
      assert.equal(await equity.count(), 0);
    }
    stage = "foreign user denial";
    await login(users[1]);
    await page.getByText("บัญชีนี้ไม่มีสิทธิ์เจ้าของระบบ", { exact: true }).waitFor();
    assert.equal(await equity.count(), 0);
    await logout(); checks.push(stage);

    stage = "owner login and private telemetry";
    const originalToken = await login(users[0]);
    await connected.waitFor();
    assert.equal(await equity.count(), 2); // Equity and Balance share the explicit fixture value.
    assert(await panel.getByText(/Synthetic-Demo/).isVisible());
    assert(await page.getByText("DEMO ONLY", { exact: true }).isVisible());
    assert.equal(await page.getByRole("button", { name: /เปิดออเดอร์|ซื้อ|ขาย/ }).count(), 0);
    assert.equal(await page.locator('input[type="password"]').count(), 0);
    checks.push(stage);

    stage = "no persistent browser session";
    assert.deepEqual(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length })),
      { local: 0, session: 0 });
    assert.equal((await context.cookies()).length, 0);
    assert.equal(await page.evaluate(async () => (await indexedDB.databases()).length), 0);
    checks.push(stage);
    stage = "desktop and mobile layout";
    await page.screenshot({ path: join(output, "desktop-synthetic.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert(await panel.locator(".account-values dd").evaluateAll(values => values.length === 4 && values.every(value => {
      const range = document.createRange(); range.selectNodeContents(value);
      return range.getClientRects().length === 1 && value.scrollWidth <= value.clientWidth;
    })));
    await page.screenshot({ path: join(output, "mobile-synthetic.png"), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1000 });
    checks.push(stage);

    stage = "fresh to stale and recovery";
    feedEnabled = false;
    await panel.getByText("ข้อมูลเก่า — ห้ามใช้เป็นราคาปัจจุบัน", { exact: true }).waitFor();
    assert(await panel.getByText("Bid ล่าสุดที่บันทึก", { exact: true }).isVisible());
    feedEnabled = true;
    await connected.waitFor(); checks.push(stage);

    stage = "SDK refresh with accelerated browser clock";
    const refreshResponses = [];
    page.on("response", response => {
      if (response.url() === `${origin}/auth/v1/token?grant_type=refresh_token`
          && response.request().method() === "POST") {
        refreshDiagnostics.exchanges++;
        refreshResponses.push(response);
      }
    });
    const refreshed = page.waitForResponse(response => response.request().method() === "POST"
      && response.url() === `${origin}/auth/v1/token?grant_type=refresh_token`);
    await page.clock.fastForward(59 * 60 * 1000);
    stage = "SDK refresh HTTP response";
    const refreshResponse = await refreshed;
    assert.equal(refreshResponse.status(), 200);
    stage = "SDK refreshed token private read";
    await page.clock.setSystemTime(Date.now());
    // Advancing only the browser can cause another refresh before its clock is
    // restored. Verify the token actually used against real successful exchanges,
    // not against only the first response in a potentially rotated chain.
    const privateRead = await page.waitForResponse(async response => {
      if (response.url() !== `${webOrigin}/api/owner/telemetry` || response.status() !== 200) return false;
      const header = (await response.request().allHeaders()).authorization;
      if (!header || header === `Bearer ${originalToken}`) return false;
      for (const refreshedResponse of refreshResponses) {
        if (refreshedResponse.status() !== 200) continue;
        const access = (await refreshedResponse.json()).access_token;
        if (typeof access === "string" && access.split(".").length === 3 && header === `Bearer ${access}`) return true;
      }
      return false;
    });
    const freshToken = (await privateRead.request().allHeaders()).authorization.slice("Bearer ".length);
    refreshDiagnostics.used_refreshed_token = true;
    assert((await privateRead.json()).observation !== null);
    stage = "SDK refreshed telemetry visibility";
    await connected.waitFor(); checks.push("SDK refresh exchange and new-token private read");

    stage = "logout revokes unexpired browser token";
    await logout();
    const claims = JSON.parse(Buffer.from(freshToken.split(".")[1], "base64url").toString());
    assert(claims.exp > Date.now() / 1000);
    assert.equal((await http(`${apiOrigin}/owner/session`, { headers: { Authorization: `Bearer ${freshToken}` } })).status, 401);
    checks.push(stage);

    stage = "reload loses memory session";
    await login(users[0]); await connected.waitFor();
    await page.reload();
    await page.getByLabel("อีเมลเจ้าของ").waitFor();
    assert.equal(await equity.count(), 0);
    assert.equal(await page.getByRole("button", { name: "ออกจากระบบ", exact: true }).count(), 0);
    assert.equal(pageErrors, 0); assert(!pumpFailure);
    checks.push(stage);
  } catch { failureStage = stage; }
  finally {
    pumping = false;
    await pump;
    try { await browser?.close(); } catch { cleanupOK = false; }
    try { if (web) await new Promise((done, reject) => web.httpServer.close(error => error ? reject(error) : done())); }
    catch { cleanupOK = false; }
    try { await stopChild(api); } catch { cleanupOK = false; }
    for (const user of users) {
      try {
        const response = await http(`${origin}/auth/v1/admin/users/${user.id}`, { method: "DELETE", headers: admin });
        if (![200, 204].includes(response.status)) cleanupOK = false;
        const absent = await http(`${origin}/auth/v1/admin/users/${user.id}`, { headers: admin });
        if (absent.status !== 404) cleanupOK = false;
      } catch { cleanupOK = false; }
    }
    // Exact directory created by this invocation, containing only its generated configs.
    await rm(temporary, { recursive: true, force: true });
  }
  const sources = ["scripts/check-owner-browser.mjs", "scripts/supabase-local.sh", "package-lock.json", "uv.lock",
    "supabase/config.toml", "supabase/migrations/20260916224038_owner_session_validation.sql", "apps/web/src/OwnerPanel.tsx",
    "apps/web/src/styles.css",
    "apps/web/src/owner-api.ts", "apps/web/src/owner-auth.ts", "services/api/src/sochron1k/main.py",
    "services/api/src/sochron1k/owner_auth.py", "services/api/src/sochron1k/telemetry.py", "tests/fixtures/mt5-telemetry-v1.json"];
  const sha256 = {};
  for (const file of sources) sha256[file] = createHash("sha256").update(await readFile(file)).digest("hex");
  const result = { result: failureStage || !cleanupOK || creationUnresolved ? "FAIL" : "PASS", failure_stage: failureStage,
    cleanup: creationUnresolved ? "UNKNOWN" : cleanupOK ? "PASS" : "FAIL",
    revision, dirty: Boolean(command("git", ["status", "--porcelain"])),
    checked_at: new Date().toISOString(), node: process.version, playwright: "1.63.0", chromium: browserVersion,
    python: command(join(root, ".venv/bin/python"), ["--version"]), runtime_images: runtimeImages.sort(),
    production_build_sha256: buildSha256, refresh_diagnostics: refreshDiagnostics,
    checks, sha256, fixture: "synthetic telemetry; two generated local Auth users",
    token_refresh: "accelerated browser clock; real refresh-token HTTP exchange; server clock unchanged",
    mt5: "NOT_RUN", hosted_supabase: "NOT_RUN", artifacts: output };
  await writeFile(join(output, "result.json"), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
  if (result.result !== "PASS") process.exitCode = 1;
}
run().catch(() => {
  console.log(JSON.stringify({ result: "FAIL", failure_stage: stage, details: "suppressed to protect credentials" }));
  process.exitCode = 1;
});
