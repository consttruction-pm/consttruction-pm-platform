import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import test from "node:test";
import {UpdateableLanguagePackStore} from "./language-pack-update.ts";
import type {LanguagePackManifest} from "./language-pack-manifest.ts";

const artifact=new TextEncoder().encode("stage-87-update");
const checksum="sha256:"+createHash("sha256").update(artifact).digest("hex");
const manifest=(version:string):LanguagePackManifest=>({
 package_id:"construction-pm.language.fa",language_tag:"fa",version,
 app_compatibility:{min_version:"0.1.0",max_version:null},
 artifact:{format:"zip",compressed_size_bytes:artifact.byteLength,download_uri:"https://example.invalid/fa.zip",delta_from:null},
 resources:{translation:"translation.json",glossary:"glossary.json",help:"help.json",reports:"reports.json",voice_input:null,voice_output:null,offline_ai_model:null},
 integrity:{checksum,signature:"sig",signing_key_id:"key-1"},
 capabilities:{ui:true,help:true,ai_text:true,voice_input:false,voice_output:false,offline_ai:false},
});
const resources=()=>[
 {path:"translation.json",bytes:new Uint8Array([1])},{path:"glossary.json",bytes:new Uint8Array([2])},
 {path:"help.json",bytes:new Uint8Array([3])},{path:"reports.json",bytes:new Uint8Array([4])},
];

test("updates and rolls back through validated previous packs",()=>{
 const store=new UpdateableLanguagePackStore();
 store.activate(artifact,manifest("1.0.0"),resources(),()=>true);
 store.update(artifact,manifest("2.0.0"),resources(),()=>true);
 store.update(artifact,manifest("3.0.0"),resources(),()=>true);
 assert.equal(store.getActive()?.manifest.version,"3.0.0");
 assert.equal(store.rollback().manifest.version,"2.0.0");
 assert.equal(store.rollback().manifest.version,"1.0.0");
});

test("rollback history is bounded",()=>{
 const store=new UpdateableLanguagePackStore();
 for(let version=1;version<=7;version++){
  store.activate(artifact,manifest(version.toFixed(1)+".0"),resources(),()=>true);
 }
 assert.equal(store.rollback().manifest.version,"6.0.0");
 assert.equal(store.rollback().manifest.version,"5.0.0");
 assert.equal(store.rollback().manifest.version,"4.0.0");
 assert.equal(store.rollback().manifest.version,"3.0.0");
 assert.equal(store.rollback().manifest.version,"2.0.0");
 assert.throws(()=>store.rollback(),/LANGUAGE_PACK_ROLLBACK_UNAVAILABLE/);
});

test("failed activation does not add a rollback entry",()=>{
 const store=new UpdateableLanguagePackStore();
 store.activate(artifact,manifest("1.0.0"),resources(),()=>true);
 assert.throws(()=>store.update(artifact,manifest("2.0.0"),resources(),()=>false));
 assert.equal(store.getActive()?.manifest.version,"1.0.0");
 assert.throws(()=>store.rollback(),/LANGUAGE_PACK_ROLLBACK_UNAVAILABLE/);
});

test("rollback is unavailable before a second validated activation",()=>{
 const store=new UpdateableLanguagePackStore();
 assert.throws(()=>store.rollback(),/LANGUAGE_PACK_ROLLBACK_UNAVAILABLE/);
});
