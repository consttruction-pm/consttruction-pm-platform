import assert from "node:assert/strict";
import test from "node:test";

import { publicationTone, translationTone } from "./enterprise/pages/knowledge.js";

test("publicationTone never paints an unpublished card as success", () => {
  assert.equal(publicationTone("published"), "success");
  assert.equal(publicationTone("validated"), "info");
  assert.equal(publicationTone("draft"), "warning");
  assert.equal(publicationTone("rejected"), "danger");
  assert.equal(publicationTone("retired"), "danger");
  assert.equal(publicationTone("unknown"), "neutral");
  assert.equal(publicationTone(""), "neutral");
});

test("translationTone keeps per-locale translation state independent", () => {
  assert.equal(translationTone("published"), "success");
  assert.equal(translationTone("approved"), "success");
  assert.equal(translationTone("translated"), "info");
  assert.equal(translationTone("draft"), "warning");
  assert.equal(translationTone("review_required"), "warning");
  assert.equal(translationTone("missing"), "neutral");
  assert.equal(translationTone("retired"), "neutral");
  assert.equal(translationTone("other"), "neutral");
});
