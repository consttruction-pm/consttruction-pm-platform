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
} from "./workspace-change-claims.js";

const context = { tenant_id: "tenant-1", project_id: "project-1", project_revision: 9 };
const evidence = [{ source_id: "doc-1", source_type: "document", locator: "/documents/1", revision: 9 }];
const audit = { updated_at: "2026-09-27T10:00:00Z" };

test("change case projection preserves control links and approval state", () => {
  const value = projectChangeCase({
    contract_version: CHANGE_CASE_VERSION,
    change_id: "chg-1",
    scope: context,
    change_type: "variation",
    status: "under_review",
    title_key: "change.title",
    detail_key: "change.detail",
    initiated_by: "user-1",
    originating_notice_id: "notice-1",
    schedule_refs: ["A-10"],
    cost_refs: ["C-1"],
    dependency_refs: ["D-1"],
    impact_link_ids: ["impact-1"],
    implementation_activity_ids: ["A-10", "A-11"],
    approval_required: true,
    approved_by: null,
    evidence_refs: evidence,
    audit,
  }, context);

  assert.equal(value.changeId, "chg-1");
  assert.equal(value.impactLinkCount, 1);
  assert.equal(value.implementationActivityCount, 2);
  assert.equal(value.approvalRequired, true);
});

test("notice and claim projections preserve cross-domain references", () => {
  const notice = projectChangeNotice({
    contract_version: CHANGE_NOTICE_VERSION,
    notice_id: "notice-1",
    scope: context,
    notice_type: "delay_notice",
    status: "submitted",
    title_key: "notice.delay",
    detail_key: "notice.detail",
    submitted_by: "user-1",
    notice_date: "2026-09-27",
    schedule_refs: ["A-10"],
    cost_refs: [],
    dependency_refs: [],
    evidence_refs: evidence,
    approval_required: true,
    audit,
  }, context);

  const claim = projectClaimRecord({
    contract_version: CLAIM_RECORD_VERSION,
    claim_id: "claim-1",
    scope: context,
    claim_type: "extension_of_time",
    status: "under_review",
    title_key: "claim.eot",
    detail_key: null,
    submitted_by: "contractor",
    originating_notice_id: "notice-1",
    change_id: "chg-1",
    schedule_refs: ["A-10"],
    cost_refs: ["C-1"],
    impact_link_ids: ["impact-1"],
    entitlement_reference: "ENT-1",
    quantum_reference: "Q-1",
    decision_reference: null,
    approval_required: true,
    decided_by: null,
    evidence_refs: evidence,
    audit,
  }, context);

  assert.equal(notice.noticeType, "delay_notice");
  assert.equal(claim.changeId, "chg-1");
  assert.equal(claim.scheduleRefCount, 1);
  assert.equal(claim.quantumReference, "Q-1");
});

test("impact projection preserves domain links and approval requirement", () => {
  const value = projectChangeClaimImpact({
    contract_version: CHANGE_CLAIM_IMPACT_VERSION,
    link_id: "impact-1",
    scope: context,
    record_type: "claim",
    record_id: "claim-1",
    impacted_domain: "schedule",
    impacted_entity_type: "activity",
    impacted_entity_id: "A-10",
    impact_type: "delay",
    schedule_reference: "A-10",
    cost_reference: null,
    evidence_refs: evidence,
    requires_application_approval: true,
  }, context);

  assert.equal(value.recordType, "claim");
  assert.equal(value.impactedEntityId, "A-10");
  assert.equal(value.requiresApplicationApproval, true);
});

test("stale scope and unsupported contract are rejected", () => {
  assert.throws(() => projectClaimRecord({
    contract_version: CLAIM_RECORD_VERSION,
    claim_id: "claim-1",
    scope: { ...context, project_revision: 8 },
    claim_type: "delay",
    status: "submitted",
    title_key: "claim.delay",
    submitted_by: "user-1",
    approval_required: false,
    evidence_refs: evidence,
    audit,
  }, context), /STALE_CLAIM_RECORD_SCOPE/);

  assert.throws(() => projectChangeNotice({
    contract_version: "change-notice.v99" as never,
    notice_id: "notice-1",
    scope: context,
    notice_type: "instruction",
    status: "draft",
    title_key: "notice.title",
    detail_key: "notice.detail",
    submitted_by: "user-1",
    evidence_refs: evidence,
    audit,
  }, context), /UNSUPPORTED_CHANGE_NOTICE_CONTRACT/);
});
