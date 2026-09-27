import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import test from "node:test";
import {AtomicLanguagePackStore} from "./language-pack-activation.ts";
import type {LanguagePackManifest} from "./language-pack-manifest.ts";
import {validateLanguagePackResourcePath} from "./language-pack-resource-validation.ts";

const artifact=new TextEncoder().encode("language-pack-stage-87");
const checksum="sha256:"+createHash("sha256").update(artifact).digest("hex");
const manifest=():LanguagePackManifest=>({
 package_id:"construction-pm.language.fa",language_tag:"fa",version:"1.0.0",
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

test("rejects unsafe resource paths",()=>assert.throws(()=>validateLanguagePackResourcePath("../translation.json"),/INVALID_LANGUAGE_PACK_RESOURCE_PATH/));
test("rejects Windows separators",()=>assert.throws(()=>validateLanguagePackResourcePath("nested\\translation.json"),/INVALID_LANGUAGE_PACK_RESOURCE_PATH/));
test("activates only after artifact integrity and resource validation",()=>{
 const store=new AtomicLanguagePackStore();
 const active=store.activate(artifact,manifest(),resources(),()=>true);
 assert.equal(active.manifest.package_id,"construction-pm.language.fa");
 assert.deepEqual([...active.resources.get("translation.json")!],[1]);
});
test("failed activation preserves the previously active pack",()=>{
 const store=new AtomicLanguagePackStore();
 store.activate(artifact,manifest(),resources(),()=>true);
 const next={...manifest(),version:"2.0.0",integrity:{...manifest().integrity,checksum:"sha256:"+"0".repeat(64)}};
 assert.throws(()=>store.activate(artifact,next,resources(),()=>true),/LANGUAGE_PACK_CHECKSUM_MISMATCH/);
 assert.equal(store.getActive()?.manifest.version,"1.0.0");
});
test("resource validation occurs before activation commit",()=>{
 const store=new AtomicLanguagePackStore();
 store.activate(artifact,manifest(),resources(),()=>true);
 assert.throws(()=>store.activate(artifact,manifest(),[{path:"../escape.json",bytes:new Uint8Array([9])}],()=>true),/INVALID_LANGUAGE_PACK_RESOURCE_PATH/);
 assert.equal(store.getActive()?.manifest.version,"1.0.0");
});
test("rejects undeclared resources",()=>{
 const store=new AtomicLanguagePackStore();
 const extra=[...resources(),{path:"extra.json",bytes:new Uint8Array([5])}];
 assert.throws(()=>store.activate(artifact,manifest(),extra,()=>true),/UNDECLARED_LANGUAGE_PACK_RESOURCE/);
 assert.equal(store.getActive(),null);
});
test("activation owns resource byte snapshots",()=>{
 const store=new AtomicLanguagePackStore();
 const mutable=new Uint8Array([1,2,3]);
 const input=[
  {path:"translation.json",bytes:mutable},{path:"glossary.json",bytes:new Uint8Array([2])},
  {path:"help.json",bytes:new Uint8Array([3])},{path:"reports.json",bytes:new Uint8Array([4])},
 ];
 const active=store.activate(artifact,manifest(),input,()=>true);
 mutable[0]=9;
 assert.deepEqual([...active.resources.get("translation.json")!],[1,2,3]);
 assert.notEqual(active.resources.get("translation.json"),mutable);
});
