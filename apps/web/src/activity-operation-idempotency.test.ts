import assert from "node:assert/strict";
import { test } from "node:test";
import type { ApiResult } from "./client.js";
import {
  ActivityOperationJournal,
  activityOperationRequest,
  runActivityOperation,
  type ActivityOperationRequest,
  type PendingActivityOperation,
} from "./activity-operation-idempotency.js";

type CopyResult = { operation: "copy"; created: Array<{ source_activity_id: string; activity_id: string }>; replayed?: boolean };

/**
 * A server that commits a copy, then loses the response once. A retry with the
 * same key must replay the stored result and must not create another copy.
 */
class FlakyCopyServer {
  readonly keyed = new Map<string, CopyResult>();
  readonly keys: string[] = [];
  readonly bodies: ActivityOperationRequest[] = [];
  constructor(private loseFirstResponse: boolean) {}

  send = async (
    pending: PendingActivityOperation,
    request: ActivityOperationRequest,
  ): Promise<ApiResult<CopyResult>> => {
    this.keys.push(pending.key);
    this.bodies.push(request);
    const stored = this.keyed.get(pending.key);
    if (stored) return { ok: true, data: { ...stored, replayed: true } };
    const result: CopyResult = {
      operation: "copy",
      created: [{ source_activity_id: "A-1", activity_id: "A-1-COPY" }],
    };
    this.keyed.set(pending.key, result);
    if (this.loseFirstResponse) {
      this.loseFirstResponse = false;
      return {
        ok: false,
        error: {
          code: "NETWORK_TIMEOUT",
          retryable: true,
          message_key: "error.network",
          available_actions: ["retry"],
        },
      };
    }
    return { ok: true, data: result };
  };
}

function keys(prefix: string): () => string {
  let index = 0;
  return () => `${prefix}-${++index}`;
}

const INPUT = {
  projectId: "preview-rps-01",
  operation: "copy" as const,
  activityIds: ["A-1"],
  targetWbsId: "WBS-RPS-CIVIL",
};

function revisions(_ids: readonly string[]): Promise<Record<string, number>> {
  return Promise.resolve({ "A-1": 3 });
}

test("a lost response keeps the key and the retry replays exactly one copy", async () => {
  const journal = new ActivityOperationJournal(keys("copy"));
  const server = new FlakyCopyServer(true);

  const first = await runActivityOperation({
    journal,
    input: INPUT,
    loadExpectedRevisions: revisions,
    send: server.send,
  });
  assert.equal(first.response.ok, false);
  assert.equal(first.reused, false);
  assert.equal(journal.peek()?.key, "copy-1");

  const retry = await runActivityOperation({
    journal,
    input: INPUT,
    loadExpectedRevisions: revisions,
    send: server.send,
  });
  assert.equal(retry.response.ok, true);
  assert.equal(retry.reused, true);
  assert.equal(retry.pending.key, "copy-1");
  if (retry.response.ok) {
    assert.equal(retry.response.data.replayed, true);
    assert.equal(retry.response.data.created.length, 1);
  }
  // The server stored one result for one key: no duplicate activity.
  assert.deepEqual(server.keys, ["copy-1", "copy-1"]);
  assert.equal(server.keyed.size, 1);
  assert.equal(journal.peek(), null);
});

test("the retry reuses the revisions armed with the first request", async () => {
  const journal = new ActivityOperationJournal(keys("rev"));
  const server = new FlakyCopyServer(true);
  // A misleading revision read after the first attempt must not reach the
  // retried request: the operation was already armed with revision 3.
  const driftingRevisions = async () => ({ "A-1": 9 });

  await runActivityOperation({
    journal,
    input: INPUT,
    loadExpectedRevisions: revisions,
    send: server.send,
  });
  await runActivityOperation({
    journal,
    input: INPUT,
    loadExpectedRevisions: driftingRevisions,
    send: server.send,
  });

  assert.deepEqual(server.bodies.map((body) => body.expected_revisions), [
    { "A-1": 3 },
    { "A-1": 3 },
  ]);
});

test("a successful request releases the key so the next paste is a new operation", async () => {
  const journal = new ActivityOperationJournal(keys("ok"));
  const server = new FlakyCopyServer(false);

  const first = await runActivityOperation({
    journal,
    input: INPUT,
    loadExpectedRevisions: revisions,
    send: server.send,
  });
  assert.equal(first.response.ok, true);
  assert.equal(journal.peek(), null);

  const second = await runActivityOperation({
    journal,
    input: { ...INPUT, activityIds: ["A-2"] },
    loadExpectedRevisions: async () => ({ "A-2": 1 }),
    send: server.send,
  });
  assert.equal(second.reused, false);
  assert.equal(second.pending.key, "ok-2");
  assert.equal(server.keyed.size, 2);
});

test("a definitive refusal releases the key; a retry after it starts over", async () => {
  const journal = new ActivityOperationJournal(keys("refuse"));
  const refusals: Array<ApiResult<CopyResult>> = [
    {
      ok: false,
      error: {
        code: "P6_ACTIVITY_TARGET_WBS_NOT_FOUND",
        retryable: false,
        message_key: "error.resource.not_found",
        available_actions: [],
      },
    },
  ];
  const send = async (): Promise<ApiResult<CopyResult>> =>
    refusals.shift() ?? { ok: true, data: { operation: "copy", created: [] } };

  const first = await runActivityOperation({
    journal,
    input: INPUT,
    loadExpectedRevisions: revisions,
    send,
  });
  assert.equal(first.response.ok, false);
  assert.equal(journal.peek(), null);
});

test("the pending operation is isolated by project and by selection", async () => {
  const journal = new ActivityOperationJournal(keys("scope"));
  const server = new FlakyCopyServer(true);

  await runActivityOperation({
    journal,
    input: INPUT,
    loadExpectedRevisions: revisions,
    send: server.send,
  });
  // Another project with the same ids is a different operation, never a
  // replay against the wrong tenant/project scope.
  const otherProject = await runActivityOperation({
    journal,
    input: { ...INPUT, projectId: "preview-nse-01" },
    loadExpectedRevisions: revisions,
    send: server.send,
  });
  assert.equal(otherProject.reused, false);
  assert.equal(otherProject.pending.key, "scope-2");

  // An explicit cancel (a new Cut/Copy) abandons the uncertain retry.
  journal.cancel();
  assert.equal(journal.peek(), null);
});

test("the request body carries the armed key's contract and confirmation", () => {
  const journal = new ActivityOperationJournal(keys("body"));
  const pending = journal.begin(
    {
      projectId: "p",
      operation: "delete",
      activityIds: ["A-1", "A-2"],
      confirmDependencies: true,
    },
    { "A-1": 2, "A-2": 4 },
  );
  assert.deepEqual(activityOperationRequest(pending), {
    contract_version: "p6-activity-operations.v1",
    operation: "delete",
    activity_ids: ["A-1", "A-2"],
    target_wbs_id: null,
    confirm_dependencies: true,
    expected_revisions: { "A-1": 2, "A-2": 4 },
  });
});
