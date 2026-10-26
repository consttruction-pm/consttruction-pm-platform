import assert from "node:assert/strict";
import test from "node:test";

import type { CapacityResolution, CapacitySegment, CapacityWriteResult } from "./p6-capacity-api.js";
import {
  describeCapacityError,
  getCapacityPanelLabels,
  renderCapacityPanel,
  renderCapacityProfile,
  renderCapacityResolution,
  renderCapacityWriteResult,
} from "./p6-capacity-panel.js";

const SEGMENTS: CapacitySegment[] = [
  {
    resource_id: "RPS-CIVIL-CREW",
    identity: "a".repeat(64),
    max_units: "8",
    unit_basis: "day",
    hours_per_time_period: "8",
    units_per_hour: "1",
    effective_from: "2026-09-21",
    effective_to: "2026-10-14",
    source: "manual-entry:preview-planner",
  },
  {
    resource_id: "RPS-CIVIL-CREW",
    identity: "b".repeat(64),
    max_units: "12",
    unit_basis: "day",
    hours_per_time_period: "8",
    units_per_hour: "1.5",
    effective_from: "2026-10-15",
    effective_to: null,
    source: "manual-entry:preview-planner",
  },
];

test("capacity panel is bilingual, exposes edit and resolve controls and avoids product branding", () => {
  const en = renderCapacityPanel(SEGMENTS, getCapacityPanelLabels("en"), "en");
  assert.match(en, /Resource Max Units \/ Time/);
  assert.match(en, /data-capacity-write-form/);
  assert.match(en, /data-capacity-close/);
  assert.match(en, /data-capacity-resolve-form/);
  assert.match(en, /never in this panel/);
  assert.match(en, /RPS-CIVIL-CREW/);
  assert.doesNotMatch(en, /Oracle|Primavera|\bP6\b|https?:\/\//i);

  const fa = renderCapacityPanel(SEGMENTS, getCapacityPanelLabels("fa"), "fa");
  assert.match(fa, /حداکثر واحد \/ زمان منبع/);
  assert.match(fa, /ثبت تغییر اثربخش/);
  assert.match(fa, /تعیین ظرفیت برای یک دوره/);
  assert.match(fa, /هیچ محاسبه‌ای/);
});

test("capacity panel shows an explicit empty state when nothing is registered", () => {
  const html = renderCapacityPanel(
    [],
    getCapacityPanelLabels("en"),
    "en",
  );
  assert.match(html, /No resource capacity is registered/);
  assert.match(html, /data-capacity-write-form/);
  assert.match(html, /data-capacity-resource-select disabled/);
});

test("capacity profile renders only server values and marks the open-ended segment", () => {
  const html = renderCapacityProfile(
    "RPS-CIVIL-CREW",
    SEGMENTS,
    getCapacityPanelLabels("en"),
  );
  assert.match(html, /2026-09-21/);
  assert.match(html, /2026-10-14/);
  assert.match(html, /Open-ended/);
  assert.match(html, /manual-entry:preview-planner/);
  assert.match(html, /data-capacity-profile-resource="RPS-CIVIL-CREW"/);
  assert.match(html, new RegExp(`data-capacity-identity="${"a".repeat(64)}"`));
  // Displayed exactly as the server returned them.
  assert.match(html, />8<\/td>/);
  assert.match(html, />12<\/td>/);
  assert.match(html, />1\.5<\/td>/);
  assert.doesNotMatch(html, /Oracle|Primavera|\bP6\b|https?:\/\//i);
});

test("capacity profile escapes server text instead of injecting it", () => {
  const html = renderCapacityProfile(
    "<script>alert(1)</script>",
    [
      {
        ...SEGMENTS[0],
        source: "<img src=x onerror=alert(1)>",
      },
    ],
    getCapacityPanelLabels("en"),
  );
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.doesNotMatch(html, /<script>alert/);
  assert.doesNotMatch(html, /<img src=x/);
});

test("capacity profile has an explicit empty state", () => {
  const html = renderCapacityProfile(
    "NEW-CREW",
    [],
    getCapacityPanelLabels("en"),
  );
  assert.match(html, /No effective capacity is registered/);
  assert.doesNotMatch(html, /<table/);
});

test("written capacity reports the supersession without rewriting history", () => {
  const result: CapacityWriteResult = {
    contract_version: "p6-resource-capacity-write-api.v1",
    kind: "resource_capacity_write",
    scope: { tenant_id: "t1", project_id: "p", revision: 7 },
    capacity: { ...SEGMENTS[1], identity: "c".repeat(64), max_units: "10", effective_from: "2026-11-01" },
    superseded: {
      identity: "b".repeat(64),
      replacement_identity: "d".repeat(64),
      effective_to: "2026-10-31",
    },
    status: "REGISTERED",
  };
  const html = renderCapacityWriteResult(
    result,
    getCapacityPanelLabels("en"),
  );
  assert.match(html, /registered the change/);
  assert.match(html, /prior open-ended segment was closed/);
  assert.match(html, new RegExp(`<code>${"c".repeat(64)}</code>`));
  assert.match(html, new RegExp(`<code>${"d".repeat(64)}</code>`));
  assert.match(html, /2026-11-01/);
  assert.doesNotMatch(html, /\{/);
});

test("resolution shows the exact server value and selected basis", () => {
  const result: CapacityResolution = {
    contract_version: "p6-resource-capacity-read-api.v1",
    kind: "resource_capacity_value",
    scope: { tenant_id: "t1", project_id: "p", revision: 7 },
    resource_id: "RPS-CIVIL-CREW",
    period: "2026-11-02",
    capacity: "50",
    basis: "week",
    source: "manual-entry:preview-planner",
    identity: "c".repeat(64),
    status: "RESOLVED",
  };
  const html = renderCapacityResolution(
    result,
    getCapacityPanelLabels("en"),
    "en",
  );
  assert.match(html, /data-capacity-resolve-value="50"/);
  assert.match(html, />50<\/strong>/);
  assert.match(html, /Week/);
  assert.match(html, /manual-entry:preview-planner/);
});

test("capacity errors distinguish permission, revision, conflict and missing capacity", () => {
  const labels = getCapacityPanelLabels("en");
  assert.match(
    describeCapacityError(
      "authorization denied for permission=project.write",
      labels,
    ),
    /denied this operation/,
  );
  assert.match(describeCapacityError("REVISION_CONFLICT", labels), /revision changed/);
  assert.match(
    describeCapacityError("CAPACITY_REPLACEMENT_REQUIRES_OPEN_RANGE", labels),
    /conflicts with the stored/,
  );
  assert.match(
    describeCapacityError("CAPACITY_SEGMENT_NOT_EFFECTIVE", labels),
    /No capacity segment is effective/,
  );
  assert.match(
    describeCapacityError("RESOURCE_CAPACITY_NOT_REGISTERED", labels),
    /No capacity is registered/,
  );
  assert.match(describeCapacityError("NETWORK_ERROR", labels), /could not be reached/);
  assert.match(describeCapacityError("SESSION_NOT_FOUND", labels), /session/);
});
