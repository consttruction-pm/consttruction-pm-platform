import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import {
  ASSISTANT_GUIDE_TARGETS,
  WORKSPACE_MENU_KEYS,
  resolveAssistantGuide,
  resolveAssistantPage,
  type AssistantGuideQuery,
} from "./assistant-guide.js";
import { WORKSPACE_NAVIGATION } from "./workspace-navigation.js";

const root = process.cwd();
const workspaceView = readFileSync(join(root, "src/workspace-view.ts"), "utf8");
const mainSource = readFileSync(join(root, "src/main.ts"), "utf8");

const publicPages = ["home", "platform", "solutions", "resources", "contact", "login"] as const;

function guideFor(query: Partial<AssistantGuideQuery> & Pick<AssistantGuideQuery, "page">) {
  return resolveAssistantGuide({ state: "visitor", locale: "en", ...query });
}

test("every public page has real bilingual guidance and no invented action", () => {
  for (const page of publicPages) {
    for (const locale of ["en", "fa"]) {
      const guide = guideFor({ page, locale });
      assert.ok(guide.purpose.trim().length > 20, `${page}/${locale} needs a purpose`);
      assert.ok(guide.steps.length >= 2, `${page}/${locale} needs concrete steps`);
      assert.ok(
        guide.steps.every((step) => step.trim().length > 10),
        `${page}/${locale} steps must be sentences`,
      );
      assert.equal(guide.action, null, `${page}/${locale} must not fake an in-page action`);
      if (locale === "fa") {
        assert.match(guide.purpose, /[\u0600-\u06FF]/, `${page} must be translated`);
      }
    }
    const en = guideFor({ page, locale: "en" });
    const fa = guideFor({ page, locale: "fa" });
    assert.notEqual(en.purpose, fa.purpose, `${page} must not reuse English copy in Persian`);
  }
});

test("every workspace menu has guidance whose action target is a real control", () => {
  const navigationKeys = WORKSPACE_NAVIGATION.map((item) => item.key);
  assert.deepEqual([...WORKSPACE_MENU_KEYS].sort(), [...navigationKeys].sort());
  for (const menu of WORKSPACE_MENU_KEYS) {
    for (const locale of ["en", "fa"]) {
      const guide = guideFor({ page: "workspace", state: "ready", menu, locale });
      assert.ok(guide.purpose.trim().length > 20, `${menu}/${locale} needs a purpose`);
      assert.ok(guide.steps.length >= 2, `${menu}/${locale} needs steps`);
      assert.ok(guide.steps.length <= 4, `${menu}/${locale} must fit the assistant panel`);
      assert.ok(guide.action, `${menu}/${locale} must point at the next control`);
      assert.ok(
        ASSISTANT_GUIDE_TARGETS.includes(guide.action.target),
        `${menu}/${locale} target must be registered: ${guide.action.target}`,
      );
      assert.ok(guide.heading.includes(
        locale === "fa"
          ? WORKSPACE_NAVIGATION.find((item) => item.key === menu)!.label.fa
          : WORKSPACE_NAVIGATION.find((item) => item.key === menu)!.label.en,
      ), `${menu}/${locale} heading must name the surface`);
      if (locale === "fa") {
        assert.match(guide.purpose, /[\u0600-\u06FF]/);
        assert.match(guide.action.label, /[\u0600-\u06FF]/);
      }
    }
  }
});

test("registered action targets exist in the rendered product", () => {
  const sources = workspaceView + mainSource;
  for (const target of ASSISTANT_GUIDE_TARGETS) {
    if (target.startsWith("#")) {
      assert.match(sources, new RegExp(`id="${target.slice(1)}"`), `${target} must be rendered`);
    } else if (target.startsWith(".")) {
      assert.match(
        sources,
        new RegExp(`class="[^"]*${target.slice(1)}`),
        `${target} class must be rendered`,
      );
    } else if (target.startsWith("[")) {
      const attribute = target.slice(1, -1).split("=")[0];
      const datasetProperty = attribute
        .replace(/^data-/, "")
        .replace(/-([a-z])/g, (_match, letter: string) => letter.toUpperCase());
      assert.match(
        sources,
        new RegExp(
          `(?:${attribute.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}|dataset\\.${datasetProperty})`,
        ),
        `${target} attribute must be rendered`,
      );
    } else {
      assert.fail(`unexpected selector shape: ${target}`);
    }
  }
});

test("first-run states explain the next step without inventing data", () => {
  const noProject = guideFor({ page: "workspace", state: "no-project" });
  assert.match(noProject.purpose, /first-run|no project/i);
  assert.match(noProject.steps.join(" "), /2 and 120|Create and open/i);
  assert.equal(noProject.action, null);

  const multiple = guideFor({ page: "workspace", state: "multiple-projects", menu: "project" });
  assert.match(multiple.steps.join(" "), /Select a project|reopens automatically/i);

  const loading = guideFor({ page: "workspace", state: "loading" });
  assert.match(loading.steps.join(" "), /Retry|reference/i);
});

test("empty WBS and empty activities add an honest load step before menu steps", () => {
  const ready = guideFor({ page: "workspace", state: "ready", menu: "schedule" });
  const emptyActivities = guideFor({ page: "workspace", state: "empty-activities", menu: "schedule" });
  const emptyWbs = guideFor({ page: "workspace", state: "empty-wbs", menu: "schedule" });
  assert.equal(emptyActivities.steps.length, ready.steps.length + 1);
  assert.match(emptyActivities.steps[0], /No activities are loaded|Import \/ Export/i);
  assert.match(emptyWbs.steps[0], /No work breakdown is loaded/i);
  assert.notEqual(emptyActivities.steps[0], emptyWbs.steps[0]);
  assert.equal(emptyActivities.action?.target, "#cp-activity-grid");
});

test("page resolution understands Pages bases, language routes and unknown addresses", () => {
  assert.equal(resolveAssistantPage("/"), "home");
  assert.equal(resolveAssistantPage("/index.html"), "home");
  assert.equal(resolveAssistantPage("/fa/"), "home");
  assert.equal(resolveAssistantPage("/consttruction-pm-platform/platform/"), "platform");
  assert.equal(resolveAssistantPage("/consttruction-pm-platform/fa/contact/"), "contact");
  assert.equal(resolveAssistantPage("/consttruction-pm-platform/app/"), "workspace");
  assert.equal(resolveAssistantPage("/app/index.html"), "workspace");
  assert.equal(resolveAssistantPage("/consttruction-pm-platform/preview/login"), "login");
  assert.equal(resolveAssistantPage("/fa/resources/"), "resources");
  assert.equal(resolveAssistantPage("/does-not-exist/"), "unknown");
  assert.equal(resolveAssistantPage("/solutions/", "/consttruction-pm-platform/"), "solutions");
  assert.equal(
    resolveAssistantPage("/consttruction-pm-platform/fa/solutions/", "/consttruction-pm-platform/"),
    "solutions",
  );
});

test("loading, error and unknown workspace states stay honest", () => {
  const loading = guideFor({ page: "workspace", state: "loading" });
  assert.match(loading.steps.join(" "), /Retry|reference/i);

  const failed = guideFor({
    page: "workspace",
    state: "error",
    reference: "API_ERROR",
  });
  assert.match(failed.purpose, /could not open|request failed/i);
  assert.match(failed.steps.join(" "), /Retry|No project data was loaded/i);
  assert.equal(failed.action, null);
  assert.match(failed.commonError ?? "", /API_ERROR/);

  const persianFailure = guideFor({
    page: "workspace",
    state: "error",
    reference: "API_ERROR",
    locale: "fa",
  });
  assert.match(persianFailure.purpose, /[\u0600-\u06FF]/);
  assert.match(persianFailure.commonError ?? "", /API_ERROR/);

  // Without a code the guide does not invent one.
  const failedWithoutCode = guideFor({ page: "workspace", state: "error" });
  assert.doesNotMatch(failedWithoutCode.commonError ?? "", /Reference:/);
});

test("unknown addresses return a typed recovery guide", () => {
  const guide = guideFor({ page: "unknown", state: "unknown" });
  assert.equal(guide.page, "unknown");
  assert.equal(guide.action, null);
  assert.match(guide.steps.join(" "), /home|workspace/i);
});

test("an unrecognized locale still produces usable English guidance", () => {
  const guide = guideFor({ page: "platform", locale: "de" });
  assert.match(guide.purpose, /CUBI|project-controls/);
  assert.ok(guide.steps.length > 0);
});
