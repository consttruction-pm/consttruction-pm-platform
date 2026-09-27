import { strict as assert } from "node:assert";
import { test } from "node:test";
import { createWebVoiceAdapters, normalizeWebVoiceCapture, requireWebVoiceOutput } from "./voice-adapters.ts";

const scope={tenant_id:"tenant-1",project_id:"project-1",project_revision:7} as const;
const aiLanguage={language_tag:"fa-IR",capabilities:{voice_input:true,voice_output:true,offline_ai:true}} as any;

test("web voice adapter uses shared normalization boundary",async()=>{
 const adapters=createWebVoiceAdapters({input:{capabilities:{input:true,output:false},async capture(){return {snapshot:{contract_version:"voice-command.v1",voice_command_id:"web-1",scope,requested_by:"u1",input_language:"fa-IR",transcript:"برنامه را بررسی کن",query_kind:"fact",captured_at:"2026-09-27T18:00:00Z",source:"microphone",confidence:1}};}},output:{capabilities:{input:false,output:true},async speak(){}}});
 const command=normalizeWebVoiceCapture(adapters,await adapters.input.capture({aiLanguage,expectedScope:scope}),aiLanguage,scope);
 assert.equal(command.voice_command_id,"web-1"); assert.doesNotThrow(()=>requireWebVoiceOutput(adapters,"fa-IR",scope));
});
