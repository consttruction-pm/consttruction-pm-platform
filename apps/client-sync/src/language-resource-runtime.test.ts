import assert from "node:assert/strict";
import test from "node:test";

import { LanguageResourceRuntime } from "./language-resource-runtime.ts";

test("installs and resolves a language resource bundle locally", async () => {
  const runtime = new LanguageResourceRuntime({
    async readText(_artifact, path) {
      const resources: Record<string, string> = {
        "translations.json": JSON.stringify({
          "nav.dashboard": "داشبورد",
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
      return resources[path] ?? "{}";
    },
  });

  await runtime.installBundle("fa", "1.0.0", new Uint8Array([1]), {
    translation: "translations.json",
    glossary: "glossary.json",
    help: "help.json",
    reports: "reports.json",
  });

  assert.equal(runtime.translate("fa", "1.0.0", "nav.dashboard"), "داشبورد");
  assert.equal(
    runtime.translate("fa", "1.0.0", "activity.duration"),
    null,
  );
});

test("can use a locally installed fallback bundle", async () => {
  const runtime = new LanguageResourceRuntime({
    async readText(_artifact, path) {
      if (path === "translations.json") {
        return JSON.stringify(
          path === "translations.json" ? {} : {},
        );
      }
      return "{}";
    },
  });

  const baseReaderRuntime = new LanguageResourceRuntime({
    async readText(_artifact, path) {
      if (path === "translations.json") {
        return JSON.stringify({
          "activity.duration": "Duration",
        });
      }
      return "{}";
    },
  });

  await runtime.installBundle("fa", "1.0.0", new Uint8Array([1]), {
    translation: "translations.json",
    glossary: "glossary.json",
    help: "help.json",
    reports: "reports.json",
  });
  await baseReaderRuntime.installBundle("en", "1.0.0", new Uint8Array([2]), {
    translation: "translations.json",
    glossary: "glossary.json",
    help: "help.json",
    reports: "reports.json",
  });

  assert.equal(
    baseReaderRuntime.translate("en", "1.0.0", "activity.duration"),
    "Duration",
  );
});
