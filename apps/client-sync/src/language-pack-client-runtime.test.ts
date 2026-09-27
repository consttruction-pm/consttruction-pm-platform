import assert from "node:assert/strict";
import test from "node:test";
import {LanguagePackClientRuntime} from "./language-pack-client-runtime.ts";
import type {LanguagePackManifest} from "./language-pack-manifest.ts";

const manifest=(version:string):LanguagePackManifest=>({
 package_id:"en-US",
 language_tag:"en-US",
 version,
 app_compatibility:{min_version:"1.0.0",max_version:null},
 artifact:{format:"zip",compressed_size_bytes:3,download_uri:"https://example.test/en.zip",delta_from:null},
 resources:{translation:"translation.json",glossary:"glossary.json",help:"help.json",reports:"reports.json",voice_input:null,voice_output:null,offline_ai_model:null},
 integrity:{checksum:version==="1.0.0"?"sha256:039058c6f2c0cb492c533b0a4d14ef77cc0f78abccced5287d84a1a2011cfb81":"sha256:787c798e39a5bc1910355bae6d0cd87a36b2e10fd0202a83e3bb6b005da83472",signature:"sig",signing_key_id:"key-1"},
 capabilities:{ui:true,help:true,ai_text:false,voice_input:false,voice_output:false,offline_ai:false},
});

const resources=(value:number)=>[
 {path:"translation.json",bytes:new Uint8Array([value])},
 {path:"glossary.json",bytes:new Uint8Array([value+1])},
 {path:"help.json",bytes:new Uint8Array([value+2])},
 {path:"reports.json",bytes:new Uint8Array([value+3])},
];

const verify=()=>true;

test("client runtime exposes the shared language-pack lifecycle",()=>{
 const runtime=new LanguagePackClientRuntime();
 const first=runtime.activateInitial(new Uint8Array([1,2,3]),manifest("1.0.0"),resources(1),verify);
 assert.equal(first.manifest.version,"1.0.0");
 assert.equal(runtime.getActive()?.manifest.version,"1.0.0");
 const updated=runtime.update(new Uint8Array([4,5,6]),manifest("2.0.0"),resources(5),verify);
 assert.equal(updated.updated,true);
 assert.equal(runtime.getActive()?.manifest.version,"2.0.0");
 assert.equal(runtime.rollback().manifest.version,"1.0.0");
 assert.equal(runtime.activateOffline().manifest.version,"1.0.0");
});

test("failed client runtime update preserves the validated active snapshot",()=>{
 const runtime=new LanguagePackClientRuntime();
 const first=runtime.activateInitial(new Uint8Array([1,2,3]),manifest("1.0.0"),resources(1),verify);
 assert.throws(()=>runtime.update(new Uint8Array([4,5,6]),manifest("2.0.0"),resources(5).slice(0,3),verify),/LANGUAGE_PACK_RESOURCE_MISSING/);
 assert.equal(runtime.getActive(),first);
 assert.equal(runtime.activateOffline(),first);
});
