import { describe, expect, it } from "vitest";
import { connectionDefinitions, connectionIds, parseConnectionMap } from "./connection-api";

function fixture() {
  return {
    demo_only: true, auto_trading_enabled: false, execution_ready: false,
    connections: connectionIds.map(id => ({
      id,
      implementation: connectionDefinitions[id].implementation,
      runtime: id === "core_api" ? "connected" : id === "statistics" ? "not_applicable" : "awaiting_configuration",
      current_routes: [...connectionDefinitions[id].routes],
      required_route: connectionDefinitions[id].required,
      sources: [...connectionDefinitions[id].sources],
    })),
  };
}

describe("redacted UI connection map", () => {
  it("accepts the exact Demo-only map", () => {
    const value = fixture();
    expect(parseConnectionMap(value).connections.map(node => node.id)).toEqual(connectionIds);
  });

  it.each([
    ["Demo flag", (value: ReturnType<typeof fixture>) => { value.demo_only = false; }],
    ["Auto Trading", (value: ReturnType<typeof fixture>) => { value.auto_trading_enabled = true; }],
    ["execution readiness", (value: ReturnType<typeof fixture>) => { value.execution_ready = true; }],
    ["unknown status", (value: ReturnType<typeof fixture>) => { value.connections[0].runtime = "unknown"; }],
    ["route drift", (value: ReturnType<typeof fixture>) => { value.connections[2].current_routes = ["/api/private"]; }],
    ["source drift", (value: ReturnType<typeof fixture>) => { value.connections[2].sources = ["browser"]; }],
    ["order drift", (value: ReturnType<typeof fixture>) => { value.connections.reverse(); }],
  ])("rejects %s", (_name, mutate) => {
    const value = fixture(); mutate(value);
    expect(() => parseConnectionMap(value)).toThrow();
  });
});
