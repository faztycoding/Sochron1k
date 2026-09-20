import { describe, expect, it } from "vitest";

import { parseDemoReadiness, readinessGateDefinitions, readinessGateIds } from "./demo-readiness-api";

function fixture() {
  return {
    protocol: "sochron.demo-readiness.v1",
    state: "awaiting_owner_inputs",
    demo_only: true,
    auto_trading_enabled: false,
    release_ready: false,
    round_trip_authorized: false,
    unattended_demo_ready: false,
    gates: readinessGateIds.map(id => ({
      id,
      state: id === "operational_authorization" ? "not_authorized" :
        ["target_artifact", "broker_round_trip", "recovery_observability"].includes(id) ? "not_run" : "missing",
      api_routes: readinessGateDefinitions[id].routes,
      sources: readinessGateDefinitions[id].sources,
      next_action: readinessGateDefinitions[id].nextActionCode,
    })),
  };
}

describe("Demo readiness contract", () => {
  it("accepts the exact redacted, default-off response", () => {
    const parsed = parseDemoReadiness(fixture());
    expect(parsed.gates.map(gate => gate.id)).toEqual(readinessGateIds);
    expect(parsed.release_ready).toBe(false);
  });

  it("accepts admitted target evidence without promoting release", () => {
    const value = fixture();
    value.state = "awaiting_runtime";
    for (const gate of value.gates.slice(5, 8)) gate.state = "evidence_admitted";
    const parsed = parseDemoReadiness(value);
    expect(parsed.gates.slice(5, 8).map(gate => gate.state)).toEqual([
      "evidence_admitted", "evidence_admitted", "evidence_admitted",
    ]);
    expect(parsed.gates[5].api_routes).toContain("/api/owner/target-evidence");
    expect(parsed.release_ready).toBe(false);
    expect(parsed.round_trip_authorized).toBe(false);
  });

  it.each([
    ["true release flag", () => ({ ...fixture(), release_ready: true })],
    ["unknown root field", () => ({ ...fixture(), account_ref: "unsafe" })],
    ["reordered gate", () => {
      const value = fixture();
      [value.gates[0], value.gates[1]] = [value.gates[1], value.gates[0]];
      return value;
    }],
    ["unsafe route drift", () => {
      const value = fixture();
      value.gates[0] = { ...value.gates[0], api_routes: ["/api/unsafe"] };
      return value;
    }],
    ["unknown gate field", () => {
      const value = fixture();
      value.gates[0] = { ...value.gates[0], token: "unsafe" } as typeof value.gates[number];
      return value;
    }],
    ["unknown evidence state", () => {
      const value = fixture();
      value.gates[5].state = "evidence_verified";
      return value;
    }],
    ["evidence state on the wrong gate", () => {
      const value = fixture();
      value.gates[0].state = "evidence_admitted";
      return value;
    }],
  ])("rejects %s", (_name, makeValue) => {
    expect(() => parseDemoReadiness(makeValue())).toThrow();
  });
});
