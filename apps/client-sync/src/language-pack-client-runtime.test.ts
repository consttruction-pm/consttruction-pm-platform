import assert from "node:assert/strict";
import test from "node:test";
import {LanguagePackClientRuntime} from "./language-pack-client-runtime.ts";
import type {LanguagePackManifest} from "./language-pack-manifest.ts";

const artifact=new TextEncoder().encode("client-language-pack");
const manifest=(version:string):LanguagePackManifest=>({
 package_id:"construction-pm.language.en",language_tag:"en",version,
 app_compatibility:{min_version:"0.1.0",max_version:null},
 artifact:{format:"zip",compressed_size_bytes:artifact.byteLength,download_uri:"https://example.invalid/en.zip",delta_from:null},
 resources:{translation:"translation.json",glossary:"glossary.json",help:"help.json",reports:"reports.json",voice_input:null,voice_output:null,offline_ai_model:null},
 integrity:{checksum:"sha256:c9e4f26d30ca0c895d6a6c85f89af8b310feb4de5a1fda8eed58c75e0135111e",signature:"sig",signing_key_id:"key-1"},
 capabilities:{ui:true,help:true,ai_text:false,voice_input:false,voice_output:false,offline_ai:false},
});
const resources=()=>[
 {path:"translation.json",bytes:new Uint8Array([1])},
 {path:"glossary.json",bytes:new Uint8Array([2])},
 {path:"help.json",bytes:new Uint8Array([3])},
 {path:"reports.json",bytes:new Uint8Array([4])},
];

test("client runtime exposes the shared validated update/rollback/offline lifecycle",()=>{
 const runtime=new LanguagePackClientRuntime();
 const first=runtime.activateInitial(artifact,manifest("1.0.0"),resources(),()=>true);
 const updated=runtime.update(artifact,manifest("2.0.0"),resources(),()=>true);
 assert.equal(updated.updated,true);
 assert.equal(runtime.getActive()?.manifest.version,"2.0.0");
 assert.equal(runtime.activateOffline().manifest.version,"2.0.0");
 const restored=runtime.rollback();
 assert.equal(restored.manifest.version,"1.0.0");
 assert.equal(runtime.getActive(),restored);
 assert.equal(runtime.activateOffline(),restored);
 assert.equal(first.manifest.version,"1.0.0");
});

test("client runtime failed update preserves active and offline snapshots",()=>{
 const runtime=new LanguagePackClientRuntime();
 const first=runtime.activateInitial(artifact,manifest("1.0.0"),resources(),()=>true);
 assert.throws(()=>runtime.update(artifact,manifest("2.0.0"),resources().slice(0,3),()=>true),/LANGUAGE_PACK_RESOURCE_MISSING/);
 assert.equal(runtime.getActive(),first);
 assert.equal(runtime.activateOffline(),first);
});
