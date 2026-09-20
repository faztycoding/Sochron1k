#!/usr/bin/env node
// SCN-005/006/007/014/015/016/032/033/034/035: browser/Auth/read models and local alert/budget/delivery evidence; no broker operations.
import assert from "node:assert/strict";
import { spawn, execFileSync } from "node:child_process";
import { createHash, randomBytes, randomUUID } from "node:crypto";
import { mkdtemp, mkdir, readdir, readFile, realpath, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
process.chdir(root);
let stage = "prerequisites";
const checks = [];
function command(executable, args, extraEnv = {}) {
  return execFileSync(executable, args, { cwd: root, encoding: "utf8", timeout: 30000,
    env: { ...process.env, ...extraEnv },
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
  const temporary = await realpath(await mkdtemp(join(tmpdir(), "sochron-browser-")));
  const users = [];
  const issuedTokens = []; // Memory only; revoke generated sessions before deleting test users.
  const signalFixtures = [];
  const evaluationFixtures = [];
  let api;
  let web;
  let browser;
  let pump;
  let pumping = false;
  let feedEnabled = true;
  let chartEnabled = true;
  let pumpFailure = false;
  let cleanupOK = true;
  let creationUnresolved = false;
  let browserVersion;
  let failureStage = null;
  let failureType = null;
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
    const chartPath = join(temporary, "chart.json");
    const executionPath = join(temporary, "execution.sqlite3");
    const alertLifecycleDir = join(temporary, "alert-lifecycle");
    const alertDeliveryStatusDir = join(temporary, "alert-delivery-status");
    const apiBudgetConfigPath = join(temporary, "api-budget-config.json");
    const apiBudgetSnapshotPath = join(temporary, "api-budget-snapshot.json");
    await mkdir(alertLifecycleDir, { mode: 0o700 });
    await mkdir(alertDeliveryStatusDir, { mode: 0o700 });
    const fixtureEpoch = Math.floor(Date.now() / 1000);
    async function insertFixture(table, body) {
      const response = await http(`${origin}/rest/v1/${table}?select=id`, { method: "POST",
        headers: { ...admin, "Content-Type": "application/json", Prefer: "return=representation" },
        body: JSON.stringify(body) });
      assert.equal(response.status, 201);
      const rows = await response.json();
      assert.equal(rows.length, 1); assert(Number.isSafeInteger(rows[0].id));
      return rows[0].id;
    }
    stage = "seed isolated owner-RLS signal and evaluation evidence";
    for (let index = 0; index < users.length; index++) {
      const unique = randomUUID();
      const confirmed = new Date((fixtureEpoch - 60) * 1000);
      const strategyId = await insertFixture("strategy_versions", { owner_id: users[index].id,
        version_id: `browser-pa01-${unique}`, code_hash: createHash("sha256").update(`strategy-${unique}`).digest("hex"),
        parameters: {}, status: "active", data_cutoff: new Date((fixtureEpoch - 600) * 1000).toISOString() });
      const accountId = await insertFixture("accounts", { owner_id: users[index].id,
        account_ref: `browser-account-${unique}`, server_ref: "Synthetic-Demo", account_mode: "demo",
        currency: "USD", initial_equity: "100000", policy_version: "risk-v1.1" });
      const experimentId = await insertFixture("experiments", { owner_id: users[index].id,
        account_id: accountId, strategy_version_id: strategyId, experiment_id: `browser-experiment-${unique}`,
        status: "demo", initial_equity: "100000", policy_version: "risk-v1.1" });
      const signalId = `browser-signal-${index}-${unique}`;
      await insertFixture("signals", { owner_id: users[index].id, experiment_id: experimentId,
        strategy_version_id: strategyId, signal_id: signalId, setup_id: `browser-setup-${unique}`,
        action: "buy", formed_at: new Date((fixtureEpoch - 300) * 1000).toISOString(),
        confirmed_at: confirmed.toISOString(), expires_at: new Date((fixtureEpoch + 300) * 1000).toISOString(),
        evidence_ids: [`browser-feature-${unique}`] });
      signalFixtures.push({ owner_id: users[index].id, signal_id: signalId });
      const datasetHash = createHash("sha256").update(`dataset-${unique}`).digest("hex");
      await insertFixture("evaluations", { owner_id: users[index].id, strategy_version_id: strategyId,
        experiment_id: experimentId, dataset_hash: datasetHash, split: "walk_forward",
        metrics: { sample_size: 40, wins: 18, losses: 20, breakeven: 2, net_return_pct: 7.25,
          expectancy_r: 0.18, expectancy_r_ci95_low: 0.03, expectancy_r_ci95_high: 0.33,
          max_drawdown_pct: 3.5, profit_factor: 1.24 },
        cost_assumptions: { spread_points: 18, slippage_points: 3, commission_per_lot: 7,
          swap_included: true, operating_cost_per_trade: 0.12, currency: "USD" },
        data_cutoff: new Date((fixtureEpoch - 60) * 1000).toISOString(),
        created_at: new Date((fixtureEpoch - 30) * 1000).toISOString() });
      evaluationFixtures.push({ owner_id: users[index].id, dataset_hash: datasetHash,
        version_id: `browser-pa01-${unique}` });
    }
    await writeFile(chartPath, JSON.stringify({ offset_valid_from_server_s: fixtureEpoch - 10 * 86400,
      offset_valid_until_server_s: fixtureEpoch + 86400 }), { mode: 0o600, flag: "wx" });
    await writeFile(authPath, JSON.stringify({ supabase_url: origin, public_key: local.ANON_KEY,
      owner_id: users[0].id }), { mode: 0o600, flag: "wx" });
    await writeFile(bridgePath, JSON.stringify({ identity: template.identity, token: bridgeToken,
      broker_utc_offset_seconds: 0 }), { mode: 0o600, flag: "wx" });
    const budgetObserved = new Date(Date.now() - 1000);
    const budgetPeriodStart = new Date(Date.UTC(budgetObserved.getUTCFullYear(), budgetObserved.getUTCMonth(), 1));
    const budgetPeriodEnd = new Date(Date.UTC(budgetObserved.getUTCFullYear(), budgetObserved.getUTCMonth() + 1, 1));
    await writeFile(apiBudgetSnapshotPath, JSON.stringify({ protocol: "sochron.api-budget-snapshot.v1",
      source_id: "synthetic-browser-provider", revision: "browser-cost-fixture-1",
      period_start_utc: budgetPeriodStart.toISOString(), period_end_utc: budgetPeriodEnd.toISOString(),
      observed_at_utc: budgetObserved.toISOString(),
      coverage_until_utc: new Date(budgetObserved.getTime() - 1000).toISOString(), currency: "USD",
      billed_cost: "65.00", unbilled_estimate: "5.00" }), { mode: 0o600, flag: "wx" });
    await writeFile(apiBudgetConfigPath, JSON.stringify({ enabled: true,
      snapshot_file: apiBudgetSnapshotPath, currency: "USD", monthly_limit: "100.00",
      warning_fraction: "0.70", critical_fraction: "0.85", stale_after_seconds: 3600 }),
    { mode: 0o600, flag: "wx" });
    const deliveryUpdated = new Date();
    await writeFile(join(alertDeliveryStatusDir, "delivery-status.json"), JSON.stringify({
      protocol: "sochron.alert-delivery-status.v1", state: "connected",
      destination_ref: "synthetic-owner-relay", updated_at_utc: deliveryUpdated.toISOString(),
      heartbeat_expires_at_utc: new Date(deliveryUpdated.getTime() + 600000).toISOString(),
      pending_deliveries: 0, unknown_deliveries: 0, verified_deliveries: 1,
      quarantined_deliveries: 0, last_delivery_ref: "a".repeat(32),
      last_verified_at_utc: new Date(deliveryUpdated.getTime() - 1000).toISOString(),
    }), { mode: 0o600, flag: "wx" });
    const seeded = JSON.parse(command(join(root, ".venv/bin/python"),
      ["tests/fixtures/execution_evidence_seed.py", executionPath],
      { PYTHONPATH: join(root, "services/api/src") }));
    assert.deepEqual(seeded, { result: "PASS", commands: 1, execution_ready: false });
    // Bind port 0 in the child and keep that exact socket open: no port-selection race.
    const launchApi = (bindPort = 0) => spawn(join(root, ".venv/bin/python"), ["-c", [
      "import json,socket,uvicorn",
      `sock=socket.socket();sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',${bindPort}));sock.listen(128)`,
      "print(json.dumps({'port':sock.getsockname()[1]}),flush=True)",
      "uvicorn.run('sochron1k.main:app',fd=sock.fileno(),access_log=False,log_level='critical')",
    ].join("\n")], { cwd: root, stdio: ["ignore", "pipe", "ignore"], env: {
      ...process.env, PYTHONPATH: join(root, "services/api/src"),
      SOCHRON_OWNER_AUTH_CONFIG_FILE: authPath, SOCHRON_BRIDGE_CONFIG_FILE: bridgePath,
      SOCHRON_CHART_CONFIG_FILE: chartPath, SOCHRON_CHART_HISTORY_DIR: temporary,
      SOCHRON_EXECUTION_JOURNAL_PATH: executionPath,
      SOCHRON_ALERT_LIFECYCLE_DIR: alertLifecycleDir,
      SOCHRON_API_BUDGET_CONFIG_FILE: apiBudgetConfigPath,
      SOCHRON_ALERT_DELIVERY_STATUS_DIR: alertDeliveryStatusDir,
    } });
    api = launchApi();
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
    let chartSequence = 0;
    const periods = { M1: 60, M5: 300, M15: 900, H1: 3600 };
    const gapTimes = Object.fromEntries(Object.entries(periods).map(([key, period]) => [key, Math.floor(fixtureEpoch / period) * period - period * 8]));
    async function sendChart(timeframe, now) {
      const period = periods[timeframe], last = Math.floor(now / 1000 / period) * period;
      const bars = Array.from({ length: 120 }, (_, index) => {
        const start = last - period * (119 - index), price = 2500 + (Math.floor(start / period) % 37) / 10;
        return { time_server_s: start, open: price.toFixed(2), high: (price + 0.9).toFixed(2),
          low: (price - 0.4).toFixed(2), close: (price + (index % 2 ? 0.2 : -0.2)).toFixed(2), tick_volume: 50, spread_points: 20 };
      }).filter(bar => bar.time_server_s !== gapTimes[timeframe]);
      // Prices and direction depend on absolute bar time, not a shifting array index.
      for (const bar of bars) bar.close = (Number(bar.open) + (Math.floor(bar.time_server_s / period) % 2 ? 0.2 : -0.2)).toFixed(2);
      const response = await http(`${apiOrigin}/bridge/v1/chart/snapshot`, { method: "POST", headers: bridgeHeaders,
        body: JSON.stringify({ protocol: "sochron.chart.v1", source: "mt5-copyrates", boot_id: template.boot_id,
          sequence: ++chartSequence, identity: template.identity, trade_mode: "demo", terminal_build: template.terminal_build,
          observed_at: new Date(now).toISOString(), broker_utc_offset_seconds: 0, timeframe, price_basis: "bid",
          digits: template.contract.digits, tick_size: template.contract.tick_size, bars }) });
      assert.equal(response.status, 200);
    }
    pumping = true;
    pump = (async () => {
      while (pumping) {
        if (feedEnabled) {
          const now = Date.now();
          const response = await http(`${apiOrigin}/bridge/v1/snapshot`, { method: "POST", headers: bridgeHeaders,
            body: JSON.stringify({ ...template, sequence: ++sequence, observed_at: new Date(now).toISOString(),
              tick_time_server_msc: now }) });
          assert.equal(response.status, 200);
          if (chartEnabled) for (const timeframe of Object.keys(periods)) await sendChart(timeframe, Date.now());
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
    stage = "redacted API connection map";
    const connectionMap = page.getByRole("region", { name: "แผนที่การเชื่อมต่อ API" });
    await connectionMap.getByText("/api/owner/telemetry", { exact: true }).waitFor();
    assert(await connectionMap.getByText("/api/owner/execution", { exact: true }).isVisible());
    assert(await connectionMap.getByText("/api/owner/alerts", { exact: true }).isVisible());
    assert(await connectionMap.getByText("/api/owner/alerts/{condition_id}/acknowledge", { exact: true }).isVisible());
    assert(await connectionMap.getByText("/api/owner/alerts/{condition_id}/resolve", { exact: true }).isVisible());
    assert(await connectionMap.getByText("/api/owner/signals", { exact: true }).isVisible());
    assert(await connectionMap.getByText("/api/owner/statistics", { exact: true }).isVisible());
    assert(await connectionMap.getByText("/api/ui/demo-readiness", { exact: true }).isVisible());
    const mapResponse = await http(`${apiOrigin}/ui/connections`);
    assert.equal(mapResponse.status, 200);
    assert.equal(mapResponse.headers.get("cache-control"), "no-store");
    const mapBody = await mapResponse.json();
    assert.equal(mapBody.demo_only, true);
    assert.equal(mapBody.auto_trading_enabled, false);
    assert.equal(mapBody.execution_ready, false);
    assert.deepEqual(mapBody.connections.map(item => item.id), ["core_api", "demo_readiness", "owner_auth",
      "market_telemetry", "native_chart", "bar_history", "execution_evidence", "operational_alerts",
      "signals", "statistics"]);
    const readiness = page.getByRole("region", { name: "สิ่งที่ต้องครบก่อนใช้งานเดโม่" });
    await readiness.getByText("Demo broker round trip", { exact: true }).waitFor();
    assert(await readiness.getByText("EA build บนเป้าหมาย", { exact: true }).isVisible());
    const readinessResponse = await http(`${apiOrigin}/ui/demo-readiness`);
    assert.equal(readinessResponse.status, 200);
    assert.equal(readinessResponse.headers.get("cache-control"), "no-store");
    const readinessBody = await readinessResponse.json();
    assert.equal(readinessBody.demo_only, true);
    assert.equal(readinessBody.auto_trading_enabled, false);
    assert.equal(readinessBody.release_ready, false);
    assert.equal(readinessBody.round_trip_authorized, false);
    assert.equal(readinessBody.unattended_demo_ready, false);
    assert.deepEqual(readinessBody.gates.map(item => item.id), ["owner_decisions", "owner_auth",
      "market_data", "execution_bridge", "policy_research", "target_artifact", "broker_round_trip",
      "recovery_observability", "operational_authorization"]);
    checks.push(stage);
    await page.getByLabel("อีเมลเจ้าของ").waitFor();
    assert((await page.locator("body").ariaSnapshot()).includes("อีเมลเจ้าของ"));
    const panel = page.getByRole("region", { name: "บัญชี Demo ของคุณ" });
    const equity = panel.getByText(template.equity, { exact: true });
    const connected = panel.getByText("เชื่อมต่อแล้ว", { exact: true });
    const chart = page.locator("#market-chart");
    const history = page.locator("#bar-history");
    const signals = page.locator("#signal-evidence");
    const statistics = page.locator("#research-statistics");
    const execution = page.locator("#execution-evidence");
    const alerts = page.locator("#operational-alerts");
    assert.equal(await alerts.locator(".alert-coverage-row").count(), 8);
    assert(await alerts.getByText("api_budget", { exact: true }).isVisible());
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
      issuedTokens.push(token);
      return token;
    }
    async function logout() {
      await page.getByRole("button", { name: "ออกจากระบบ", exact: true }).click();
      await page.getByText("ออกจากระบบแล้ว", { exact: true }).waitFor();
      assert.equal(await equity.count(), 0);
      assert.equal(await chart.locator("canvas").count(), 0);
      assert.equal(await history.locator("tbody tr").count(), 0);
      assert.equal(await signals.getByText(signalFixtures[0].signal_id, { exact: true }).count(), 0);
      assert.equal(await statistics.getByText(evaluationFixtures[0].version_id, { exact: true }).count(), 0);
      assert.equal(await execution.getByText("browser-command-confirmed", { exact: true }).count(), 0);
      assert.equal(await alerts.locator(".active-alerts").count(), 0);
    }
    stage = "foreign user denial";
    const foreignToken = await login(users[1]);
    await page.getByText("บัญชีนี้ไม่มีสิทธิ์เจ้าของระบบ", { exact: true }).waitFor();
    assert.equal(await equity.count(), 0);
    assert.equal((await http(`${apiOrigin}/owner/chart/M5`, { headers: { Authorization: `Bearer ${foreignToken}` } })).status, 403);
    assert.equal((await http(`${apiOrigin}/owner/history/M5`, { headers: { Authorization: `Bearer ${foreignToken}` } })).status, 403);
    assert.equal((await http(`${apiOrigin}/owner/execution`, { headers: { Authorization: `Bearer ${foreignToken}` } })).status, 403);
    assert.equal((await http(`${apiOrigin}/owner/alerts`, { headers: { Authorization: `Bearer ${foreignToken}` } })).status, 403);
    assert.equal((await http(`${apiOrigin}/owner/api-budget`, { headers: { Authorization: `Bearer ${foreignToken}` } })).status, 403);
    assert.equal((await http(`${apiOrigin}/owner/alerts/${"a".repeat(24)}/acknowledge`, {
      method: "POST", headers: { Authorization: `Bearer ${foreignToken}`, "Idempotency-Key": randomUUID() },
    })).status, 403);
    assert.equal((await http(`${apiOrigin}/owner/signals`, { headers: { Authorization: `Bearer ${foreignToken}` } })).status, 403);
    assert.equal((await http(`${apiOrigin}/owner/statistics`, { headers: { Authorization: `Bearer ${foreignToken}` } })).status, 403);
    const foreignRows = await (await http(`${origin}/rest/v1/signals?select=signal_id`, {
      headers: { apikey: local.ANON_KEY, Authorization: `Bearer ${foreignToken}` },
    })).json();
    assert.deepEqual(foreignRows, [{ signal_id: signalFixtures[1].signal_id }]);
    const foreignEvaluations = await (await http(`${origin}/rest/v1/evaluations?select=dataset_hash`, {
      headers: { apikey: local.ANON_KEY, Authorization: `Bearer ${foreignToken}` },
    })).json();
    assert.deepEqual(foreignEvaluations, [{ dataset_hash: evaluationFixtures[1].dataset_hash }]);
    await logout(); checks.push(stage);

    stage = "owner login and private telemetry";
    const originalToken = await login(users[0]);
    await connected.waitFor();
    assert.equal(await equity.count(), 2); // Equity and Balance share the explicit fixture value.
    assert(await panel.getByText(/Synthetic-Demo/).isVisible());
    assert(await page.getByText("DEMO ONLY", { exact: true }).isVisible());
    assert.equal(await page.getByRole("button", { name: /เปิดออเดอร์|ซื้อ|ขาย/ }).count(), 0);
    assert.equal(await page.locator('input[type="password"]').count(), 0);
    await alerts.getByText("1 รายการ · journal connected", { exact: true }).waitFor();
    assert(await alerts.getByText("70.00 / 100.00 USD", { exact: true }).isVisible());
    assert(await alerts.getByText("ถึงระดับเตือน", { exact: true }).isVisible());
    const alertResponse = await http(`${apiOrigin}/owner/alerts`, {
      headers: { Authorization: `Bearer ${originalToken}` },
    });
    assert.equal(alertResponse.status, 200);
    assert.equal(alertResponse.headers.get("cache-control"), "no-store");
    const alertBody = await alertResponse.json();
    assert.equal(alertBody.protocol, "sochron.operational-alerts.v4");
    assert.equal(alertBody.trading_mode, "demo");
    assert.equal(alertBody.read_only, true);
    assert.equal(alertBody.auto_trading_enabled, false);
    assert.equal(alertBody.execution_ready, false);
    assert.equal(alertBody.delivery_configured, true);
    assert.equal(alertBody.delivery.state, "connected");
    assert.equal(alertBody.delivery.destination_ref, "synthetic-owner-relay");
    assert.equal(alertBody.delivery.verified_deliveries, 1);
    assert(!JSON.stringify(alertBody.delivery).includes(alertDeliveryStatusDir));
    assert.equal(alertBody.lifecycle_runtime, "connected");
    assert.equal(alertBody.lifecycle_mutations_enabled, true);
    assert.equal(alertBody.api_budget.state, "warning");
    assert.equal(alertBody.api_budget.evidence.total_cost, "70.00");
    assert.equal(alertBody.alerts.length, 1);
    assert.equal(alertBody.alerts[0].kind, "api_budget");
    assert.equal(alertBody.alerts[0].detail_code, "api_budget_warning");
    assert.deepEqual(alertBody.coverage.map(item => item.kind), ["order_reject", "no_sl", "risk_halt",
      "unknown_execution", "stale_price", "bridge_disconnected", "storage_limit", "api_budget"]);
    assert.deepEqual(alertBody.coverage.at(-1), { kind: "api_budget", implementation: "available",
      runtime: "connected", api_routes: ["/api/owner/alerts", "/api/owner/api-budget"], sources: ["api_budget"] });
    const budgetResponse = await http(`${apiOrigin}/owner/api-budget`, {
      headers: { Authorization: `Bearer ${originalToken}` },
    });
    assert.equal(budgetResponse.status, 200);
    assert.equal(budgetResponse.headers.get("cache-control"), "no-store");
    const budgetBody = await budgetResponse.json();
    assert.equal(budgetBody.state, "warning");
    assert(!JSON.stringify(budgetBody).includes("synthetic-browser-provider"));
    assert(!JSON.stringify(budgetBody).includes(apiBudgetSnapshotPath));
    assert(await alerts.getByText("synthetic-owner-relay", { exact: true }).isVisible());
    assert(await alerts.getByText("1 รายการ", { exact: true }).isVisible());
    checks.push("owner operational alerts, lifecycle, delivery status and provider-neutral API budget evidence");
    await signals.getByText(signalFixtures[0].signal_id, { exact: true }).waitFor();
    assert(await signals.getByText("BUY", { exact: true }).isVisible());
    assert(await signals.getByText("ยังอยู่ในอายุสัญญาณ", { exact: true }).isVisible());
    assert(await signals.getByText(/browser-pa01-/).isVisible());
    assert(await page.evaluate(() => {
      const chartNode = document.querySelector("#market-chart");
      const signalNode = document.querySelector("#signal-evidence");
      const statisticsNode = document.querySelector("#research-statistics");
      const historyNode = document.querySelector("#bar-history");
      return Boolean(chartNode && signalNode && statisticsNode && historyNode &&
        chartNode.compareDocumentPosition(signalNode) & Node.DOCUMENT_POSITION_FOLLOWING &&
        signalNode.compareDocumentPosition(statisticsNode) & Node.DOCUMENT_POSITION_FOLLOWING &&
        statisticsNode.compareDocumentPosition(historyNode) & Node.DOCUMENT_POSITION_FOLLOWING);
    }));
    const signalResponse = await http(`${apiOrigin}/owner/signals`, {
      headers: { Authorization: `Bearer ${originalToken}` },
    });
    assert.equal(signalResponse.status, 200);
    const signalBody = await signalResponse.json();
    assert.equal(signalBody.status.state, "available");
    assert.deepEqual(signalBody.signals.map(item => item.signal_id), [signalFixtures[0].signal_id]);
    assert(!JSON.stringify(signalBody).includes(users[0].id));
    const ownerRows = await (await http(`${origin}/rest/v1/signals?select=signal_id`, {
      headers: { apikey: local.ANON_KEY, Authorization: `Bearer ${originalToken}` },
    })).json();
    assert.deepEqual(ownerRows, [{ signal_id: signalFixtures[0].signal_id }]);
    checks.push("owner signal RLS evidence, causal projection and UI placement");
    await statistics.getByText(evaluationFixtures[0].version_id, { exact: true }).waitFor();
    assert(await statistics.getByText("Walk-forward", { exact: true }).isVisible());
    assert(await statistics.getByText("n = 40", { exact: true }).isVisible());
    assert(await statistics.getByText("45.0000%", { exact: true }).isVisible());
    assert(await statistics.getByText("Spread 18 points", { exact: true }).isVisible());
    const statisticsResponse = await http(`${apiOrigin}/owner/statistics`, {
      headers: { Authorization: `Bearer ${originalToken}` },
    });
    assert.equal(statisticsResponse.status, 200);
    const statisticsBody = await statisticsResponse.json();
    assert.equal(statisticsBody.status.state, "available");
    assert.equal(statisticsBody.status.promotion_decided, false);
    assert.deepEqual(statisticsBody.evaluations.map(item => item.dataset_hash), [evaluationFixtures[0].dataset_hash]);
    assert(!JSON.stringify(statisticsBody).includes(users[0].id));
    const ownerEvaluations = await (await http(`${origin}/rest/v1/evaluations?select=dataset_hash`, {
      headers: { apikey: local.ANON_KEY, Authorization: `Bearer ${originalToken}` },
    })).json();
    assert.deepEqual(ownerEvaluations, [{ dataset_hash: evaluationFixtures[0].dataset_hash }]);
    checks.push("owner research evaluation RLS, costs, uncertainty and UI placement");
    await execution.getByText("browser-command-confirmed", { exact: true }).waitFor();
    assert(await execution.getByText("MT5 ยืนยันแล้ว", { exact: true }).isVisible());
    assert(await execution.getByText(/Deal: browser-deal-confirmed/).isVisible());
    const executionResponse = await http(`${apiOrigin}/owner/execution`, {
      headers: { Authorization: `Bearer ${originalToken}` },
    });
    assert.equal(executionResponse.status, 200);
    const executionBody = await executionResponse.json();
    assert.equal(executionBody.status.state, "available");
    assert.equal(executionBody.commands[0].command_id, "browser-command-confirmed");
    assert.equal(executionBody.commands[0].order.stop_loss_confirmed, true);
    checks.push("owner execution journal evidence and confirmed SL projection");
    checks.push(stage);

    stage = "native chart rendering and keyboard timeframe selection";
    await chart.getByLabel("ตรวจค่าแท่งเทียน (UTC)").waitFor();
    await chart.locator("canvas").first().waitFor();
    assert(await chart.getByText("ยังไม่ยืนยันปิด — ค่านี้ยังเปลี่ยนได้", { exact: true }).isVisible());
    assert(await chart.getByText(/มีช่วงข้อมูลขาด 1 ช่วง/).isVisible());
    for (const timeframe of ["M1", "M15", "H1", "M5"]) {
      const button = chart.getByRole("button", { name: timeframe, exact: true });
      await button.focus(); await page.keyboard.press("Enter");
      await chart.getByRole("img", { name: `กราฟแท่งเทียน ${timeframe} เวลา UTC; ค่า OHLC แบบข้อความอยู่ด้านล่าง`, exact: true }).waitFor();
      assert.equal(await button.getAttribute("aria-pressed"), "true");
    }
    await chart.getByLabel("ตรวจค่าแท่งเทียน (UTC)").selectOption({ index: 0 });
    assert(await chart.getByText("แท่งปิดแล้ว — มีแท่งถัดไปยืนยัน", { exact: true }).isVisible());
    assert(await chart.locator(".chart-values dd").evaluateAll(values => values.length === 4 && values.every(value => /^\d+\.\d{2}$/.test(value.textContent))));
    const inspectedTime = await chart.getByLabel("ตรวจค่าแท่งเทียน (UTC)").inputValue();
    const chartRead = await http(`${apiOrigin}/owner/chart/M5`, { headers: { Authorization: `Bearer ${originalToken}` } });
    assert.equal(chartRead.status, 200); assert.equal(chartRead.headers.get("cache-control"), "no-store");
    const inspectedBar = (await chartRead.json()).observation.bars.find(bar => bar.open_time_utc === inspectedTime);
    assert(inspectedBar);
    assert.deepEqual(await chart.locator(".chart-values dd").allTextContents(), [inspectedBar.open, inspectedBar.high, inspectedBar.low, inspectedBar.close]);
    assert.equal((await http(`${webOrigin}/chart-notice.txt`)).status, 200);
    assert.equal((await http(`${webOrigin}/lightweight-charts-LICENSE.txt`)).status, 200);
    checks.push(stage);

    stage = "durable history exact values, pinned paging and keyboard timeframes";
    await history.locator("tbody tr").first().waitFor();
    assert.equal(await history.locator("tbody tr").count(), 20);
    const historyRequests = [];
    page.on("request", request => { if (request.url().includes("/api/owner/history/")) historyRequests.push(new URL(request.url())); });
    async function historyAction(action) {
      const response = page.waitForResponse(response => response.url().includes("/api/owner/history/") && response.status() === 200);
      await action();
      const data = await (await response).json();
      await history.getByText(`ชุดข้อมูลถึง receipt ${data.through_receipt} · ไม่มีการเพิ่มแท่งใหม่ระหว่างเปลี่ยนหน้า`, { exact: true }).waitFor();
      if (data.bars.length) await history.getByRole("button", { name: `ดูหลักฐาน ${data.bars[0].open_time_utc}`, exact: true }).waitFor();
      return data;
    }
    const initialHistory = await historyAction(() => history.getByRole("button", { name: "อ่านชุดล่าสุด", exact: true }).click());
    assert.equal(initialHistory.bars.length, 20);
    assert.deepEqual(await history.locator("tbody tr").first().locator("td").allTextContents(),
      [initialHistory.bars[0].open, initialHistory.bars[0].high, initialHistory.bars[0].low, initialHistory.bars[0].close, String(initialHistory.bars[0].tick_volume)]);
    const secondPage = await historyAction(() => history.getByRole("button", { name: "หน้าถัดไป", exact: true }).click());
    assert.equal(secondPage.archive_id, initialHistory.archive_id);
    assert.equal(secondPage.through_receipt, initialHistory.through_receipt);
    assert(secondPage.bars[0].time_server_s > initialHistory.bars.at(-1).time_server_s);
    assert.equal(historyRequests.at(-1).searchParams.get("through_receipt"), String(initialHistory.through_receipt));
    assert.equal(historyRequests.at(-1).searchParams.get("archive_id"), initialHistory.archive_id);
    const previousPage = await historyAction(() => history.getByRole("button", { name: "หน้าก่อน", exact: true }).click());
    assert.deepEqual(previousPage.bars, initialHistory.bars);
    let endPage = previousPage;
    for (let index = 0; index < 6 && endPage.bars.length === 20; index++) {
      endPage = await historyAction(() => history.getByRole("button", { name: "หน้าถัดไป", exact: true }).click());
      assert.equal(endPage.through_receipt, initialHistory.through_receipt);
    }
    assert(endPage.bars.length < 20 && endPage.gaps.length === 1);
    assert(await history.getByText("ข้อมูลขาด 1 ช่วง — ยังไม่ทราบสาเหตุ", { exact: true }).isVisible());
    for (const timeframe of ["M1", "M15", "H1", "M5"]) {
      const button = history.getByRole("button", { name: timeframe, exact: true });
      const data = await historyAction(async () => { await button.focus(); await page.keyboard.press("Enter"); });
      assert.equal(data.timeframe, timeframe); assert.equal(await button.getAttribute("aria-pressed"), "true");
      assert.equal(historyRequests.at(-1).searchParams.has("through_receipt"), false);
    }
    checks.push(stage);

    stage = "history network failure clears rows and deliberate retry recovers";
    await page.route("**/api/owner/history/**", route => route.abort());
    await history.getByRole("button", { name: "หน้าถัดไป", exact: true }).click();
    await history.getByRole("alert").waitFor();
    assert.equal(await history.locator("tbody tr").count(), 0);
    await page.unroute("**/api/owner/history/**");
    await historyAction(() => history.getByRole("button", { name: "ลองอ่านหน้าเดิมอีกครั้ง", exact: true }).click());
    assert.equal(await history.locator("tbody tr").count(), 20);
    checks.push(stage);

    stage = "durable alert acknowledgement and guarded resolution";
    feedEnabled = false;
    await panel.getByText("ข้อมูลเก่า — ห้ามใช้เป็นราคาปัจจุบัน", { exact: true }).waitFor();
    const staleAlert = alerts.locator("li.active-alert").filter({ hasText: "ราคาหรือ heartbeat เก่า" });
    await staleAlert.getByRole("button", { name: "รับทราบ", exact: true }).waitFor({ timeout: 15000 });
    await staleAlert.getByRole("button", { name: "รับทราบ", exact: true }).click();
    await staleAlert.getByText("รับทราบแล้ว · เหตุยัง active", { exact: true }).waitFor();
    assert.equal(await staleAlert.getByRole("button", { name: "ปิด workflow", exact: true }).count(), 0);
    let lifecycleBody = await (await http(`${apiOrigin}/owner/alerts`, {
      headers: { Authorization: `Bearer ${originalToken}` },
    })).json();
    let lifecycleAlert = lifecycleBody.alerts.find(item => item.kind === "stale_price");
    assert.equal(lifecycleAlert.lifecycle_state, "acknowledged");
    assert.equal(lifecycleAlert.acknowledged_by, "owner");
    assert.equal(lifecycleAlert.resolved_at_utc, null);
    feedEnabled = true;
    await connected.waitFor();
    await staleAlert.getByRole("button", { name: "ปิด workflow", exact: true }).waitFor({ timeout: 15000 });
    await staleAlert.getByRole("button", { name: "ปิด workflow", exact: true }).click();
    await staleAlert.getByText("ปิด workflow แล้ว", { exact: true }).waitFor();
    lifecycleBody = await (await http(`${apiOrigin}/owner/alerts`, {
      headers: { Authorization: `Bearer ${originalToken}` },
    })).json();
    lifecycleAlert = lifecycleBody.alerts.find(item => item.kind === "stale_price");
    assert.equal(lifecycleAlert.lifecycle_state, "resolved");
    assert.match(lifecycleAlert.resolved_at_utc, /(Z|\+00:00)$/);
    assert.equal(lifecycleBody.delivery_configured, true);
    checks.push(stage);

    stage = "no persistent browser session";
    assert.deepEqual(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length })),
      { local: 0, session: 0 });
    assert.equal((await context.cookies()).length, 0);
    assert.equal(await page.evaluate(async () => (await indexedDB.databases()).length), 0);
    checks.push(stage);
    stage = "desktop and mobile layout";
    await page.screenshot({ path: join(output, "desktop-synthetic.png"), fullPage: true });
    await history.screenshot({ path: join(output, "history-desktop-synthetic.png") });
    await page.setViewportSize({ width: 390, height: 844 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert(await panel.locator(".account-values dd").evaluateAll(values => values.length === 4 && values.every(value => {
      const range = document.createRange(); range.selectNodeContents(value);
      return range.getClientRects().length === 1 && value.scrollWidth <= value.clientWidth;
    })));
    assert(await chart.locator(".chart-values dd").evaluateAll(values => values.length === 4 && values.every(value => value.scrollWidth <= value.clientWidth)));
    assert(await connectionMap.locator(".connection-row").evaluateAll(rows => rows.length === 10 && rows.every(row => row.scrollWidth <= row.clientWidth)));
    assert(await readiness.locator(".readiness-row").evaluateAll(rows => rows.length === 9 && rows.every(row => row.scrollWidth <= row.clientWidth)));
    assert(await alerts.locator(".alert-coverage-row").evaluateAll(rows => rows.length === 8 && rows.every(row => row.scrollWidth <= row.clientWidth)));
    assert(await alerts.locator(".budget-ledger").evaluate(element => element.scrollWidth <= element.clientWidth));
    assert(await alerts.locator(".delivery-ledger").evaluate(element => element.scrollWidth <= element.clientWidth));
    await page.screenshot({ path: join(output, "mobile-synthetic.png"), fullPage: true });
    assert(await history.locator(".history-table-scroll").evaluate(element => element.scrollWidth > element.clientWidth));
    await history.screenshot({ path: join(output, "history-mobile-synthetic.png") });
    stage = "320px page containment and keyboard table scrolling";
    await page.setViewportSize({ width: 320, height: 740 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert(await alerts.evaluate(element => element.scrollWidth <= element.clientWidth));
    await history.getByRole("region", { name: "ตารางประวัติแท่งปิด", exact: true }).focus();
    await page.keyboard.press("ArrowRight");
    await page.waitForFunction(() => document.querySelector("#bar-history .history-table-scroll").scrollLeft > 0);
    await page.setViewportSize({ width: 1440, height: 1000 });
    checks.push(stage);

    stage = "fresh to stale and recovery";
    feedEnabled = false;
    await panel.getByText("ข้อมูลเก่า — ห้ามใช้เป็นราคาปัจจุบัน", { exact: true }).waitFor();
    assert(await panel.getByText("Bid ล่าสุดที่บันทึก", { exact: true }).isVisible());
    await chart.getByText("ข้อมูลเก่า — ไม่ใช่ราคาปัจจุบัน", { exact: true }).waitFor();
    feedEnabled = true;
    await connected.waitFor(); await chart.getByText("ข้อมูลล่าสุดจากช่อง MT5", { exact: true }).waitFor(); checks.push(stage);

    stage = "chart network failure clears values and reconnects";
    await page.route("**/api/owner/chart/*", route => route.abort());
    await chart.getByText("อ่านกราฟไม่ได้ ซ่อนข้อมูลแล้ว กำลังลองเชื่อมต่อใหม่", { exact: true }).waitFor();
    assert.equal(await chart.locator("canvas").count(), 0);
    assert.equal(await chart.locator(".chart-values dd").count(), 0);
    await page.unroute("**/api/owner/chart/*");
    await chart.getByLabel("ตรวจค่าแท่งเทียน (UTC)").waitFor(); checks.push(stage);

    stage = "chart snapshot expiry independent of fresh telemetry";
    chartEnabled = false;
    await chart.getByText("ข้อมูลเก่า — ไม่ใช่ราคาปัจจุบัน", { exact: true }).waitFor({ timeout: 20000 });
    assert(await connected.isVisible());
    chartEnabled = true;
    await chart.getByText("ข้อมูลล่าสุดจากช่อง MT5", { exact: true }).waitFor(); checks.push(stage);

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
    assert.equal((await http(`${apiOrigin}/owner/chart/M5`, { headers: { Authorization: `Bearer ${freshToken}` } })).status, 401);
    assert.equal((await http(`${apiOrigin}/owner/history/M5`, { headers: { Authorization: `Bearer ${freshToken}` } })).status, 401);
    assert.equal((await http(`${apiOrigin}/owner/execution`, { headers: { Authorization: `Bearer ${freshToken}` } })).status, 401);
    assert.equal((await http(`${apiOrigin}/owner/statistics`, { headers: { Authorization: `Bearer ${freshToken}` } })).status, 401);
    checks.push(stage);

    stage = "reload loses memory session";
    await login(users[0]); await connected.waitFor();
    await page.reload();
    await page.getByLabel("อีเมลเจ้าของ").waitFor();
    assert.equal(await equity.count(), 0);
    assert.equal(await page.getByRole("button", { name: "ออกจากระบบ", exact: true }).count(), 0);
    assert.equal(pageErrors, 0); assert(!pumpFailure);
    checks.push(stage);

    stage = "history survives API restart without a live snapshot";
    pumping = false; await pump;
    await stopChild(api);
    api = launchApi(port);
    for (let attempt = 0; ; attempt++) {
      assert(attempt < 40 && api.exitCode === null);
      try { if ((await http(`${apiOrigin}/health`)).ok) break; } catch { /* bounded restart */ }
      await delay(100);
    }
    const restartedToken = await login(users[0]);
    await panel.getByText("รอข้อมูลจาก MT5", { exact: true }).waitFor();
    await history.locator("tbody tr").first().waitFor();
    assert.equal(await equity.count(), 0);
    assert.equal(await chart.locator("canvas").count(), 0);
    const restored = await http(`${apiOrigin}/owner/history/M5?limit=20&archive_id=${initialHistory.archive_id}&through_receipt=${initialHistory.through_receipt}`,
      { headers: { Authorization: `Bearer ${restartedToken}` } });
    assert.equal(restored.status, 200);
    assert.deepEqual((await restored.json()).bars, initialHistory.bars);
    await logout(); assert.equal(pageErrors, 0);
    checks.push(stage);
  } catch (error) {
    failureStage = stage;
    failureType = error?.constructor?.name ?? "Error";
  }
  finally {
    pumping = false;
    await pump;
    try { await browser?.close(); } catch { cleanupOK = false; }
    try { if (web) await new Promise((done, reject) => web.httpServer.close(error => error ? reject(error) : done())); }
    catch { cleanupOK = false; }
    try { await stopChild(api); } catch { cleanupOK = false; }
    for (const token of issuedTokens) {
      try {
        const response = await http(`${origin}/auth/v1/logout?scope=global`, { method: "POST",
          headers: { apikey: local.ANON_KEY, Authorization: `Bearer ${token}` } });
        if (![204, 401, 403, 404].includes(response.status)) cleanupOK = false;
      } catch { cleanupOK = false; }
    }
    if (users.length) {
      const ownerFilter = `in.(${users.map(user => user.id).join(",")})`;
      for (const table of ["evaluations", "signals", "experiments", "accounts", "strategy_versions"]) {
        try {
          const url = new URL(`${origin}/rest/v1/${table}`); url.searchParams.set("owner_id", ownerFilter);
          const response = await http(url, { method: "DELETE", headers: { ...admin, Prefer: "return=minimal" } });
          if (![200, 204].includes(response.status)) cleanupOK = false;
        } catch { cleanupOK = false; }
      }
    }
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
    "apps/web/src/ExecutionPanel.tsx", "apps/web/src/execution-api.ts", "apps/web/src/ExecutionPanel.test.tsx",
    "apps/web/src/execution-api.test.ts", "tests/fixtures/execution_evidence_seed.py",
    "apps/web/src/SignalPanel.tsx", "apps/web/src/signal-api.ts", "apps/web/src/SignalPanel.test.tsx",
    "apps/web/src/signal-api.test.ts", "services/api/src/sochron1k/signal_evidence.py",
    "apps/web/src/StatisticsPanel.tsx", "apps/web/src/statistics-api.ts", "apps/web/src/StatisticsPanel.test.tsx",
    "apps/web/src/statistics-api.test.ts", "services/api/src/sochron1k/research_statistics.py",
    "apps/web/src/styles.css",
    "apps/web/src/chart-api.ts", "apps/web/src/ChartPanel.tsx", "apps/web/src/CandleCanvas.tsx",
    "apps/web/src/history-api.ts", "apps/web/src/HistoryPanel.tsx", "apps/web/src/history-api.test.ts",
    "apps/web/src/HistoryPanel.test.tsx", "apps/web/src/test/history-fixture.ts", "services/api/src/sochron1k/bar_history.py",
    "services/api/src/sochron1k/chart.py", "services/api/src/sochron1k/chart_api.py",
    "apps/web/src/owner-api.ts", "apps/web/src/owner-auth.ts", "apps/web/src/App.tsx",
    "apps/web/src/App.test.tsx", "apps/web/src/connection-api.ts",
    "apps/web/src/connection-api.test.ts", "apps/web/src/ConnectionMap.tsx",
    "apps/web/src/OperationalAlertsPanel.tsx", "apps/web/src/operational-alerts-api.ts",
    "apps/web/src/OperationalAlertsPanel.test.tsx", "apps/web/src/operational-alerts-api.test.ts",
    "apps/web/src/demo-readiness-api.ts", "apps/web/src/demo-readiness-api.test.ts",
    "apps/web/src/DemoReadinessPanel.tsx", "services/api/src/sochron1k/demo_readiness.py",
    "services/api/src/sochron1k/main.py", "services/api/src/sochron1k/ui_connections.py",
    "services/api/src/sochron1k/owner_api.py", "services/api/src/sochron1k/execution_evidence.py",
    "services/api/src/sochron1k/operational_alerts.py", "services/api/src/sochron1k/alert_lifecycle.py",
    "tests/test_operational_alerts.py",
    "tests/test_api_safety.py", "tests/test_demo_readiness.py", "tests/test_execution_evidence.py", "tests/test_signal_evidence.py",
    "tests/test_research_statistics.py",
    "services/api/src/sochron1k/owner_auth.py", "services/api/src/sochron1k/telemetry.py", "tests/fixtures/mt5-telemetry-v1.json"];
  const sha256 = {};
  for (const file of sources) sha256[file] = createHash("sha256").update(await readFile(file)).digest("hex");
  const result = { result: failureStage || !cleanupOK || creationUnresolved ? "FAIL" : "PASS", failure_stage: failureStage,
    failure_type: failureType,
    cleanup: creationUnresolved ? "UNKNOWN" : cleanupOK ? "PASS" : "FAIL",
    revision, dirty: Boolean(command("git", ["status", "--porcelain"])),
    checked_at: new Date().toISOString(), node: process.version, playwright: "1.63.0", chromium: browserVersion,
    python: command(join(root, ".venv/bin/python"), ["--version"]), runtime_images: runtimeImages.sort(),
    production_build_sha256: buildSha256, refresh_diagnostics: refreshDiagnostics,
    checks, sha256, fixture: "synthetic telemetry, OHLC, execution journal, derived alert inventory, durable alert lifecycle, owner-RLS signals and research evaluations; two generated local Auth users",
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
