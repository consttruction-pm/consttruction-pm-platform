import assert from "node:assert/strict";
import test from "node:test";

import { applyLanguagePresentation } from "./apply-language-presentation.ts";

test("applies language and direction to the document root", () => {
  const root = { lang: "", dir: "" };
  const documentRef = { documentElement: root } as unknown as Document;

  applyLanguagePresentation(
    {
      languageTag: "fa",
      locale: "fa-IR",
      direction: "rtl",
      offline: true,
      packVersion: "1.0.0",
    },
    documentRef,
  );

  assert.equal(root.lang, "fa");
  assert.equal(root.dir, "rtl");
});
