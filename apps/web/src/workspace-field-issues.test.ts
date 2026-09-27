import assert from "node:assert/strict";
import test from "node:test";

import {
  FIELD_ISSUE_VERSION,
  projectFieldIssue,
} from "./workspace-field-issues.js";

const scope = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  project_revision: 12,
};

const evidence = [{
  source_id: "photo-1",
  source_type: "photo",
  locator: "/photos/1",
  revision: 12,
}];

const audit = {
  created_by: "user-1",
  created_at: "2026-09-27T06:00:00Z",
  updated_at: "2026-09-27T10:00:00Z",
};

test("field issue projection preserves evidence and activity links", () => {
  const issue = projectFieldIssue({
    contract_version: FIELD_ISSUE_VERSION,
    issue_id: "issue-1",
    scope,
    category: "quality",
    severity: "high",
    status: "open",
    title_key: "issue.concrete.honeycombing",
    detail_key: "issue.detail",
    reported_by: "inspector-1",
    location_key: "tower-a",
    activity_ids: ["A-101", "A-102"],
    evidence_refs: evidence,
    audit,
  }, scope);

  assert.equal(issue.issueId, "issue-1");
  assert.equal(issue.evidenceCount, 1);
  assert.deepEqual(issue.activityIds, ["A-101", "A-102"]);
  assert.equal(issue.updatedAt, audit.updated_at);
});

test("field issue rejects stale project revision", () => {
  assert.throws(() => projectFieldIssue({
    contract_version: FIELD_ISSUE_VERSION,
    issue_id: "issue-1",
    scope: { ...scope, project_revision: 11 },
    category: "safety",
    severity: "critical",
    status: "open",
    title_key: "issue.title",
    reported_by: "user-1",
    evidence_refs: evidence,
    audit,
  }, scope), /STALE_FIELD_ISSUE_SCOPE/);
});

test("field issue requires at least one valid evidence reference", () => {
  assert.throws(() => projectFieldIssue({
    contract_version: FIELD_ISSUE_VERSION,
    issue_id: "issue-1",
    scope,
    category: "quality",
    severity: "medium",
    status: "open",
    title_key: "issue.title",
    reported_by: "user-1",
    evidence_refs: [],
    audit,
  }, scope), /INVALID_FIELD_ISSUE/);

  assert.throws(() => projectFieldIssue({
    contract_version: FIELD_ISSUE_VERSION,
    issue_id: "issue-2",
    scope,
    category: "quality",
    severity: "medium",
    status: "open",
    title_key: "issue.title",
    reported_by: "user-1",
    evidence_refs: [{ ...evidence[0], revision: -1 }],
    audit,
  }, scope), /INVALID_FIELD_ISSUE_EVIDENCE/);
});

test("field issue rejects invalid audit timestamps and unsupported contracts", () => {
  assert.throws(() => projectFieldIssue({
    contract_version: FIELD_ISSUE_VERSION,
    issue_id: "issue-1",
    scope,
    category: "quality",
    severity: "medium",
    status: "open",
    title_key: "issue.title",
    reported_by: "user-1",
    evidence_refs: evidence,
    audit: { ...audit, updated_at: "2026-09-27T10:00:00" },
  }, scope), /INVALID_FIELD_ISSUE/);

  assert.throws(() => projectFieldIssue({
    ...{
      contract_version: "field-issue.v99",
      issue_id: "issue-1",
      scope,
      category: "quality",
      severity: "medium",
      status: "open",
      title_key: "issue.title",
      reported_by: "user-1",
      evidence_refs: evidence,
      audit,
    },
  } as never, scope), /UNSUPPORTED_FIELD_ISSUE_CONTRACT/);
});
