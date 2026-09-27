import assert from "node:assert/strict";
import test from "node:test";
import {WebSyncRuntime} from "./sync-runtime.js";
import type {LanguagePackManifest} from "../../client-sync/src/language-pack-manifest.js";

const artifact=new TextEncoder().encode("stage-87-client");
const manifest=(version:string):LanguagePackManifest=>({
 package_id:"construction-pm.language.en",language_tag:"en",version,
 app_compatibility:{min_version:"0.1.0",max_version:null},
 artifact:{format:"zip",compressed_size_bytes:artifact.byteLength,download_uri:"https://example.invalid/en.zip",delta_from:null},
 resources:{translation:"translation.json",glossary:"glossary.json",help:"help.json",reports:"reports.json",voice_input:null,voice_output:null,offline_ai_model:null},
 integrity:{checksum:"sha256:b3d6e2fb28a20a84ea9af9a20f78fef721b2e5eac7c2f4c6eb6f02cce107537e",signature:"sig",signing_key_id:"key-1"},
 capabilities:{ui:true,help:true,ai_text:false,voice_input:false,voice_output:false,offline_ai:false},
});
const resources=()=>[
 {path:"translation.json",bytes:new Uint8Array([1])},
 {path:"glossary.json",bytes:new Uint8Array([2])},
 {path:"help.json",bytes:new Uint8Array([3])},
 {path:"reports.json",bytes:new Uint8Array([4])},
];

test("WebSyncRuntime uses the shared validated update, rollback, and offline lifecycle",()=>{
 const runtime=new WebSyncRuntime();
 const first=runtime.languagePacks().activateInitial(artifact,manifest("1.0.0"),resources(),()=>true);
 const updated=runtime.languagePacks().update(artifact,manifest("2.0.0"),resources(),()=>true);
 assert.equal(updated.updated,true);
 assert.equal(runtime.languagePacks().getActive()?.manifest.version,"2.0.0");
 assert.equal(runtime.languagePacks().activateOffline().manifest.version,"2.0.0");
 const restored=runtime.languagePacks().rollback();
 assert.equal(restored.manifest.version,"1.0.0");
 assert.equal(runtime.languagePacks().getActive(),restored);
 assert.equal(runtime.languagePacks().activateOffline(),restored);
 assert.equal(first.manifest.version,"1.0.0");
});

test("WebSyncRuntime preserves active and offline snapshots when an update fails",()=>{
 const runtime=new WebSyncRuntime();
 const first=runtime.languagePacks().activateInitial(artifact,manifest("1.0.0"),resources(),()=>true);
 assert.throws(()=>runtime.languagePacks().update(artifact,manifest("2.0.0"),resources().slice(0,3),()=>true),/LANGUAGE_PACK_RESOURCE_MISSING/);
 assert.equal(runtime.languagePacks().getActive(),first);
 assert.equal(runtime.languagePacks().activateOffline(),first);
});
