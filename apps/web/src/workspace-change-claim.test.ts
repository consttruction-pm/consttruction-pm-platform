import assert from "node:assert/strict";
import test from "node:test";

import {
  CHANGE_CASE_VERSION,
  CHANGE_CLAIM_IMPACT_VERSION,
  CHANGE_NOTICE_VERSION,
  CLAIM_RECORD_VERSION,
  projectChangeCase,
  projectChangeClaimImpact,
  projectChangeNotice,
  projectClaimRecord,
} from "./workspace-change-claim.js";

const context = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  project_revision: 12,
};

const evidence = [{
  source_id: "doc-1",
  source_type: "document",
  locator: "/documents/doc-1",
  revision: 12,
}];

const audit = {
  created_by: "user-1",
  created_at: "2026-09-27T06:00:00Z",
  updated_at: "2026-09-27T07:00:00Z",
};

test("change notice projection preserves schedule, cost, dependency and evidence references", () => {
  const notice = projectChangeNotice({
    contract_version: CHANGE_NOTICE_VERSION,
    notice_id: "N-1",
    scope: context,
    notice_type: "variation",
    status: "under_review",
    title_key: "change.notice.title",
    detail_key: "change.notice.detail",
    submitted_by: "contract-manager",
    notice_date: "2026-09-27",
    schedule_refs: ["A-101", "A-102"],
    cost_refs: ["C-10"],
    dependency_refs: ["D-20"],
    evidence_refs: evidence,
    approval_required: true,
    audit,
  }, context);

  assert.equal(notice.noticeId, "N-1");
  assert.deepEqual(notice.scheduleRefs, ["A-101", "A-102"]);
  assert.deepEqual(notice.costRefs, ["C-10"]);
  assert.equal(notice.evidenceCount, 1);
});

test("approved change case requires approval metadata", () => {
  assert.throws(() => projectChangeCase({
    contract_version: CHANGE_CASE_VERSION,
    change_id: "CH-1",
    scope: context,
    change_type: "variation",
    status: "approved",
    title_key: "change.case.title",
    initiated_by: "project-manager",
    evidence_refs: evidence,
    approval_required: true,
    audit,
  }, context), /CHANGE_APPROVAL_METADATA_REQUIRED/);

  const change = projectChangeCase({
    contract_version: CHANGE_CASE_VERSION,
    change_id: "CH-1",
    scope: context,
    change_type: "variation",
    status: "approved",
    title_key: "change.case.title",
    detail_key: "change.case.detail",
    initiated_by: "project-manager",
    originating_notice_id: "N-1",
    schedule_refs: ["A-101"],
    cost_refs: ["C-10"],
    dependency_refs: ["D-20"],
    impact_link_ids: ["IMP-1"],
    implementation_activity_ids: ["A-103"],
    approval_required: true,
    approved_by: "owner-1",
    approved_at: "2026-09-27T08:00:00Z",
    evidence_refs: evidence,
    audit,
  }, context);

  assert.equal(change.approvedBy, "owner-1");
  assert.equal(change.impactLinkIds[0], "IMP-1");
  assert.equal(change.implementationActivityIds[0], "A-103");
});

test("accepted claim requires decision traceability", () => {
  assert.throws(() => projectClaimRecord({
    contract_version: CLAIM_RECORD_VERSION,
    claim_id: "CL-1",
    scope: context,
    claim_type: "extension_of_time",
    status: "accepted",
    title_key: "claim.eot.title",
    submitted_by: "contract-manager",
    evidence_refs: evidence,
    audit,
  }, context), /CLAIM_DECISION_METADATA_REQUIRED/);

  const claim = projectClaimRecord({
    contract_version: CLAIM_RECORD_VERSION,
    claim_id: "CL-1",
    scope: context,
    claim_type: "extension_of_time",
    status: "accepted",
    title_key: "claim.eot.title",
    detail_key: "claim.eot.detail",
    submitted_by: "contract-manager",
    originating_notice_id: "N-1",
    change_id: "CH-1",
    schedule_refs: ["A-101"],
    cost_refs: ["C-10"],
    impact_link_ids: ["IMP-2"],
    entitlement_reference: "ENT-1",
    quantum_reference: "Q-1",
    decision_reference: "DEC-1",
    approval_required: true,
    decided_by: "owner-1",
    decided_at: "2026-09-27T09:00:00Z",
    evidence_refs: evidence,
    audit,
  }, context);

  assert.equal(claim.changeId, "CH-1");
  assert.equal(claim.entitlementReference, "ENT-1");
  assert.equal(claim.decisionReference, "DEC-1");
});

test("change claim impact preserves schedule/cost references and approval requirement", () => {
  const impact = projectChangeClaimImpact({
    contract_version: CHANGE_CLAIM_IMPACT_VERSION,
    link_id: "IMP-1",
    scope: context,
    record_type: "change",
    record_id: "CH-1",
    impacted_domain: "schedule",
    impacted_entity_type: "activity",
    impacted_entity_id: "A-101",
    impact_type: "potential_delay",
    schedule_reference: "A-101",
    cost_reference: "C-10",
    evidence_refs: evidence,
    requires_application_approval: true,
  }, context);

  assert.equal(impact.recordType, "change");
  assert.equal(impact.scheduleReference, "A-101");
  assert.equal(impact.costReference, "C-10");
  assert.equal(impact.requiresApplicationApproval, true);
});

test("change and claim projections reject stale scopes, bad evidence and unsupported versions", () => {
  assert.throws(() => projectChangeNotice({
    contract_version: CHANGE_NOTICE_VERSION,
    notice_id: "N-2",
    scope: { ...context, project_revision: 11 },
    notice_type: "instruction",
    status: "submitted",
    title_key: "notice.title",
    submitted_by: "user-1",
    evidence_refs: evidence,
    audit,
  }, context), /STALE_CHANGE_NOTICE_SCOPE/);

  assert.throws(() => projectClaimRecord({
    contract_version: "claim-record.v99",
    claim_id: "CL-2",
    scope: context,
    claim_type: "other",
    status: "draft",
    title_key: "claim.title",
    submitted_by: "user-1",
    evidence_refs: evidence,
    audit,
  } as never, context), /UNSUPPORTED_CLAIM_RECORD_CONTRACT/);

  assert.throws(() => projectChangeClaimImpact({
    contract_version: CHANGE_CLAIM_IMPACT_VERSION,
    link_id: "IMP-2",
    scope: context,
    record_type: "claim",
    record_id: "CL-1",
    impacted_domain: "cost",
    impacted_entity_type: "commitment",
    impacted_entity_id: "C-10",
    impact_type: "potential_increase",
    evidence_refs: [],
    requires_application_approval: true,
  }, context), /INVALID_CHANGE_CLAIM_IMPACT_EVIDENCE/);
});
