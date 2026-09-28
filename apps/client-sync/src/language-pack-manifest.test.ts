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
  typography:{
    font_family:"Vazirmatn",
    fallback_families:["Noto Sans Arabic","Tahoma","Arial","sans-serif"],
    font_style:"normal",
    font_weight:400,
    line_height:"1.7",
    letter_spacing:"normal",
    font_feature_settings:"normal",
    font_variant_ligatures:"common-ligatures",
    font_kerning:"auto",
    font_resources:[]
  },
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

test("accepts Persian typography metadata and arbitrary font resources",()=>{
  const value=structuredClone(base());
  value.typography.font_resources=[{
    family:"Vazirmatn",
    uri:"https://example.invalid/fonts/vazirmatn.woff2",
    format:"woff2",
    weight:400,
    style:"normal",
    unicode_range:"U+0600-06FF,U+200C"
  }];
  assert.deepEqual(validateLanguagePackManifest(value).typography.font_family,"Vazirmatn");
});
test("rejects invalid font resource format",()=>{
  const value=structuredClone(base());
  value.typography.font_resources=[{family:"Bad",uri:"https://example.invalid/bad.bin",format:"bin" as never,weight:400,style:"normal"}];
  assert.throws(()=>validateLanguagePackManifest(value),/INVALID_LANGUAGE_PACK_TYPOGRAPHY/);
});
