import assert from "node:assert/strict";
import test from "node:test";
import { MobileRuntime } from "./runtime.js";
import type { SyncOutcome } from "../../client-sync/src/mutation-queue.js";
import type { SyncProjectContext } from "../../client-sync/src/api-sync-transport.js";

test("mobile syncOnce uses shared transport and preserves retry", async () => {
  const runtime = new MobileRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation({ contract_version: "sync-mutation.v1", mutation_id: "m1", tenant_id: "t1", project_id: "p1", expected_revision: 7, operation: "update_activity", payload: { activity_id: "A1" }, idempotency_key: "idem-1" });
  const outcomes = await runtime.syncOnce({ async post() { return { ok: false as const, error: { code: "TEMPORARY_UNAVAILABLE", retryable: true } }; } });
  assert.equal(outcomes[0]?.disposition, "retry");
  assert.equal(runtime.pendingMutationCount(), 1);
});

test("mobile stale revision retry requires authoritative refresh", async () => {
  const runtime = new MobileRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation({ contract_version: "sync-mutation.v1", mutation_id: "m1", tenant_id: "t1", project_id: "p1", expected_revision: 7, operation: "update_activity", payload: {}, idempotency_key: "idem-1" });
  const outcome: SyncOutcome = { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "conflict", error_code: "STALE_REVISION" };

  const retried = await runtime.retryStaleRevision("m1", outcome, {
    async get<TResponse>(path: string, context: SyncProjectContext) {
      assert.equal(path, "/api/v1/sync/revision");
      assert.deepEqual(context, { tenant_id: "t1", project_id: "p1", revision: 7 });
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 42 } as TResponse };
    },
  });

  assert.equal(retried.expected_revision, 42);
  assert.equal(retried.idempotency_key, "idem-1:r42");
  assert.equal(runtime.current().revision, 42);
});


test("mobile runtime refreshes the project revision", async () => {
  const runtime = new MobileRuntime();
  runtime.openProject("t1", "p1", 7);
  const state = await runtime.refreshRevision({
    async get<TResponse>(path: string, context: SyncProjectContext) {
      assert.equal(path, "/api/v1/sync/revision");
      assert.deepEqual(context, { tenant_id: "t1", project_id: "p1", revision: 7 });
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 8 } as TResponse };
    },
  });
  assert.equal(state.revision, 8);
});

test("mobile runtime rejects an invalid authoritative revision response", async () => {
  const runtime = new MobileRuntime();
  runtime.openProject("t1", "p1", 7);
  await assert.rejects(
    runtime.refreshRevision({
      async get<TResponse>() {
        return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 8.5 } as TResponse };
      },
    }),
    /INVALID_PROJECT_REVISION_RESPONSE/,
  );
});

test("mobile stale retry can be acknowledged after authoritative refresh", async () => {
  const runtime = new MobileRuntime();
  runtime.openProject("t1", "p1", 7);
  runtime.queueMutation({ contract_version: "sync-mutation.v1", mutation_id: "m1", tenant_id: "t1", project_id: "p1", expected_revision: 7, operation: "update_activity", payload: {}, idempotency_key: "idem-1" });
  const conflict: SyncOutcome = { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "conflict", error_code: "STALE_REVISION" };
  const retried = await runtime.retryStaleRevision("m1", conflict, {
    async get<TResponse>() {
      return { ok: true as const, data: { contract_version: "sync-project-revision.v1", tenant_id: "t1", project_id: "p1", revision: 42 } as TResponse };
    },
  });
  const outcomes = await runtime.syncOnce({
    async post<TRequest, TResponse>(_path: string, request: TRequest, context: { tenant_id: string; project_id: string; revision: number }, idempotencyKey: string) {
      assert.equal((request as any).expected_revision, 42);
      assert.equal(context.revision, 42);
      assert.equal(idempotencyKey, "idem-1:r42");
      return { ok: true as const, data: { contract_version: "sync-outcome.v1", mutation_id: "m1", disposition: "acknowledged" } as TResponse };
    },
  });
  assert.equal(retried.expected_revision, 42);
  assert.equal(outcomes[0]?.disposition, "acknowledged");
  assert.equal(runtime.current().revision, 42);
  assert.equal(runtime.pendingMutationCount(), 0);
});

import type {LanguagePackManifest} from "../../client-sync/src/language-pack-manifest.ts";

const mobileLanguageManifest:LanguagePackManifest={
 package_id:"en-US",language_tag:"en-US",version:"1.0.0",
 app_compatibility:{min_version:"1.0.0",max_version:null},
 artifact:{format:"zip",compressed_size_bytes:3,download_uri:"https://example.test/en.zip",delta_from:null},
 resources:{translation:"translation.json",glossary:"glossary.json",help:"help.json",reports:"reports.json",voice_input:null,voice_output:null,offline_ai_model:null},
 integrity:{checksum:"sha256:039058c6f2c0cb492c533b0a4d14ef77cc0f78abccced5287d84a1a2011cfb81",signature:"sig",signing_key_id:"key-1"},
 capabilities:{ui:true,help:true,ai_text:false,voice_input:false,voice_output:false,offline_ai:false},
};

test("mobile runtime exposes shared language-pack activation lifecycle",()=>{
 const runtime=new MobileRuntime();
 const active=runtime.languagePacks().activateInitial(new Uint8Array([1,2,3]),mobileLanguageManifest,[
  {path:"translation.json",bytes:new Uint8Array([1])},
  {path:"glossary.json",bytes:new Uint8Array([2])},
  {path:"help.json",bytes:new Uint8Array([3])},
  {path:"reports.json",bytes:new Uint8Array([4])},
 ],()=>true);
 assert.equal(active.manifest.package_id,"en-US");
 assert.equal(runtime.languagePacks().getActive(),active);
 assert.equal(runtime.languagePacks().activateOffline(),active);
});
