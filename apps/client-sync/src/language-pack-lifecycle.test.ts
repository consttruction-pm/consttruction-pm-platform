import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import test from "node:test";
import {LanguagePackLifecycle} from "./language-pack-lifecycle.ts";
import type {LanguagePackManifest} from "./language-pack-manifest.ts";

const artifact=new TextEncoder().encode("stage-87-lifecycle");
const checksum="sha256:"+createHash("sha256").update(artifact).digest("hex");
const manifest=(version:string):LanguagePackManifest=>({
 package_id:"construction-pm.language.fa",language_tag:"fa",version,
 app_compatibility:{min_version:"0.1.0",max_version:null},
 artifact:{format:"zip",compressed_size_bytes:artifact.byteLength,download_uri:"https://example.invalid/fa.zip",delta_from:null},
 resources:{translation:"translation.json",glossary:"glossary.json",help:"help.json",reports:"reports.json",voice_input:null,voice_output:null,offline_ai_model:null},
 integrity:{checksum,signature:"sig",signing_key_id:"key-1"},
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
const resources=()=>[
 {path:"translation.json",bytes:new Uint8Array([1])},{path:"glossary.json",bytes:new Uint8Array([2])},
 {path:"help.json",bytes:new Uint8Array([3])},{path:"reports.json",bytes:new Uint8Array([4])},
];

test("keeps online, rollback, and offline activation on the same validated snapshot",()=>{
 const lifecycle=new LanguagePackLifecycle();
 lifecycle.activateInitial(artifact,manifest("1.0.0"),resources(),()=>true);
 lifecycle.update(artifact,manifest("2.0.0"),resources(),()=>true);
 assert.equal(lifecycle.getActive()?.manifest.version,"2.0.0");
 assert.equal(lifecycle.activateOffline().manifest.version,"2.0.0");
 lifecycle.rollback();
 assert.equal(lifecycle.getActive()?.manifest.version,"1.0.0");
 assert.equal(lifecycle.activateOffline().manifest.version,"1.0.0");
});

test("failed update leaves both active and offline snapshots unchanged",()=>{
 const lifecycle=new LanguagePackLifecycle();
 lifecycle.activateInitial(artifact,manifest("1.0.0"),resources(),()=>true);
 const bad={...manifest("2.0.0"),integrity:{...manifest("2.0.0").integrity,checksum:"sha256:"+"0".repeat(64)}};
 assert.throws(()=>lifecycle.update(artifact,bad,resources(),()=>true),/LANGUAGE_PACK_CHECKSUM_MISMATCH/);
 assert.equal(lifecycle.getActive()?.manifest.version,"1.0.0");
 assert.equal(lifecycle.activateOffline().manifest.version,"1.0.0");
});
