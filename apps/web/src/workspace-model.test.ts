import assert from "node:assert/strict";
import test from "node:test";

import {
  addFormulaColumn,
  createWorkspaceState,
  selectActivity,
  selectWbs,
  setCalendarMode,
  setLocale,
  setControlSummary,
  setFieldOperations,
  setFieldIssues,
  setChangeClaimRecords,
  setFieldAssurance,
  setSiteDailyLogs,
  withActivities,
} from "./workspace-model.js";

const context = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 4,
};

test("workspace model creates a bilingual Main Workspace state", () => {
  const state = createWorkspaceState(context, "fa", "jalali");

  assert.equal(state.direction, "rtl");
  assert.equal(state.calendarMode, "jalali");
  assert.equal(state.activeMenu, "schedule");
  assert.equal(state.visiblePanels.activity_grid, true);
  assert.equal(state.columns.find((column) => column.id === "duration")?.dataType, "duration");
});

test("WBS selection clears Activity selection", () => {
  let state = createWorkspaceState(context);
  state = withActivities(state, [
    { id: "A-1", wbsId: "W-1", code: "01", name: "Foundation" },
    { id: "A-2", wbsId: "W-2", code: "02", name: "Structure" },
  ]);
  state = selectActivity(state, "A-1");
  assert.equal(state.selectedActivityId, "A-1");

  state = selectWbs(state, "W-2");
  assert.equal(state.selectedWbsId, "W-2");
  assert.equal(state.selectedActivityId, null);
});

test("activity selection rejects activities that are not loaded", () => {
  const state = createWorkspaceState(context);
  assert.throws(() => selectActivity(state, "missing"), /ACTIVITY_NOT_FOUND/);
});

test("locale and calendar switches preserve project context", () => {
  let state = createWorkspaceState(context);
  state = setLocale(state, "fa");
  state = setCalendarMode(state, "jalali");

  assert.equal(state.direction, "rtl");
  assert.equal(state.calendarMode, "jalali");
  assert.deepEqual(state.context, context);
});

test("formula columns remain metadata and do not calculate client values", () => {
  const state = createWorkspaceState(context);
  const next = addFormulaColumn(state, {
    id: "variance",
    label: "Variance",
    dataType: "decimal",
    editable: false,
    formula: "[EV] - [PV]",
    width: 120,
  });

  assert.equal(next.columns.at(-1)?.formula, "[EV] - [PV]");
  assert.equal(next.columns.at(-1)?.dataType, "decimal");
});

test("duplicate activity ids are rejected", () => {
  const state = createWorkspaceState(context);
  assert.throws(
    () =>
      withActivities(state, [
        { id: "A-1", wbsId: "W-1", code: "01", name: "One" },
        { id: "A-1", wbsId: "W-1", code: "02", name: "Two" },
      ]),
    /INVALID_ACTIVITY_ROWS/,
  );
});


test("control summary can be attached without changing project context", () => {
  const state = createWorkspaceState(context);
  const summary = {
    resultId: "result-1",
    generatedAt: "2026-09-27T08:00:00Z",
    summaryKey: "control.summary",
    metrics: Object.freeze({ progress_percent: 63 }),
    findings: [],
    proposedActions: [],
  };
  const next = setControlSummary(state, summary);
  assert.equal(next.controlSummary?.resultId, "result-1");
  assert.deepEqual(next.context, context);
});


test("site daily logs attach to the same project workspace", () => {
  const state = createWorkspaceState(context);
  const log = {
    logId: "log-1",
    logDate: "2026-09-27",
    locationKey: "tower-a",
    status: "submitted" as const,
    entries: [],
    updatedAt: "2026-09-27T10:00:00Z",
  };
  const next = setSiteDailyLogs(state, [log]);
  assert.equal(next.siteDailyLogs[0]?.logId, "log-1");
  assert.deepEqual(next.context, context);
});


test("field operations attach to the workspace without changing project identity", () => {
  const state = createWorkspaceState(context);
  const next = setFieldOperations(
    state,
    [{
      timecardId: "tc-1",
      personId: "person-1",
      logDate: "2026-09-27",
      workplaceKey: "tower-a",
      attendanceStatus: "present",
      startAt: "2026-09-27T07:30:00Z",
      endAt: "2026-09-27T16:30:00Z",
    }],
    [{
      reportId: "eqr-1",
      equipmentId: "exc-01",
      reportDate: "2026-09-27",
      workplaceKey: "tower-a",
      status: "active",
      breakdownCauseKey: null,
      reportedBy: "user-1",
      meterHours: "120.50",
    }],
  );
  assert.equal(next.timecards[0]?.personId, "person-1");
  assert.equal(next.equipmentReports[0]?.equipmentId, "exc-01");
  assert.deepEqual(next.context, context);
});

test("field issues attach without changing project context", () => {
  const state = createWorkspaceState(context);
  const next = setFieldIssues(state, [{
    issueId: "issue-1",
    category: "safety",
    severity: "critical",
    status: "open",
    titleKey: "issue.title",
    detailKey: "issue.detail",
    reportedBy: "user-1",
    locationKey: "tower-a",
    activityIds: ["A-101"],
    evidenceCount: 1,
    updatedAt: "2026-09-27T10:00:00Z",
  }]);
  assert.equal(next.fieldIssues[0]?.issueId, "issue-1");
  assert.deepEqual(next.context, context);
});

test("field assurance attaches without changing project context", () => {
  const state = createWorkspaceState(context);
  const next = setFieldAssurance(state, {
    inspections: [{
      inspectionId: "insp-1",
      inspectionTypeKey: "rebar",
      subjectType: "activity",
      subjectId: "A-10",
      locationKey: "tower-a",
      inspectionDate: "2026-09-27",
      inspectorId: "user-1",
      status: "completed",
      result: "pass",
      checklist: [{
        itemId: "item-1",
        criterionKey: "cover",
        result: "pass",
        commentKey: null,
      }],
    }],
    qualityRecords: [{
      recordId: "qr-1",
      categoryKey: "concrete",
      severity: "high",
      status: "pending_verification",
      titleKey: "ncr.concrete",
      detailKey: null,
      reportedBy: "qc-1",
      locationKey: "tower-a",
      activityIds: ["A-10"],
      inspectionId: "insp-1",
      specificationReference: "SPEC-09",
      correctiveActionKey: "repair",
      dispositionKey: null,
      evidenceCount: 1,
    }],
    safetyObservations: [{
      observationId: "obs-1",
      categoryKey: "ppe",
      severity: "medium",
      status: "open",
      titleKey: "ppe.gap",
      observedBy: "safety-1",
      locationKey: "tower-a",
      activityIds: ["A-10"],
      immediateActionKey: null,
      rootCauseKey: null,
    }],
    punchItems: [{
      punchId: "p-1",
      categoryKey: "finish",
      priority: "medium",
      status: "open",
      titleKey: "door.hardware",
      reportedBy: "qc-1",
      locationKey: "tower-a",
      activityIds: ["A-10"],
      responsiblePartyId: "sub-1",
      dueDate: "2026-10-05",
      verificationBy: null,
      closeoutCodeKey: null,
    }],
  });
  assert.equal(next.qualityRecords[0]?.recordId, "qr-1");
  assert.equal(next.safetyObservations[0]?.observationId, "obs-1");
  assert.equal(next.punchItems[0]?.punchId, "p-1");
  assert.deepEqual(next.context, context);
});

test("change claim records attach without changing project context", () => {
  const state = createWorkspaceState(context);
  const next = setChangeClaimRecords(state, {
    changeNotices: [{
      noticeId: "N-1",
      noticeType: "variation",
      status: "under_review",
      titleKey: "notice.title",
      detailKey: null,
      submittedBy: "user-1",
      noticeDate: "2026-09-27",
      scheduleRefs: ["A-1"],
      costRefs: ["C-1"],
      dependencyRefs: [],
      approvalRequired: true,
      evidenceCount: 1,
    }],
    changeCases: [{
      changeId: "CH-1",
      changeType: "variation",
      status: "approved",
      titleKey: "change.title",
      detailKey: null,
      initiatedBy: "user-1",
      originatingNoticeId: "N-1",
      scheduleRefs: ["A-1"],
      costRefs: ["C-1"],
      dependencyRefs: [],
      impactLinkIds: ["IMP-1"],
      implementationActivityIds: ["A-2"],
      approvalRequired: true,
      approvedBy: "user-2",
      approvedAt: "2026-09-27T09:00:00Z",
      evidenceCount: 1,
    }],
    claims: [{
      claimId: "CL-1",
      claimType: "extension_of_time",
      status: "submitted",
      titleKey: "claim.title",
      detailKey: null,
      submittedBy: "user-1",
      originatingNoticeId: "N-1",
      changeId: "CH-1",
      scheduleRefs: ["A-1"],
      costRefs: ["C-1"],
      impactLinkIds: ["IMP-2"],
      entitlementReference: "ENT-1",
      quantumReference: "Q-1",
      decisionReference: null,
      approvalRequired: true,
      decidedBy: null,
      decidedAt: null,
      evidenceCount: 1,
    }],
    changeClaimImpacts: [{
      linkId: "IMP-1",
      recordType: "change",
      recordId: "CH-1",
      impactedDomain: "schedule",
      impactedEntityType: "activity",
      impactedEntityId: "A-1",
      impactType: "potential_delay",
      scheduleReference: "A-1",
      costReference: "C-1",
      requiresApplicationApproval: true,
      evidenceCount: 1,
    }],
  });
  assert.equal(next.changeNotices[0]?.noticeId, "N-1");
  assert.equal(next.changeCases[0]?.changeId, "CH-1");
  assert.equal(next.claims[0]?.claimId, "CL-1");
  assert.equal(next.changeClaimImpacts[0]?.linkId, "IMP-1");
  assert.deepEqual(next.context, context);
});

test("typed activity cells and Gantt data remain server-projected", () => {
  const state = createWorkspaceState(context);
  const next = withActivities(state, [
    {
      id: "A-1",
      wbsId: "W-1",
      code: "01",
      name: "Foundation",
      cells: {
        start: "2026-09-01T08:00:00Z",
        finish: "2026-09-05T17:00:00Z",
        duration: 4,
        progress: 35,
      },
      gantt: {
        start: "2026-09-01T08:00:00Z",
        finish: "2026-09-05T17:00:00Z",
        progressPercent: 35,
        critical: true,
      },
    },
  ]);

  assert.equal(next.activities[0]?.cells?.duration, 4);
  assert.equal(next.activities[0]?.gantt?.critical, true);
  assert.equal(next.activities[0]?.gantt?.progressPercent, 35);
});

test("invalid Gantt geometry is rejected at the workspace boundary", () => {
  const state = createWorkspaceState(context);
  assert.throws(
    () =>
      withActivities(state, [
        {
          id: "A-1",
          wbsId: "W-1",
          code: "01",
          name: "Foundation",
          gantt: {
            start: "2026-09-05",
            finish: "2026-09-01",
            progressPercent: 40,
            critical: false,
          },
        },
      ]),
    /INVALID_GANTT_DATA/,
  );
});
