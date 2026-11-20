import assert from "node:assert/strict";
import test from "node:test";

import {
  WORKBENCH_COPY,
  WORKBENCH_LOCALES,
  environmentHref,
  formatWorkbenchDate,
  formatWorkbenchNumber,
  resolveEnvironments,
  resolveWorkbenchLocale,
  workbenchDirection,
  workbenchHtmlLang,
} from "./personal-workbench.js";

test("the workbench ships the ten approved locales", () => {
  assert.deepEqual([...WORKBENCH_LOCALES], ["en", "fa", "de", "zh", "ar", "fr", "ja", "ko", "ru", "tr"]);
  const keys = Object.keys(WORKBENCH_COPY.en) as Array<keyof typeof WORKBENCH_COPY.en>;
  assert.ok(keys.length >= 20);
  for (const locale of WORKBENCH_LOCALES) {
    const copy = WORKBENCH_COPY[locale];
    assert.deepEqual(Object.keys(copy).sort(), [...keys].sort(), locale);
    for (const key of keys) assert.ok(copy[key].trim().length > 1, `${locale}:${key}`);
    assert.notEqual(copy.title, "", locale);
  }
  for (const key of ["title", "subtitle", "projects", "environments", "open", "restricted"] as const) {
    assert.notEqual(WORKBENCH_COPY.fa[key], WORKBENCH_COPY.en[key], `fa:${key}`);
    assert.notEqual(WORKBENCH_COPY.de[key], WORKBENCH_COPY.en[key], `de:${key}`);
    assert.notEqual(WORKBENCH_COPY.tr[key], WORKBENCH_COPY.en[key], `tr:${key}`);
  }
});

test("locale resolution normalizes regional tags and falls back to English", () => {
  assert.equal(resolveWorkbenchLocale("fa-IR"), "fa");
  assert.equal(resolveWorkbenchLocale("tr-TR"), "tr");
  assert.equal(resolveWorkbenchLocale("zh-Hans-CN"), "zh");
  assert.equal(resolveWorkbenchLocale("de-AT"), "de");
  assert.equal(resolveWorkbenchLocale("EN-us"), "en");
  assert.equal(resolveWorkbenchLocale("pt-BR"), "en");
  assert.equal(resolveWorkbenchLocale(null), "en");
  assert.equal(workbenchDirection("fa"), "rtl");
  assert.equal(workbenchDirection("ar"), "rtl");
  for (const locale of WORKBENCH_LOCALES) {
    if (locale === "fa" || locale === "ar") continue;
    assert.equal(workbenchDirection(locale), "ltr", locale);
  }
  assert.equal(workbenchHtmlLang("zh"), "zh-CN");
  assert.equal(workbenchHtmlLang("tr"), "tr-TR");
});

test("environment availability follows server responses, not a role list", () => {
  const granted = resolveEnvironments({ projectsOk: true, enterpriseOk: true });
  assert.deepEqual(granted, [
    { id: "engineering", available: true, reason: "authorized" },
    { id: "enterprise", available: true, reason: "authorized" },
  ]);
  const engineeringOnly = resolveEnvironments({ projectsOk: true, enterpriseOk: false });
  assert.equal(engineeringOnly[0].available, true);
  assert.equal(engineeringOnly[1].available, false);
  assert.equal(engineeringOnly[1].reason, "no_server_grant");
  const unknown = resolveEnvironments({ projectsOk: false, enterpriseOk: null });
  assert.equal(unknown[0].available, false);
  assert.equal(unknown[1].reason, "server_unknown");
});

test("environment links stay inside the two real product entries", () => {
  assert.equal(environmentHref("engineering"), "/app?view=live");
  assert.equal(environmentHref("engineering", "preview-rps-01"), "/app?project=preview-rps-01&view=live");
  assert.equal(environmentHref("engineering", "a b/c"), "/app?project=a%20b%2Fc&view=live");
  assert.equal(environmentHref("enterprise"), "/cubi/enterprise/dashboard");
});

test("dates and numbers are locale aware", () => {
  const iso = "2026-11-20T10:00:00+00:00";
  const en = formatWorkbenchDate("en", iso);
  const fa = formatWorkbenchDate("fa", iso);
  assert.ok(en.length > 5);
  assert.notEqual(en, fa);
  assert.match(fa, /[۰-۹]/, "Persian dates should use Persian digits");
  assert.equal(formatWorkbenchNumber("en", 1234567), "1,234,567");
  assert.match(formatWorkbenchNumber("fa", 1234567), /[۰-۹]/);
  assert.equal(formatWorkbenchDate("de", "not-a-date"), "not-a-date");
});
