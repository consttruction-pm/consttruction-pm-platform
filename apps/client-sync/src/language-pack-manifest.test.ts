import assert from "node:assert/strict";
import test from "node:test";
import { validateLanguagePackManifest, type LanguagePackManifest } from "./language-pack-manifest.ts";

const base = (): LanguagePackManifest => ({
  package_id:"construction-pm.language.fa", language_tag:"fa", version:"1.0.0",
  app_compatibility:{min_version:"0.1.0",max_version:null},
  artifact:{format:"zip",compressed_size_bytes:1,download_uri:"https://example.invalid/fa.zip",delta_from:null},
  resources:{translation:"translation.json",glossary:"glossary.json",help:"help.json",reports:"reports.json",voice_input:null,voice_output:null,offline_ai_model:null},
  integrity:{checksum:"sha256:"+"a".repeat(64),signature:"sig",signing_key_id:"key-1"},
  capabilities:{ui:true,help:true,ai_text:true,voice_input:false,voice_output:false,offline_ai:false},
});

test("accepts a schema-conformant manifest",()=>assert.deepEqual(validateLanguagePackManifest(base()),base()));
test("rejects truthy non-boolean capabilities",()=>{
  const value=structuredClone(base()) as unknown as Record<string,unknown>;
  (value.capabilities as Record<string,unknown>).offline_ai="false";
  assert.throws(()=>validateLanguagePackManifest(value),/INVALID_LANGUAGE_PACK_CAPABILITIES/);
});
test("rejects unknown manifest fields instead of silently widening the signed surface",()=>{
  const value=structuredClone(base()) as Record<string,unknown>;
  value.untrusted_extra="tampered";
  assert.throws(()=>validateLanguagePackManifest(value),/INVALID_LANGUAGE_PACK_MANIFEST/);
});
test("rejects malformed nested fields",()=>{
  const value=structuredClone(base()) as unknown as Record<string,unknown>;
  (value.artifact as Record<string,unknown>).compressed_size_bytes=true;
  assert.throws(()=>validateLanguagePackManifest(value),/INVALID_LANGUAGE_PACK_ARTIFACT/);
});
test("rejects invalid version and URI",()=>{
  const value=structuredClone(base()) as unknown as Record<string,unknown>;
  value.version="1";
  assert.throws(()=>validateLanguagePackManifest(value),/INVALID_LANGUAGE_PACK_VERSION/);
  value.version="1.0.0";
  (value.artifact as Record<string,unknown>).download_uri="not-a-uri";
  assert.throws(()=>validateLanguagePackManifest(value),/INVALID_LANGUAGE_PACK_ARTIFACT/);
});
