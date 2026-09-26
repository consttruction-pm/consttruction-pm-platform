import assert from "node:assert/strict";
import test from "node:test";

type PortfolioDecision = {
  contract_version: string;
  decision_id: string;
  portfolio_id: string;
  tenant_id: string;
  status: string;
  decision_type: string;
  title_key: string;
  requires_approval: boolean;
  evidence_refs: Array<{ source_id: string; source_type: string; locator: string; revision: number }>;
  approved_by?: string | null;
  approved_at?: string | null;
  implemented_at?: string | null;
  implementation_reference?: string | null;
  [key: string]: unknown;
};

const baseDecision: PortfolioDecision = {
  contract_version: "portfolio-decision.v1",
  decision_id: "D-1",
  portfolio_id: "PORT-1",
  tenant_id: "TENANT-1",
  status: "proposed",
  decision_type: "review",
  title_key: "portfolio.review",
  requires_approval: true,
  evidence_refs: [
    { source_id: "SNAP-1", source_type: "portfolio_snapshot", locator: "$.projects[0]", revision: 7 },
  ],
};

function assertClientPortfolioDecision(value: unknown): asserts value is PortfolioDecision {
  assert.ok(value && typeof value === "object" && !Array.isArray(value), "decision must be an object");
  const decision = value as Record<string, unknown>;
  const allowed = new Set([
    "contract_version", "decision_id", "portfolio_id", "tenant_id", "status",
    "decision_type", "title_key", "detail_key", "affected_project_ids",
    "source_snapshot_id", "impact_link_ids", "proposed_action_ids",
    "requires_approval", "approved_by", "approved_at", "implemented_at",
    "implementation_reference", "evidence_refs",
  ]);
  for (const key of Object.keys(decision)) assert.ok(allowed.has(key), `unexpected contract field: ${key}`);

  for (const key of ["contract_version", "decision_id", "portfolio_id", "tenant_id", "status", "decision_type", "title_key"]) {
    assert.equal(typeof decision[key], "string", `invalid ${key}`);
  }
  assert.equal(decision.contract_version, "portfolio-decision.v1");
  assert.equal(typeof decision.requires_approval, "boolean");
  assert.ok(Array.isArray(decision.evidence_refs) && decision.evidence_refs.length > 0);

  const statuses = new Set(["proposed", "under_review", "approved", "rejected", "implemented", "closed", "cancelled"]);
  const types = new Set(["escalate", "prioritize", "hold", "review", "sequence", "approve"]);
  assert.ok(statuses.has(decision.status as string));
  assert.ok(types.has(decision.decision_type as string));

  for (const ref of decision.evidence_refs as unknown[]) {
    assert.ok(ref && typeof ref === "object" && !Array.isArray(ref));
    const evidence = ref as Record<string, unknown>;
    for (const key of ["source_id", "source_type", "locator"]) assert.equal(typeof evidence[key], "string");
    assert.equal(typeof evidence.revision, "number");
    assert.ok(Number.isSafeInteger(evidence.revision) && (evidence.revision as number) >= 0);
  }

  if (decision.requires_approval && ["approved", "implemented", "closed"].includes(decision.status as string)) {
    assert.equal(typeof decision.approved_by, "string");
    assert.equal(typeof decision.approved_at, "string");
  }
  if (decision.status === "implemented") {
    assert.equal(typeof decision.implemented_at, "string");
    assert.equal(typeof decision.implementation_reference, "string");
  }
}

test("client runtime accepts the shared portfolio-decision.v1 wire contract", () => {
  const wireValue = JSON.parse(JSON.stringify(baseDecision));
  assertClientPortfolioDecision(wireValue);
  assert.equal(wireValue.tenant_id, "TENANT-1");
  assert.equal(wireValue.evidence_refs[0].revision, 7);
});

test("client runtime rejects lifecycle payloads that violate approval requirements", () => {
  const invalid = JSON.parse(JSON.stringify({
    ...baseDecision,
    status: "approved",
    approved_by: null,
    approved_at: null,
  }));
  assert.throws(() => assertClientPortfolioDecision(invalid));
});

test("client runtime rejects unknown fields instead of silently widening the closed contract", () => {
  const invalid = JSON.parse(JSON.stringify({
    ...baseDecision,
    unexpected_client_field: true,
  }));
  assert.throws(() => assertClientPortfolioDecision(invalid));
});
