import assert from "node:assert/strict"; import test from "node:test"; import {InMemoryLanguagePreferenceStore} from "./language-preference-store.ts";
test("persists preferred language",async()=>{const s=new InMemoryLanguagePreferenceStore();assert.equal(await s.load(),null);await s.save("fa");assert.equal(await s.load(),"fa");});
test("rejects empty preference",async()=>{const s=new InMemoryLanguagePreferenceStore();await assert.rejects(s.save("   "),/INVALID_LANGUAGE_PREFERENCE/);});
