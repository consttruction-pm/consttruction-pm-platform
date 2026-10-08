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
  setSmartGuide,
  setFieldOperations,
  setFieldIssues,
  setChangeClaimRecords,
  setDocuments,
  setFieldAssurance,
  setSiteDailyLogs,
  withActivities,
  setP6Presentation,
  addP6Field,
  removeP6Field,
  reorderP6Fields,
  updateP6FieldPresentation,
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
  assert.equal(state.columns.find((column) => column.id === "activity_name")?.label, "نام فعالیت");
  assert.equal(state.columns.find((column) => column.id === "progress")?.label, "پیشرفت");
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

test("locale switch relocalizes default grid columns", () => {
  let state = createWorkspaceState(context, "en");
  state = setLocale(state, "fa");

  assert.equal(state.columns.find((column) => column.id === "activity_name")?.label, "نام فعالیت");
  assert.equal(state.columns.find((column) => column.id === "progress")?.label, "پیشرفت");

  state = setLocale(state, "en");
  assert.equal(state.columns.find((column) => column.id === "activity_name")?.label, "Activity Name");
  assert.equal(state.columns.find((column) => column.id === "progress")?.label, "Progress");
});

test("P6 presentation preserves the authoritative field data types", () => {
  const state = createWorkspaceState(context);
  const registry = {
    registry_version: "p6-field-registry.v1" as const,
    reference_product: "Oracle Primavera P6 Professional" as const,
    reference_version: "25.12",
    status: "seeded_not_certified",
    fields: [
      { field_id: "f-string", subject_area: "activity", p6_field: "NAME", display_name: "Name", data_type: "string" as const, writable: true, computed: false, disposition: "supported" },
      { field_id: "f-datetime", subject_area: "activity", p6_field: "DT", display_name: "Date Time", data_type: "datetime" as const, writable: false, computed: false, disposition: "supported" },
      { field_id: "f-percentage", subject_area: "activity", p6_field: "PCT", display_name: "Percent", data_type: "percentage" as const, writable: false, computed: false, disposition: "supported" },
      { field_id: "f-cost", subject_area: "activity", p6_field: "COST", display_name: "Cost", data_type: "cost" as const, writable: false, computed: false, disposition: "supported" },
      { field_id: "f-enum", subject_area: "activity", p6_field: "TYPE", display_name: "Type", data_type: "enum" as const, writable: true, computed: false, disposition: "supported" },
      { field_id: "f-object-array", subject_area: "activity", p6_field: "REFS", display_name: "References", data_type: "object-id-array" as const, writable: false, computed: false, disposition: "supported" },
      { field_id: "f-spread", subject_area: "activity", p6_field: "SPREAD", display_name: "Spread", data_type: "spread" as const, writable: false, computed: false, disposition: "supported" },
    ],
  };
  const layout = {
    schema_version: "p6-layout.v1" as const,
    scope: "project" as const,
    view_id: "activity",
    revision: 1,
    columns: registry.fields.map((field, order) => ({
      field_id: field.field_id,
      visible: true,
      order,
      width: 120,
      alignment: "start" as const,
      pinned: false,
      frozen: false,
    })),
  };
  const next = setP6Presentation(state, registry, layout);
  assert.deepEqual(
    next.columns.map((column) => column.dataType),
    ["text", "datetime", "percentage", "cost", "enum", "object-id-array", "spread"],
  );
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
    alignment: "end",
    pinned: false,
    frozen: false,
  });

  assert.equal(next.columns.at(-1)?.formula, "[EV] - [PV]");
  assert.equal(next.columns.at(-1)?.alignment, "end");
  assert.equal(next.columns.at(-1)?.pinned, false);
  assert.equal(next.columns.at(-1)?.frozen, false);
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


test("smart guide attaches without changing project identity", () => {
  const state = createWorkspaceState(context);
  const next = setSmartGuide(state, {
    contractVersion: "smart-guide.v1",
    module: "schedule",
    locale: "fa",
    resultId: "result-1",
    generatedAt: "2026-09-27T08:00:00Z",
    summaryKey: "control.summary",
    findings: [],
    proposedActions: [],
    sourceCount: 1,
    approvalRequiredCount: 0,
  });
  assert.equal(next.smartGuide?.module, "schedule");
  assert.equal(next.smartGuide?.locale, "fa");
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


test("documents attach to the workspace without changing project context", () => {
  const state = createWorkspaceState(context);
  const next = setDocuments(state, [{
    documentId: "DOC-1",
    resourceType: "rfi",
    title: "RFI — foundation reinforcement",
    status: "submitted",
    revision: 4,
    contentHash: "sha256:" + "a".repeat(64),
    linkedEntityRefs: ["A-101"],
    hasStorageRef: true,
  }]);

  assert.equal(next.documents[0]?.documentId, "DOC-1");
  assert.equal(next.documents[0]?.resourceType, "rfi");
  assert.deepEqual(next.documents[0]?.linkedEntityRefs, ["A-101"]);
  assert.deepEqual(next.context, context);
});


test("P6 registry and persisted layout drive real workspace columns", () => {
  const registry = {
    registry_version: "p6-field-registry.v1" as const,
    reference_product: "Oracle Primavera P6 Professional" as const,
    reference_version: "26",
    status: "active",
    fields: [
      { field_id: "activity_code", subject_area: "activity", p6_field: "ActivityId", display_name: "Activity Code", data_type: "string" as const, writable: false, computed: false, disposition: "supported" },
      { field_id: "duration", subject_area: "activity", p6_field: "OriginalDuration", display_name: "Duration", data_type: "duration" as const, writable: false, computed: true, disposition: "supported" },
    ],
  };
  const layout = {
    schema_version: "p6-layout.v1" as const,
    scope: "project" as const,
    view_id: "activity-grid",
    revision: 1,
    columns: [
      { field_id: "activity_code", visible: true, order: 0, width: 140, alignment: "start" as const, pinned: false, frozen: false },
    ],
  };
  let state = createWorkspaceState(context);
  state = setP6Presentation(state, registry, layout);
  assert.deepEqual(state.columns.map((column) => column.id), ["activity_code"]);
  state = addP6Field(state, "duration");
  assert.deepEqual(state.columns.map((column) => column.id), ["activity_code", "duration"]);
  state = removeP6Field(state, "duration");
  assert.deepEqual(state.columns.map((column) => column.id), ["activity_code"]);
  assert.equal(state.p6FieldRegistry?.registry_version, "p6-field-registry.v1");
  assert.equal(state.columns[0]?.alignment, "start");
  assert.equal(state.columns[0]?.pinned, false);
  assert.equal(state.columns[0]?.frozen, false);
});

test("P6 layout mutations remain authoritative for reorder and presentation", () => {
  const registry = {
    registry_version: "p6-field-registry.v1" as const,
    reference_product: "Oracle Primavera P6 Professional" as const,
    reference_version: "26",
    status: "active",
    fields: [
      { field_id: "code", subject_area: "activity", p6_field: "ActivityId", display_name: "Code", data_type: "string" as const, writable: false, computed: false, disposition: "supported" },
      { field_id: "duration", subject_area: "activity", p6_field: "OriginalDuration", display_name: "Duration", data_type: "duration" as const, writable: false, computed: true, disposition: "supported" },
    ],
  };
  const layout = {
    schema_version: "p6-layout.v1" as const,
    scope: "project" as const,
    view_id: "activity-grid",
    revision: 3,
    columns: [
      { field_id: "code", visible: true, order: 0, width: 120, alignment: "start" as const, pinned: false, frozen: false },
      { field_id: "duration", visible: false, order: 1, width: 110, alignment: "end" as const, pinned: false, frozen: false },
    ],
  };
  let state = setP6Presentation(createWorkspaceState(context), registry, layout);
  assert.equal(state.columns.length, 1);
  state = reorderP6Fields(state, ["duration", "code"]);
  assert.equal(state.p6Layout?.columns[0]?.field_id, "duration");
  state = updateP6FieldPresentation(state, "code", { visible: false, width: 180 });
  assert.equal(state.p6Layout?.columns.find((column) => column.field_id === "code")?.width, 180);
  assert.equal(state.columns.length, 0);
});


test("P6 chooser can restore a hidden authoritative field", () => {
  const registry = { registry_version: "p6-field-registry.v1" as const, reference_product: "Oracle Primavera P6 Professional" as const, reference_version: "26", status: "active", fields: [{ field_id: "code", subject_area: "activity", p6_field: "ActivityId", display_name: "Code", data_type: "string" as const, writable: false, computed: false, disposition: "supported" }] };
  const layout = { schema_version: "p6-layout.v1" as const, scope: "project" as const, view_id: "activity-grid", revision: 1, columns: [{ field_id: "code", visible: false, order: 0, width: 120, alignment: "start" as const, pinned: false, frozen: false }] };
  let state = setP6Presentation(createWorkspaceState(context), registry, layout);
  assert.equal(state.columns.length, 0);
  state = addP6Field(state, "code");
  assert.equal(state.columns.length, 1);
  assert.equal(state.p6Layout?.columns[0]?.visible, true);
});