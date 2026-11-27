import type { ApiResult } from "./client.js";

export const ACTIVITY_OPERATION_CONTRACT_VERSION = "p6-activity-operations.v1";

export type ActivityOperationName = "copy" | "move" | "delete";

export type ActivityOperationInput = {
  projectId: string;
  operation: ActivityOperationName;
  activityIds: readonly string[];
  targetWbsId?: string | null;
  confirmDependencies?: boolean;
};

/**
 * One accepted Cut/Copy/Paste/Delete request whose outcome may still be
 * unknown. The key and the armed revisions belong to the operation, not to
 * the call that happens to retry it: a lost response must replay the stored
 * server result instead of creating a second set of activities.
 */
export type PendingActivityOperation = {
  key: string;
  projectId: string;
  operation: ActivityOperationName;
  activityIds: readonly string[];
  targetWbsId: string | null;
  confirmDependencies: boolean;
  expectedRevisions: Record<string, number>;
};

export type ActivityOperationRequest = {
  contract_version: string;
  operation: ActivityOperationName;
  activity_ids: string[];
  target_wbs_id: string | null;
  confirm_dependencies: boolean;
  expected_revisions: Record<string, number>;
};

export function activityOperationRequest(
  pending: PendingActivityOperation,
): ActivityOperationRequest {
  return {
    contract_version: ACTIVITY_OPERATION_CONTRACT_VERSION,
    operation: pending.operation,
    activity_ids: [...pending.activityIds],
    target_wbs_id: pending.targetWbsId,
    confirm_dependencies: pending.confirmDependencies,
    expected_revisions: { ...pending.expectedRevisions },
  };
}

export function createActivityOperationKey(): string {
  const cryptoApi = globalThis.crypto;
  if (cryptoApi && typeof cryptoApi.randomUUID === "function") {
    return cryptoApi.randomUUID();
  }
  return `activity-op-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function sameSelection(left: readonly string[], right: readonly string[]): boolean {
  if (left.length !== right.length) return false;
  const a = [...left].sort();
  const b = [...right].sort();
  return a.every((value, index) => value === b[index]);
}

/**
 * Session memory for the one paste/delete whose result may be in doubt.
 *
 * The clipboard itself stays project-scoped and lives only in memory; the
 * journal deliberately has no persistence because a browser reload ends the
 * user's pending operation and a fresh key is then correct.
 */
export class ActivityOperationJournal {
  private pending: PendingActivityOperation | null = null;

  constructor(
    private readonly createKey: () => string = createActivityOperationKey,
  ) {}

  peek(): PendingActivityOperation | null {
    return this.pending;
  }

  /**
   * Return the pending operation when this input retries it, otherwise arm a
   * new one. ``expectedRevisions`` is only read when a new key is created.
   */
  begin(
    input: ActivityOperationInput,
    expectedRevisions: Record<string, number>,
  ): PendingActivityOperation {
    const current = this.pending;
    if (current && matches(current, input)) return current;
    const pending: PendingActivityOperation = {
      key: this.createKey(),
      projectId: input.projectId,
      operation: input.operation,
      activityIds: [...input.activityIds],
      targetWbsId: input.targetWbsId ?? null,
      confirmDependencies: input.confirmDependencies === true,
      expectedRevisions: { ...expectedRevisions },
    };
    this.pending = pending;
    return pending;
  }

  /** The outcome is known (success or a definitive refusal) — forget the key. */
  settle(pending: PendingActivityOperation): void {
    if (this.pending && this.pending.key === pending.key) this.pending = null;
  }

  /** The user started a different operation; an uncertain retry is abandoned. */
  cancel(): void {
    this.pending = null;
  }
}

function matches(
  pending: PendingActivityOperation,
  input: ActivityOperationInput,
): boolean {
  return (
    pending.projectId === input.projectId
    && pending.operation === input.operation
    && (pending.targetWbsId ?? null) === (input.targetWbsId ?? null)
    && pending.confirmDependencies === (input.confirmDependencies === true)
    && sameSelection(pending.activityIds, input.activityIds)
  );
}

function isUncertain(error: { code: string; retryable: boolean }): boolean {
  return (
    error.retryable === true
    || error.code === "NETWORK_ERROR"
    || error.code === "NETWORK_TIMEOUT"
  );
}

export type ActivityOperationRun<T> = {
  response: ApiResult<T>;
  pending: PendingActivityOperation;
  reused: boolean;
};

/**
 * Send one operation with a key that survives an uncertain outcome.
 *
 * A retry of the same clipboard operation reuses the original key *and* the
 * revisions armed with it, so the server replays the committed result instead
 * of applying the edit twice. Definitive refusals and successes release the
 * key; only a retryable transport/server failure keeps it alive.
 */
export async function runActivityOperation<T>(options: {
  journal: ActivityOperationJournal;
  input: ActivityOperationInput;
  loadExpectedRevisions: (
    activityIds: readonly string[],
  ) => Promise<Record<string, number>>;
  send: (
    pending: PendingActivityOperation,
    request: ActivityOperationRequest,
  ) => Promise<ApiResult<T>>;
}): Promise<ActivityOperationRun<T>> {
  const existing = options.journal.peek();
  const reuse = existing !== null && matches(existing, options.input);
  const pending = reuse
    ? (existing as PendingActivityOperation)
    : options.journal.begin(
        options.input,
        await options.loadExpectedRevisions(options.input.activityIds),
      );
  const response = await options.send(pending, activityOperationRequest(pending));
  if (response.ok || !isUncertain(response.error)) {
    options.journal.settle(pending);
  }
  return { response, pending, reused: reuse };
}
