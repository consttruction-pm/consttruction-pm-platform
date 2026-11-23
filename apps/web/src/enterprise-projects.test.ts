import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import { gunzipSync } from "node:zlib";

import { ApiError, type ProjectSummary } from "./enterprise/api.js";
import {
  ENTERPRISE_LOCALES,
  RTL_LOCALES,
  hasReviewedContent,
  isRtl,
  localeHasMessage,
  translator,
} from "./enterprise/i18n.js";
import {
  ENTERPRISE_ICON_NAMES,
  enterpriseIconShapeCount,
} from "./enterprise/icons.js";
import {
  PROJECT_TABS,
  filterAndSortProjects,
  isProjectSort,
  isProjectTab,
  projectErrorKind,
  projectStatusLabel,
} from "./enterprise/pages/projects.js";

/**
 * ENT-07 — Enterprise projects register and project portal.
 *
 * The register must list the three durable shared reference projects next to
 * every other project the policy returns, separate each project's data, keep
 * the selection in the URL, and expose a real toolbar (search, status, sort,
 * refresh). These tests cover the pure surface; the Preview E2E covers the
 * rendered page against the real HTTP runtime.
 */

const repoRoot = join(process.cwd(), "..", "..");
const webSrc = join(process.cwd(), "src", "enterprise");

/** Names/domains read from the shared bundle — the fixtures must match it. */
function referenceBundle(): Record<string, { name: string; domain: string; start: string }> {
  const raw = readFileSync(
    join(
      repoRoot,
      "src",
      "construction_pm",
      "importing",
      "data",
      "cubi_reference_projects.v1.json.gz",
    ),
  );
  const bundle = JSON.parse(gunzipSync(raw).toString("utf8")) as {
    projects: Record<string, { project: Record<string, string> }>;
  };
  const result: Record<string, { name: string; domain: string; start: string }> = {};
  for (const [projectId, entry] of Object.entries(bundle.projects)) {
    result[projectId] = {
      name: entry.project.project_name,
      domain: entry.project.sector,
      start: entry.project.planned_start,
    };
  }
  return result;
}

const BUNDLE = referenceBundle();
const REFERENCE_IDS = ["CUBI-REF-001", "CUBI-REF-002", "CUBI-REF-003"];

const REFERENCE_PROJECTS: ProjectSummary[] = REFERENCE_IDS.map((projectId) => ({
  project_id: projectId,
  tenant_id: "tenant-demo",
  name: BUNDLE[projectId].name,
  revision: 1,
  business_domain: BUNDLE[projectId].domain,
  status: "active",
  start_date: BUNDLE[projectId].start,
}));

/** The two seeded Preview projects (see preview/fixtures.py). */
const MEMBER_PROJECTS: ProjectSummary[] = [
  {
    project_id: "preview-rps-01",
    tenant_id: "tenant-demo",
    name: "Riverside Pump Station Upgrade",
    revision: 7,
    business_domain: "infrastructure",
    status: "active",
    start_date: "2026-09-21",
  },
  {
    project_id: "preview-nse-02",
    tenant_id: "tenant-demo",
    name: "نوسازی سامانه شرقی",
    revision: 2,
    business_domain: "industrial",
    status: "active",
    start_date: "2027-02-02",
  },
];

/** Unit-only row that exercises the non-active status filter path. */
const RETIRED_PROJECT: ProjectSummary = {
  project_id: "demo-retired-01",
  tenant_id: "tenant-demo",
  name: "Retired Demonstration Project",
  revision: 3,
  business_domain: "construction",
  status: "inactive",
  start_date: "2024-04-01",
  finish_date: "2025-04-01",
};

const REGISTER: ProjectSummary[] = [
  ...REFERENCE_PROJECTS,
  ...MEMBER_PROJECTS,
  RETIRED_PROJECT,
];

const byId = (rows: ProjectSummary[]): string[] => rows.map((row) => row.project_id);

test("fixtures match the durable shared reference bundle and are not invented", () => {
  assert.deepEqual(Object.keys(BUNDLE).sort(), REFERENCE_IDS);
  for (const project of REFERENCE_PROJECTS) {
    assert.equal(project.name, BUNDLE[project.project_id].name);
    assert.equal(project.business_domain, BUNDLE[project.project_id].domain);
    assert.equal(project.start_date, BUNDLE[project.project_id].start);
  }
});

test("the register lists the three references alongside the other authorized projects", () => {
  const rows = filterAndSortProjects(REGISTER, { q: "", status: "all", sort: "name" }, "en");
  assert.equal(rows.length, REGISTER.length);
  for (const projectId of REFERENCE_IDS) {
    assert.ok(byId(rows).includes(projectId), `${projectId} must appear in the register`);
  }
  assert.deepEqual(byId(rows).slice(0, 3), ["CUBI-REF-003", "CUBI-REF-002", "demo-retired-01"]);
});

test("a same-tenant user without personal membership still sees every reference", () => {
  // The server list for such a user is exactly the reference union; the
  // register must render it without a membership hint or a write affordance.
  const rows = filterAndSortProjects(REFERENCE_PROJECTS, { q: "", status: "all", sort: "name" }, "en");
  assert.equal(rows.length, 3);
  for (const project of rows) {
    assert.equal(project.tenant_id, "tenant-demo");
  }
});

test("each project keeps its own data when the selection changes", () => {
  const one = filterAndSortProjects(REGISTER, { q: "CUBI-REF-001", status: "all", sort: "name" }, "en");
  assert.deepEqual(byId(one), ["CUBI-REF-001"]);
  assert.equal(one[0]?.business_domain, BUNDLE["CUBI-REF-001"].domain);
  assert.equal(one[0]?.revision, 1);
  assert.notEqual(one[0]?.business_domain, BUNDLE["CUBI-REF-002"].domain);
  assert.notEqual(one[0]?.name, BUNDLE["CUBI-REF-003"].name);
});

test("search matches name, project id and business domain, case-insensitively", () => {
  const search = (q: string) =>
    byId(filterAndSortProjects(REGISTER, { q, status: "all", sort: "name" }, "en"));

  assert.deepEqual(search("petrochemical"), ["CUBI-REF-001"]);
  assert.deepEqual(search("REF-002"), ["CUBI-REF-002"]);
  assert.deepEqual(search("water"), ["CUBI-REF-002"]);
  assert.deepEqual(search("riverside pump"), ["preview-rps-01"]);
  assert.deepEqual(search("نوسازی"), ["preview-nse-02"]);
  assert.deepEqual(search("  "), byId(filterAndSortProjects(REGISTER, { q: "", status: "all", sort: "name" }, "en")));
  assert.deepEqual(search("nothing matches this"), []);
});

test("the status filter narrows to one real status and keeps all rows for 'all'", () => {
  const status = (value: string) =>
    byId(filterAndSortProjects(REGISTER, { q: "", status: value, sort: "name" }, "en"));
  assert.equal(status("all").length, REGISTER.length);
  assert.deepEqual(status("inactive"), ["demo-retired-01"]);
  assert.ok(status("active").every((projectId) => projectId !== "demo-retired-01"));
  assert.deepEqual(status("archived"), []);
});

test("each sort order is deterministic and uses the requested field", () => {
  const sorted = (sort: "name" | "revision" | "start" | "finish", rows = REGISTER) =>
    byId(filterAndSortProjects(rows, { q: "", status: "all", sort }, "en"));

  const byName = sorted("name");
  assert.deepEqual(byName, [
    "CUBI-REF-003",
    "CUBI-REF-002",
    "demo-retired-01",
    "preview-rps-01",
    "CUBI-REF-001",
    "preview-nse-02",
  ]);
  assert.equal(new Set(byName).size, REGISTER.length);

  assert.deepEqual(sorted("revision").slice(0, 3), ["preview-rps-01", "demo-retired-01", "preview-nse-02"]);

  const byStart = sorted("start");
  assert.equal(byStart[0], "demo-retired-01");
  assert.equal(byStart[byStart.length - 1], "preview-nse-02");

  // Only one project carries a finish date; missing values never fabricate one.
  const byFinish = filterAndSortProjects(REGISTER, { q: "", status: "all", sort: "finish" }, "en");
  assert.ok(byFinish.some((project) => project.project_id === "demo-retired-01"));
  assert.equal(byFinish.filter((project) => project.finish_date).length, 1);
});

test("filtering and sorting never mutate the server array", () => {
  const original = [...REGISTER];
  filterAndSortProjects(REGISTER, { q: "cubi", status: "active", sort: "revision" }, "en");
  assert.deepEqual(REGISTER, original);
});

test("tab and sort query values are validated before they reach the page", () => {
  for (const tab of ["overview", "engineering", "resources", "documents", "risk", "reports"]) {
    assert.equal(isProjectTab(tab), true, `${tab} is a real tab`);
  }
  for (const value of ["", null, "Overview", "schedule", "risks", "unknown"]) {
    assert.equal(isProjectTab(value), false, `${String(value)} is not a tab id`);
  }
  for (const sort of ["name", "revision", "start", "finish"]) {
    assert.equal(isProjectSort(sort), true);
  }
  for (const value of ["", null, "revision_desc", "NAME"]) {
    assert.equal(isProjectSort(value), false);
  }
});

test("the portal exposes exactly the six ENT-07 tabs with drawn icons", () => {
  assert.deepEqual(
    PROJECT_TABS.map((tab) => tab.id),
    ["overview", "engineering", "resources", "documents", "risk", "reports"],
  );
  for (const tab of PROJECT_TABS) {
    assert.ok(tab.labelKey.startsWith("ent07.tab."));
    assert.ok(ENTERPRISE_ICON_NAMES.includes(tab.icon), `${tab.icon} is a registered icon`);
    assert.ok(enterpriseIconShapeCount(tab.icon) > 0, `${tab.icon} draws at least one shape`);
  }
});

test("every enterprise icon id draws a real SVG shape", () => {
  assert.equal(ENTERPRISE_ICON_NAMES.length, 13);
  for (const name of ENTERPRISE_ICON_NAMES) {
    assert.ok(enterpriseIconShapeCount(name) > 0, `${name} must not be empty`);
  }
});

test("the register and shell use the registered icons instead of the legacy squares", () => {
  const page = readFileSync(join(webSrc, "pages", "projects.ts"), "utf8");
  const shell = readFileSync(join(webSrc, "app.ts"), "utf8");
  for (const name of [
    "projects-search",
    "projects-filter-status",
    "projects-sort",
    "project-open",
  ]) {
    assert.ok(page.includes(`enterpriseIcon("${name}")`), `${name} must be drawn on the register`);
  }
  // The refresh button and tab bar pass the registered name through helpers.
  assert.ok(page.includes('"action-refresh"'), "the refresh control must use action-refresh");
  assert.ok(page.includes("enterpriseIcon(entry.icon)"), "each tab must draw its registered icon");
  assert.ok(shell.includes("nav-projects"), "the Projects navigation item must use nav-projects");
  assert.ok(shell.includes('enterpriseIcon("top-help"'), "the topbar help control must use top-help");
  assert.ok(!/(class|className): "cubi-icon"/.test(page), "no legacy flat icon span on the page");
});

test("status labels are localized in all ten locales and fall back to the raw value", () => {
  for (const locale of ENTERPRISE_LOCALES) {
    const t = translator(locale);
    for (const status of ["active", "completed", "pending", "draft", "archived", "locked"]) {
      const label = projectStatusLabel(status, t);
      assert.ok(label.length > 0);
      assert.notEqual(label, `status.${status}`, `${locale} must translate status.${status}`);
    }
    assert.equal(projectStatusLabel("suspended", t), "suspended");
    assert.notEqual(projectStatusLabel(null, t), "ent07.register.unknownStatus");
  }
  assert.equal(projectStatusLabel("active", translator("en")), "Active");
  assert.equal(projectStatusLabel("active", translator("fa")), "فعال");
});

test("error mapping separates unauthorized, forbidden, disconnected and generic failures", () => {
  assert.equal(projectErrorKind(new ApiError(401, "UNAUTHENTICATED", "no session")), "unauthenticated");
  assert.equal(projectErrorKind(new ApiError(403, "FORBIDDEN", "denied")), "forbidden");
  assert.equal(projectErrorKind(new ApiError(0, "NETWORK", "offline")), "disconnected");
  assert.equal(projectErrorKind(new ApiError(503, "UPSTREAM", "down")), "error");
  assert.equal(projectErrorKind(new Error("boom")), "error");
});

test("every ENT-07 label is authored in all ten locales, with no raw key leakage", () => {
  const source = readFileSync(join(webSrc, "i18n.ts"), "utf8");
  const keys = [...new Set([...source.matchAll(/"(ent07\.[a-zA-Z.]+)"/g)].map((match) => match[1]))].sort();
  assert.ok(keys.length >= 80, `expected the full ENT-07 key set, saw ${keys.length}`);
  for (const locale of ENTERPRISE_LOCALES) {
    const t = translator(locale);
    for (const key of keys) {
      assert.ok(localeHasMessage(locale, key), `${locale} must author ${key}`);
      const value = t(key);
      assert.ok(value.length > 0 && value !== key, `${locale} renders ${key}`);
    }
  }
});

test("the register copy is translated, not English fallback, outside en", () => {
  const en = translator("en");
  for (const locale of ENTERPRISE_LOCALES) {
    if (locale === "en") continue;
    const t = translator(locale);
    for (const key of [
      "ent07.register.title",
      "ent07.register.description",
      "ent07.register.searchPlaceholder",
      "ent07.register.emptyTitle",
      "ent07.register.errorTitle",
      "ent07.register.disconnectedTitle",
    ]) {
      assert.notEqual(t(key), en(key), `${locale} must translate ${key}`);
    }
  }
});

test("Persian and Arabic are the only RTL locales and keep reviewed content", () => {
  assert.deepEqual([...RTL_LOCALES].sort(), ["ar", "fa"]);
  assert.equal(isRtl("fa"), true);
  assert.equal(isRtl("ar"), true);
  for (const locale of ENTERPRISE_LOCALES) {
    if (locale === "fa" || locale === "ar") continue;
    assert.equal(isRtl(locale), false);
  }
  assert.equal(hasReviewedContent("fa"), true);
  assert.equal(hasReviewedContent("en"), true);
  assert.equal(hasReviewedContent("de"), false);
});
