import assert from "node:assert/strict";
import test from "node:test";
import {selectCompatiblePack,isNewerPackAvailable} from "./language-pack-catalog.ts";
const catalog={schemaVersion:"1.0",generatedAt:"2026-09-27T00:00:00Z",defaultLanguage:"en",items:[
 {packageId:"construction-pm.language.fa",languageTag:"fa",version:"1.0.0",minAppVersion:"0.1.0",maxAppVersion:null,compressedSizeBytes:1,downloadUri:"https://example.invalid/fa.zip",checksum:"sha256:"+"a".repeat(64),signature:"s",capabilities:{ui:true,help:true,aiText:true,voiceInput:true,voiceOutput:true,offlineAi:false}}
]};
test("selects compatible pack",()=>assert.equal(selectCompatiblePack(catalog,"fa","0.1.0")?.version,"1.0.0"));
test("rejects incompatible language",()=>assert.equal(selectCompatiblePack(catalog,"de","0.1.0"),null));
test("detects newer pack",()=>assert.equal(isNewerPackAvailable("1.0.0","1.1.0"),true));
test("does not treat downgrade as update",()=>assert.equal(isNewerPackAvailable("1.1.0","1.0.0"),false));