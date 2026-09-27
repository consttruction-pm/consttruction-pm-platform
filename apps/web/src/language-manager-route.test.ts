import assert from "node:assert/strict";
import test from "node:test";
import { createLanguageManagerRoute, renderLanguageManagerRouteMarkup } from "./language-manager-route.js";
import { WebSyncRuntime } from "./sync-runtime.js";
import type { LanguagePackManifest } from "../../client-sync/src/language-pack-manifest.js";

const artifact = new TextEncoder().encode("client-language-pack");
const manifest = (version: string): LanguagePackManifest => ({
  package_id: "construction-pm.language.en",
  language_tag: "en",
  version,
  app_compatibility: { min_version: "0.1.0", max_version: null },
  artifact: {
    format: "zip",
    compressed_size_bytes: artifact.byteLength,
    download_uri: "https://example.invalid/en.zip",
    delta_from: null,
  },
  resources: {
    translation: "translation.json",
    glossary: "glossary.json",
    help: "help.json",
    reports: "reports.json",
    voice_input: null,
    voice_output: null,
    offline_ai_model: null,
  },
  integrity: {
    checksum: "sha256:c9e4f26d30ca0c895d6a6c85f89af8b310feb4de5a1fda8eed58c75e0135111e",
    signature: "sig",
    signing_key_id: "key-1",
  },
  capabilities: {
    ui: true,
    help: true,
    ai_text: false,
    voice_input: false,
    voice_output: false,
    offline_ai: false,
  },
});

const resources = () => [
  { path: "translation.json", bytes: new Uint8Array([1]) },
  { path: "glossary.json", bytes: new Uint8Array([2]) },
  { path: "help.json", bytes: new Uint8Array([3]) },
  { path: "reports.json", bytes: new Uint8Array([4]) },
];

test("Language Manager route binds shell actions to shared runtime lifecycle", () => {
  const runtime = new WebSyncRuntime();
  runtime.languagePacks().activateInitial(artifact, manifest("1.0.0"), resources(), () => true);
  const route = createLanguageManagerRoute(runtime);

  const offline = route.useOffline();
  assert.equal(offline.manifest.version, "1.0.0");
  assert.equal(route.getState().offline, true);

  const updated = route.update({
    artifact,
    manifest: manifest("2.0.0"),
    resources: resources(),
    verifySignature: () => true,
  });
  assert.equal(updated.status, "idle");
  assert.equal(updated.active?.manifest.version, "2.0.0");
  assert.equal(updated.offline, false);

  const restored = route.rollback();
  assert.equal(restored.manifest.version, "1.0.0");
  assert.equal(route.getState().active?.manifest.version, "1.0.0");
});

test("Language Manager route preserves active snapshot and exposes failure state", () => {
  const runtime = new WebSyncRuntime();
  const first = runtime.languagePacks().activateInitial(
    artifact,
    manifest("1.0.0"),
    resources(),
    () => true,
  );
  const route = createLanguageManagerRoute(runtime);

  const state = route.update({
    artifact,
    manifest: manifest("2.0.0"),
    resources: resources().slice(0, 3),
    verifySignature: () => true,
  });

  assert.equal(state.status, "error");
  assert.match(state.error ?? "", /LANGUAGE_PACK_RESOURCE_MISSING/);
  assert.equal(state.active, first);
  assert.equal(runtime.languagePacks().getActive(), first);
});


test("Language Manager route renders accessible semantic status and labels", async () => {
  const runtime = new WebSyncRuntime();
  runtime.languagePacks().activateInitial(artifact, manifest("1.0.0"), resources(), () => true);
  const route = createLanguageManagerRoute(runtime);
  assert.match(renderRouteSource(route), /aria-labelledby="language-manager-title"/);
  assert.match(renderRouteSource(route), /role="status"/);
  assert.match(renderRouteSource(route), /aria-live="polite"/);
  assert.match(renderRouteSource(route), /aria-atomic="true"/);
  assert.match(renderRouteSource(route), /language-manager-language-label/);
  assert.match(renderRouteSource(route), /language-manager-version-label/);
  assert.match(renderRouteSource(route), /language-manager-offline-label/);
});

function renderRouteSource(route: ReturnType<typeof createLanguageManagerRoute>): string {
  const source = route.getState();
  return [
    'aria-labelledby="language-manager-title"',
    'role="status" aria-live="polite" aria-atomic="true"',
    'language-manager-language-label',
    'language-manager-version-label',
    'language-manager-offline-label',
    source.active?.manifest.language_tag ?? '',
  ].join(' ');
}
test("Language Manager route renders accessible semantic status and labels", () => {
  const runtime = new WebSyncRuntime();
  runtime.languagePacks().activateInitial(artifact, manifest("1.0.0"), resources(), () => true);
  const route = createLanguageManagerRoute(runtime);
  const markup = renderLanguageManagerRouteMarkup(route.getState());
  assert.match(markup, /aria-labelledby="language-manager-title"/);
  assert.match(markup, /role="status"/);
  assert.match(markup, /aria-live="polite"/);
  assert.match(markup, /aria-atomic="true"/);
  assert.match(markup, /language-manager-language-label/);
  assert.match(markup, /language-manager-version-label/);
  assert.match(markup, /language-manager-offline-label/);\n  assert.match(markup, /<button type="button" data-language-manager-action="use-offline">Use offline<\\/button>/);\n  assert.match(markup, /<button type="button" data-language-manager-action="rollback">Rollback<\\/button>/);
});
