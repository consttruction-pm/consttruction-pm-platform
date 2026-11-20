import assert from "node:assert/strict";
import test from "node:test";
import {
  BASE_PATH,
  normalizePath,
  pageHref,
  resolvePage,
  safeNextPath,
} from "./enterprise/router.js";
import { enterpriseTier, environmentAccess, isEnterpriseWriter } from "./enterprise/session.js";
import {
  ENTERPRISE_LOCALES,
  isRtl,
  normalizeLocale,
  translator,
} from "./enterprise/i18n.js";
import { validate, type Draft } from "./enterprise/pages/workflows.js";

test("every Enterprise page resolves to exactly one route", () => {
  const expectations: [string, string][] = [
    ["/cubi/", "home"],
    ["/cubi/login/", "login"],
    ["/cubi/roles/", "roles"],
    ["/cubi/workbench/", "workbench"],
    ["/cubi/environments/", "environments"],
    ["/cubi/enterprise/dashboard/", "dashboard"],
    ["/cubi/enterprise/portfolio/", "portfolio"],
    ["/cubi/enterprise/projects/", "projects"],
    ["/cubi/enterprise/access/", "access"],
    ["/cubi/enterprise/tasks/", "tasks"],
    ["/cubi/enterprise/workflows/", "workflows"],
    ["/cubi/enterprise/approvals/", "approvals"],
    ["/cubi/enterprise/resources/", "resources"],
    ["/cubi/enterprise/reports/", "reports"],
    ["/cubi/enterprise/knowledge/", "knowledge"],
  ];
  for (const [path, page] of expectations) {
    assert.equal(resolvePage(path), page, path);
    assert.equal(resolvePage(path.replace(/\/$/, "")), page, `${path} without slash`);
  }
  assert.equal(resolvePage("/app/"), "not-found");
  assert.equal(resolvePage("/cubi/enterprise/unknown/"), "not-found");
  assert.equal(normalizePath("/cubi//enterprise/tasks///"), "/cubi//enterprise/tasks/");
});

test("pageHref builds stable /cubi links and drops empty parameters", () => {
  assert.equal(pageHref("home"), `${BASE_PATH}/`);
  assert.equal(pageHref("tasks"), `${BASE_PATH}/enterprise/tasks/`);
  assert.equal(
    pageHref("resource" as never, {}),
    `${BASE_PATH}/__not_found__/`,
  );
  assert.equal(
    pageHref("projects", { project: "p-1", empty: "", missing: null }),
    `${BASE_PATH}/enterprise/projects/?project=p-1`,
  );
});

test("safeNextPath refuses anything outside the Enterprise application", () => {
  assert.equal(safeNextPath("/cubi/enterprise/tasks/"), "/cubi/enterprise/tasks/");
  assert.equal(safeNextPath("//evil.example"), `${BASE_PATH}/workbench/`);
  assert.equal(safeNextPath("/app/"), `${BASE_PATH}/workbench/`);
  assert.equal(safeNextPath("https://evil.example/cubi/"), `${BASE_PATH}/workbench/`);
  assert.equal(safeNextPath("/cubi/\u0000"), `${BASE_PATH}/workbench/`);
  assert.equal(safeNextPath(null), `${BASE_PATH}/workbench/`);
});

test("enterprise tier is independent from project roles", () => {
  assert.equal(enterpriseTier(["project_admin"]), null);
  assert.equal(enterpriseTier(["planner", "enterprise_viewer"]), "viewer");
  assert.equal(enterpriseTier(["enterprise_user", "enterprise_viewer"]), "user");
  assert.equal(enterpriseTier(["enterprise_admin"]), "admin");
  assert.equal(isEnterpriseWriter(["enterprise_viewer"]), false);
  assert.equal(isEnterpriseWriter(["enterprise_user"]), true);
  assert.equal(isEnterpriseWriter(["project_admin"]), false);

  const denied = environmentAccess({
    user_id: "u-1", tenant_id: "t-1", roles: ["project_admin"],
  } as never);
  assert.equal(denied.enterprise.allowed, false);
  assert.equal(denied.engineering.allowed, true);

  const allowed = environmentAccess({
    user_id: "u-2", tenant_id: "t-1", roles: ["project_admin", "enterprise_admin"],
  } as never);
  assert.equal(allowed.enterprise.allowed, true);
  assert.equal(allowed.enterprise.tier, "admin");
  assert.equal(environmentAccess(null).enterprise.allowed, false);
});

test("all ten locales are addressable and right-to-left is explicit", () => {
  const expected = ["fa", "en", "de", "zh", "ar", "fr", "ja", "ko", "ru", "tr"];
  assert.deepEqual([...ENTERPRISE_LOCALES], expected);
  assert.equal(normalizeLocale("tr-TR"), "tr");
  assert.equal(normalizeLocale("fa-IR"), "fa");
  assert.equal(normalizeLocale("unknown"), "en");
  for (const locale of ENTERPRISE_LOCALES) {
    assert.equal(isRtl(locale), locale === "fa" || locale === "ar", locale);
    const t = translator(locale);
    assert.ok(t("page.tasks.title").length > 0, locale);
    assert.ok(t("common.refresh").length > 0, locale);
  }
  // Missing keys fall back to English instead of leaking a raw key.
  assert.equal(translator("de")("page.tasks.subtitle"), translator("en")("page.tasks.subtitle"));
});

test("workflow validation rejects structural defects and accepts a sound draft", () => {
  const base: Draft = {
    id: "draft",
    name: "Change request",
    revision: 1,
    updated_at: "2026-01-01T00:00:00Z",
    steps: [
      { id: "draft", name: "Draft", terminal: false },
      { id: "done", name: "Done", terminal: true },
    ],
    transitions: [{ from: "draft", to: "done", label: "Submit" }],
  };
  assert.deepEqual(validate(base), []);

  const duplicate = structuredClone(base);
  duplicate.steps.push({ id: "draft", name: "Duplicate", terminal: false });
  assert.ok(validate(duplicate).some((message) => message.includes("Duplicate step ID")));

  const noTerminal = structuredClone(base);
  noTerminal.steps[1].terminal = false;
  assert.ok(validate(noTerminal).some((message) => message.includes("terminal")));

  const missing = structuredClone(base);
  missing.transitions.push({ from: "draft", to: "ghost", label: "Break" });
  assert.ok(validate(missing).some((message) => message.includes("missing step")));

  const selfLoop = structuredClone(base);
  selfLoop.transitions.push({ from: "draft", to: "draft", label: "Loop" });
  assert.ok(validate(selfLoop).some((message) => message.includes("itself")));

  const duplicateTransition = structuredClone(base);
  duplicateTransition.transitions.push({ from: "draft", to: "done", label: "Again" });
  assert.ok(validate(duplicateTransition).some((message) => message.includes("Duplicate transition")));

  const unreachable = structuredClone(base);
  unreachable.steps.push({ id: "island", name: "Island", terminal: false });
  assert.ok(validate(unreachable).some((message) => message.includes("unreachable")));

  assert.ok(validate({ ...base, name: "  " }).some((message) => message.includes("name")));
});
