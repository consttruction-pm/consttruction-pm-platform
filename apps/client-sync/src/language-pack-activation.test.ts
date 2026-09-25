import assert from "node:assert/strict";
import test from "node:test";

import { LanguagePackActivationService } from "./language-pack-activation.ts";
import { InMemoryLanguagePackStore } from "./language-pack-store.ts";
import { LanguageResourceRuntime } from "./language-resource-runtime.ts";

test("activates a verified pack from local storage", async () => {
  const store = new InMemoryLanguagePackStore();
  const artifact = new Uint8Array([1]);

  await store.put({
    packageId: "construction-pm.language.fa",
    languageTag: "fa",
    version: "1.0.0",
    verified: true,
    artifact,
  });

  const resources = new LanguageResourceRuntime({
    async readText(_artifact, path) {
      const values: Record<string, string> = {
        "translations.json": JSON.stringify({
          "nav.dashboard": "داشبورد",
        }),
        "glossary.json": JSON.stringify({}),
        "help.json": JSON.stringify({}),
        "reports.json": JSON.stringify({}),
      };
      return values[path] ?? "{}";
    },
  });

  const service = new LanguagePackActivationService(store, resources);

  const active = await service.activate({
    package_id: "construction-pm.language.fa",
    language_tag: "fa",
    version: "1.0.0",
    app_compatibility: {
      min_version: "0.1.0",
      max_version: null,
    },
    artifact: {
      format: "zip",
      compressed_size_bytes: 1,
      download_uri: "https://example.invalid/fa.zip",
      delta_from: null,
    },
    resources: {
      translation: "translations.json",
      glossary: "glossary.json",
      help: "help.json",
      reports: "reports.json",
      voice_input: null,
      voice_output: null,
      offline_ai_model: null,
    },
    integrity: {
      checksum: "sha256:test",
      signature: "sig",
      signing_key_id: "key",
    },
    capabilities: {
      ui: true,
      help: true,
      ai_text: true,
      voice_input: false,
      voice_output: false,
      offline_ai: false,
    },
    rollback: {
      previous_version: null,
      rollback_supported: true,
    },
  });

  assert.equal(active.languageTag, "fa");
  assert.equal(service.current()?.version, "1.0.0");
  assert.equal(
    active.bundle.translations["nav.dashboard"],
    "داشبورد",
  );
});

test("rejects a missing verified pack", async () => {
  const service = new LanguagePackActivationService(
    new InMemoryLanguagePackStore(),
    new LanguageResourceRuntime({
      async readText() {
        return "{}";
      },
    }),
  );

  await assert.rejects(
    service.activate({
      package_id: "construction-pm.language.fa",
      language_tag: "fa",
      version: "1.0.0",
      app_compatibility: { min_version: "0.1.0", max_version: null },
      artifact: {
        format: "zip",
        compressed_size_bytes: 1,
        download_uri: "https://example.invalid/fa.zip",
        delta_from: null,
      },
      resources: {
        translation: "translations.json",
        glossary: "glossary.json",
        help: "help.json",
        reports: "reports.json",
      },
      integrity: {
        checksum: "sha256:x",
        signature: "sig",
      },
      capabilities: {
        ui: true,
        help: true,
        ai_text: true,
        voice_input: false,
        voice_output: false,
        offline_ai: false,
      },
    }),
    /LANGUAGE_PACK_NOT_VERIFIED/,
  );
});


test("keeps the previous active bundle until the replacement bundle loads", async () => {
  const store = new InMemoryLanguagePackStore();
  await store.put({
    packageId: "construction-pm.language.en",
    languageTag: "en",
    version: "1.0.0",
    verified: true,
    artifact: new Uint8Array([1]),
  });
  await store.put({
    packageId: "construction-pm.language.fa",
    languageTag: "fa",
    version: "1.0.0",
    verified: true,
    artifact: new Uint8Array([2]),
  });

  let failFa = true;
  const resources = new LanguageResourceRuntime({
    async readText(_artifact, path) {
      if (path === "fa.json" && failFa) {
        throw new Error("BROKEN_FA_RESOURCE");
      }
      return JSON.stringify({});
    },
  });

  const service = new LanguagePackActivationService(store, resources);
  await service.activate({
    package_id: "construction-pm.language.en",
    language_tag: "en",
    version: "1.0.0",
    app_compatibility: { min_version: "0.1.0", max_version: null },
    artifact: {
      format: "zip",
      compressed_size_bytes: 1,
      download_uri: "https://example.invalid/en.zip",
      delta_from: null,
    },
    resources: {
      translation: "en.json",
      glossary: "en.json",
      help: "en.json",
      reports: "en.json",
      voice_input: null,
      voice_output: null,
      offline_ai_model: null,
    },
    integrity: { checksum: "sha256:x", signature: "sig", signing_key_id: null },
    capabilities: {
      ui: true, help: true, ai_text: true,
      voice_input: false, voice_output: false, offline_ai: false,
    },
    rollback: {
      previous_version: null,
      rollback_supported: true,
    },
  });

  await assert.rejects(
    service.activate({
      package_id: "construction-pm.language.fa",
      language_tag: "fa",
      version: "1.0.0",
      app_compatibility: { min_version: "0.1.0", max_version: null },
      artifact: {
        format: "zip",
        compressed_size_bytes: 1,
        download_uri: "https://example.invalid/fa.zip",
        delta_from: null,
      },
      resources: {
        translation: "fa.json",
        glossary: "fa.json",
        help: "fa.json",
        reports: "fa.json",
        voice_input: null,
        voice_output: null,
        offline_ai_model: null,
      },
      integrity: { checksum: "sha256:x", signature: "sig", signing_key_id: null },
      capabilities: {
        ui: true, help: true, ai_text: true,
        voice_input: false, voice_output: false, offline_ai: false,
      },
      rollback: {
        previous_version: null,
        rollback_supported: true,
      },
    }),
    /BROKEN_FA_RESOURCE/,
  );

  assert.equal(service.current()?.languageTag, "en");
  failFa = false;
  const activated = await service.activate({
    package_id: "construction-pm.language.fa",
    language_tag: "fa",
    version: "1.0.0",
    app_compatibility: { min_version: "0.1.0", max_version: null },
    artifact: {
      format: "zip",
      compressed_size_bytes: 1,
      download_uri: "https://example.invalid/fa.zip",
      delta_from: null,
    },
    resources: {
      translation: "fa.json",
      glossary: "fa.json",
      help: "fa.json",
      reports: "fa.json",
      voice_input: null,
      voice_output: null,
      offline_ai_model: null,
    },
    integrity: { checksum: "sha256:x", signature: "sig", signing_key_id: null },
    capabilities: {
      ui: true, help: true, ai_text: true,
      voice_input: false, voice_output: false, offline_ai: false,
    },
    rollback: {
      previous_version: "1.0.0",
      rollback_supported: true,
    },
  });
  assert.equal(activated.languageTag, "fa");
  assert.equal(service.current()?.languageTag, "fa");
  assert.equal(resources.getBundle("en", "1.0.0"), null);
});
