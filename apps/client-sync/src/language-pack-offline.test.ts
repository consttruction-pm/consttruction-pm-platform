import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import test from "node:test";
import {OfflineLanguagePackStore} from "./language-pack-offline.ts";
import type {LanguagePackManifest} from "./language-pack-manifest.ts";

const artifact=new TextEncoder().encode("offline-stage-87");
const checksum="sha256:"+createHash("sha256").update(artifact).digest("hex");
const manifest:LanguagePackManifest={
 package_id:"construction-pm.language.fa",language_tag:"fa",version:"2.0.0",
 app_compatibility:{min_version:"0.1.0",max_version:null},
 artifact:{format:"zip",compressed_size_bytes:artifact.byteLength,download_uri:"https://example.invalid/fa.zip",delta_from:null},
 resources:{translation:"translation.json",glossary:"glossary.json",help:"help.json",reports:"reports.json",voice_input:null,voice_output:null,offline_ai_model:null},
 integrity:{checksum,signature:"sig",signing_key_id:"key-1"},
 capabilities:{ui:true,help:true,ai_text:true,voice_input:false,voice_output:false,offline_ai:false},
};
const resources=()=>[
 {path:"translation.json",bytes:new Uint8Array([1])},{path:"glossary.json",bytes:new Uint8Array([2])},
 {path:"help.json",bytes:new Uint8Array([3])},{path:"reports.json",bytes:new Uint8Array([4])},
];

test("offline activation requires a verified cached pack",()=>{
 const store=new OfflineLanguagePackStore();
 assert.throws(()=>store.activateOffline(),/LANGUAGE_PACK_OFFLINE_CACHE_UNAVAILABLE/);
 const active=store.cacheVerifiedPack({artifact,manifest,resources:resources()},()=>true);
 assert.equal(active.manifest.version,"2.0.0");
 assert.equal(store.hasVerifiedCache(manifest.package_id,manifest.version),true);
 assert.equal(store.activateOffline().manifest.version,"2.0.0");
});
test("invalid cached pack is not made available offline",()=>{
 const store=new OfflineLanguagePackStore();
 const invalid={...manifest,integrity:{...manifest.integrity,checksum:"sha256:"+"0".repeat(64)}};
 assert.throws(()=>store.cacheVerifiedPack({artifact,manifest:invalid,resources:resources()},()=>true),/LANGUAGE_PACK_CHECKSUM_MISMATCH/);
 assert.throws(()=>store.activateOffline(),/LANGUAGE_PACK_OFFLINE_CACHE_UNAVAILABLE/);
});
