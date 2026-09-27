import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import test from "node:test";
import {verifyLanguagePackChecksum,verifyLanguagePackIntegrity} from "./language-pack-integrity.ts";

const artifact=new TextEncoder().encode("language-pack-v1");
const digest=()=> "sha256:"+createHash("sha256").update(artifact).digest("hex");
const manifest=(checksum=digest(),signature="sig")=>({package_id:"construction-pm.language.fa",language_tag:"fa",version:"1.0.0",app_compatibility:{min_version:"0.1.0",max_version:null},artifact:{format:"zip",compressed_size_bytes:artifact.byteLength,download_uri:"https://example.invalid/fa.zip",delta_from:null},resources:{translation:"translation.json",glossary:"glossary.json",help:"help.json",reports:"reports.json",voice_input:null,voice_output:null,offline_ai_model:null},integrity:{checksum,signature,signing_key_id:"key-1"},capabilities:{ui:true,help:true,ai_text:true,voice_input:false,voice_output:false,offline_ai:false}});

test("rejects a checksum mismatch",()=>assert.equal(verifyLanguagePackChecksum(artifact,manifest("sha256:"+"0".repeat(64))),false));
test("accepts the exact SHA-256 digest",()=>assert.equal(verifyLanguagePackChecksum(artifact,manifest()),true));
test("requires checksum before signature",()=>assert.throws(()=>verifyLanguagePackIntegrity(artifact,manifest("sha256:"+"0".repeat(64)),()=>true),/LANGUAGE_PACK_CHECKSUM_MISMATCH/));
test("rejects invalid signature result",()=>assert.throws(()=>verifyLanguagePackIntegrity(artifact,manifest(),()=>false),/LANGUAGE_PACK_SIGNATURE_INVALID/));
test("passes when checksum and signature verify",()=>assert.doesNotThrow(()=>verifyLanguagePackIntegrity(artifact,manifest(),()=>true)));