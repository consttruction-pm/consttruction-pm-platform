import assert from "node:assert/strict";
import test from "node:test";
import {sha256Hex} from "./sha256.ts";

test("sha256Hex matches the standard empty-input vector",()=>{
 assert.equal(sha256Hex(new Uint8Array()),"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
});

test("sha256Hex matches the standard abc vector",()=>{
 assert.equal(sha256Hex(new TextEncoder().encode("abc")),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
});

test("sha256Hex matches a language-pack artifact vector",()=>{
 assert.equal(sha256Hex(new TextEncoder().encode("stage-87-client")),"b3d6e2fb28a20a84ea9af9a20f78fef721b2e5eac7c2f4c6eb6f02cce107537e");
});
