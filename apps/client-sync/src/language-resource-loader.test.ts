import assert from "node:assert/strict";
import test from "node:test";

import {
  LanguageResourceLoader,
  resolveMessage,
} from "./language-resource-loader.ts";

const files: Record<string, string> = {
  "translations.json": JSON.stringify({
    "nav.dashboard": "داشبورد",
    "activity.duration": "مدت",
  }),
  "glossary.json": JSON.stringify({
    "glossary.earned_schedule": "Earned Schedule",
  }),
  "help.json": JSON.stringify({
    "help.calendar": "راهنمای تقویم",
  }),
  "reports.json": JSON.stringify({
    "report.progress": "گزارش پیشرفت",
  }),
};

test("loads deterministic language resources", async () => {
  const loader = new LanguageResourceLoader({
    async readText(_artifact, path) {
      const value = files[path];
      if (value === undefined) throw new Error("MISSING_RESOURCE");
      return value;
    },
  });

  const bundle = await loader.load("fa", "1.0.0", new Uint8Array([1]), {
    translation: "translations.json",
    glossary: "glossary.json",
    help: "help.json",
    reports: "reports.json",
  });

  assert.equal(bundle.languageTag, "fa");
  assert.equal(bundle.translations["nav.dashboard"], "داشبورد");
  assert.equal(bundle.glossary["glossary.earned_schedule"], "Earned Schedule");
  assert.equal(resolveMessage(bundle, "activity.duration"), "مدت");
});

test("falls back to base language for missing translation key", async () => {
  const loader = new LanguageResourceLoader({
    async readText(_artifact, path) {
      return path === "translations.json"
        ? JSON.stringify({"nav.dashboard": "داشبورد"})
        : JSON.stringify({});
    },
  });

  const bundle = await loader.load("fa", "1.0.0", new Uint8Array(), {
    translation: "translations.json",
    glossary: "glossary.json",
    help: "help.json",
    reports: "reports.json",
  });
  const base = {
    ...bundle,
    languageTag: "en",
    translations: {"activity.duration": "Duration"},
  };
  assert.equal(resolveMessage(bundle, "activity.duration", base), "Duration");
});

test("rejects invalid resource JSON", async () => {
  const loader = new LanguageResourceLoader({
    async readText() {
      return "{bad";
    },
  });

  await assert.rejects(
    loader.load("fa", "1.0.0", new Uint8Array(), {
      translation: "translations.json",
      glossary: "glossary.json",
      help: "help.json",
      reports: "reports.json",
    }),
    /INVALID_TRANSLATION_RESOURCE_JSON/,
  );
});


test("rejects absolute resource paths", async () => {
  const loader = new LanguageResourceLoader({
    async readText() {
      return "{}";
    },
  });

  await assert.rejects(
    loader.load("fa", "1.0.0", new Uint8Array([1]), {
      translation: "/translations.json",
      glossary: "glossary.json",
      help: "help.json",
      reports: "reports.json",
    }),
    /INVALID_LANGUAGE_RESOURCE_PATH/,
  );
});

test("rejects parent traversal resource paths", async () => {
  const loader = new LanguageResourceLoader({
    async readText() {
      return "{}";
    },
  });

  await assert.rejects(
    loader.load("fa", "1.0.0", new Uint8Array([1]), {
      translation: "../translations.json",
      glossary: "glossary.json",
      help: "help.json",
      reports: "reports.json",
    }),
    /INVALID_LANGUAGE_RESOURCE_PATH/,
  );
});
