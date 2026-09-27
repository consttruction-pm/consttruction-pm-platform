import assert from "node:assert/strict";
import test from "node:test";
import {verifyLanguagePackChecksum,verifyLanguagePackIntegrity} from "./language-pack-integrity.ts";

const artifact=new TextEncoder().encode("language-pack-v1");
const checksum="sha256:2c6c8e0a8d11c2fddf0d5d1fef2cf7a2b6f3a8e9d3c2c6c6a9b8f4f3f2c1d0e9";

function manifest(checksumValue:string=checksum,signature="sig"){return {package_id:"construction-pm.language.fa",language_tag:"fa",version:"1.0.0",app_compatibility:{min_version:"0.1.0",max_version:null},artifact:{format:"zip",compressed_size_bytes:artifact.byteLength,download_uri:"https://example.invalid/fa.zip",delta_from:null},resources:{translation:"translation.json",glossary:"glossary.json",help:"help.json",reports:"reports.json",voice_input:null,voice_output:null,offline_ai_model:null},integrity:{checksum:checksumValue,signature,signing_key_id:"key-1"},capabilities:{ui:true,help:true,ai_text:true,voice_input:false,voice_output:false,offline_ai:false}}}

test("rejects a checksum mismatch",()=>assert.equal(verifyLanguagePackChecksum(artifact,manifest()),false));
test("accepts the exact SHA-256 digest",()=>{const crypto=await import("node:crypto"); const digest="sha256:"+crypto.createHash("sha256").update(artifact).digest("hex"); assert.equal(verifyLanguagePackChecksum(artifact,manifest(digest)),true)});
test("requires checksum before signature",()=>assert.throws(()=>verifyLanguagePackIntegrity(artifact,manifest(),"".length?()=>true:()=>true),/LANGUAGE_PACK_CHECKSUM_MISMATCH/));
test("rejects invalid signature result",()=>{const crypto=require("node:crypto"); const digest="sha256:"+crypto.createHash("sha256").update(artifact).digest("hex"); assert.throws(()=>verifyLanguagePackIntegrity(artifact,manifest(digest),"sig"?()=>false:()=>false),/LANGUAGE_PACK_SIGNATURE_INVALID/)});
test("passes when checksum and signature verify",()=>{const crypto=require("node:crypto"); const digest="sha256:"+crypto.createHash("sha256").update(artifact).digest("hex"); assert.doesNotThrow(()=>verifyLanguagePackIntegrity(artifact,manifest(digest),()=>true))});
