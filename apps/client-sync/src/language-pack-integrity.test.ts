import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import test from "node:test";
import type {LanguagePackManifest} from "./language-pack-manifest.ts";
import {canonicalizeLanguagePackSigningPayload,verifyLanguagePackChecksum,verifyLanguagePackIntegrity} from "./language-pack-integrity.ts";

const artifact=new TextEncoder().encode("language-pack-v1");
const digest=()=> "sha256:"+createHash("sha256").update(artifact).digest("hex");
const manifest=(checksum=digest(),signature="sig"):LanguagePackManifest=>({package_id:"construction-pm.language.fa",language_tag:"fa",version:"1.0.0",app_compatibility:{min_version:"0.1.0",max_version:null},artifact:{format:"zip" as const,compressed_size_bytes:artifact.byteLength,download_uri:"https://example.invalid/fa.zip",delta_from:null},resources:{translation:"translation.json",glossary:"glossary.json",help:"help.json",reports:"reports.json",voice_input:null,voice_output:null,offline_ai_model:null},integrity:{checksum,signature,signing_key_id:"key-1"},capabilities:{ui:true,help:true,ai_text:true,voice_input:false,voice_output:false,offline_ai:false}});

test("rejects a checksum mismatch",()=>assert.equal(verifyLanguagePackChecksum(artifact,manifest("sha256:"+"0".repeat(64))),false));
test("accepts the exact SHA-256 digest",()=>assert.equal(verifyLanguagePackChecksum(artifact,manifest()),true));
test("requires checksum before signature",()=>assert.throws(()=>verifyLanguagePackIntegrity(artifact,manifest("sha256:"+"0".repeat(64)),()=>true),/LANGUAGE_PACK_CHECKSUM_MISMATCH/));
test("rejects invalid signature result",()=>assert.throws(()=>verifyLanguagePackIntegrity(artifact,manifest(),()=>false),/LANGUAGE_PACK_SIGNATURE_INVALID/));
test("passes when checksum and signature verify",()=>assert.doesNotThrow(()=>verifyLanguagePackIntegrity(artifact,manifest(),()=>true)));

test("canonical signing payload is deterministic and excludes only the signature field",()=>{
 const first=canonicalizeLanguagePackSigningPayload(manifest());
 const second=canonicalizeLanguagePackSigningPayload({...manifest(),integrity:{...manifest().integrity,signature:"different"}});
 assert.deepEqual([...first],[...second]);
 assert.equal(new TextDecoder().decode(first).includes('"schema_version":"language-pack-signing-payload.v1"'),true);
});

test("signature verification receives the canonical manifest payload",()=>{
 let received:Uint8Array|undefined;
 verifyLanguagePackIntegrity(artifact,manifest(),(payload)=>{received=payload;return true;});
 assert.deepEqual([...received!],[...canonicalizeLanguagePackSigningPayload(manifest())]);
});

test("manifest capability changes invalidate the signed payload",()=>{
 const baseManifest=manifest();
 let signedPayload="";
 verifyLanguagePackIntegrity(artifact,baseManifest,(payload)=>{signedPayload=new TextDecoder().decode(payload);return true;});
 const changed={...baseManifest,capabilities:{...baseManifest.capabilities,offline_ai:true}};
 let changedPayload="";
 verifyLanguagePackIntegrity(artifact,changed,(payload)=>{changedPayload=new TextDecoder().decode(payload);return true;});
 assert.notEqual(changedPayload,signedPayload);
});

test("manifest resource changes invalidate the signed payload",()=>{
 const baseManifest=manifest();
 const changed={...baseManifest,resources:{...baseManifest.resources,translation:"tampered.json"}};
 assert.notDeepEqual(
  [...canonicalizeLanguagePackSigningPayload(baseManifest)],
  [...canonicalizeLanguagePackSigningPayload(changed)],
 );
});

test("package, version, checksum, and signing key changes invalidate the signed payload",()=>{
 const baseManifest=manifest();
 const variants=[
  {...baseManifest,package_id:"construction-pm.language.en"},
  {...baseManifest,version:"2.0.0"},
  {...baseManifest,integrity:{...baseManifest.integrity,checksum:"sha256:"+"b".repeat(64)}},
  {...baseManifest,integrity:{...baseManifest.integrity,signing_key_id:"key-2"}},
 ];
 for(const variant of variants){
  assert.notDeepEqual(
   [...canonicalizeLanguagePackSigningPayload(baseManifest)],
   [...canonicalizeLanguagePackSigningPayload(variant)],
  );
 }
});
