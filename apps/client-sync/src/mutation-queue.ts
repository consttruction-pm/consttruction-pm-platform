export type SyncMutation = {
  contract_version: "sync-mutation.v1";
  mutation_id: string;
  tenant_id: string;
  project_id: string;
  expected_revision: number;
  operation: string;
  payload: Record<string, unknown>;
  idempotency_key: string;
};

export type SyncDisposition =
  | "acknowledged"
  | "retry"
  | "conflict"
  | "rejected";

export type SyncOutcome = {
  contract_version: "sync-outcome.v1";
  mutation_id: string;
  disposition: SyncDisposition;
  error_code?: string | null;
  retry_after_seconds?: number | null;
};

export class OfflineMutationQueue {
  private readonly pendingMutations: SyncMutation[] = [];
  private readonly mutationIds = new Set<string>();
  private readonly idempotencyKeys = new Map<string, string>();

  enqueue(mutation: SyncMutation): void {
    if (mutation.contract_version !== "sync-mutation.v1") {
      throw new Error("UNSUPPORTED_MUTATION_CONTRACT");
    }
    if (mutation.expected_revision < 0) {
      throw new Error("INVALID_EXPECTED_REVISION");
    }
    if (!mutation.mutation_id || !mutation.idempotency_key) {
      throw new Error("INVALID_MUTATION_METADATA");
    }

    const existingMutation = this.idempotencyKeys.get(mutation.idempotency_key);
    if (existingMutation && existingMutation !== mutation.mutation_id) {
      throw new Error("IDEMPOTENCY_KEY_REUSE");
    }
    if (this.mutationIds.has(mutation.mutation_id)) {
      return;
    }

    this.pendingMutations.push(Object.freeze({ ...mutation }));
    this.mutationIds.add(mutation.mutation_id);
    this.idempotencyKeys.set(mutation.idempotency_key, mutation.mutation_id);
  }

  pending(): readonly SyncMutation[] {
    return this.pendingMutations.slice();
  }

  peek(): SyncMutation | undefined {
    return this.pendingMutations[0];
  }

  applyOutcome(outcome: SyncOutcome): void {
    if (outcome.contract_version !== "sync-outcome.v1") {
      throw new Error("UNSUPPORTED_OUTCOME_CONTRACT");
    }
    if (outcome.disposition !== "acknowledged") {
      return;
    }

    const index = this.pendingMutations.findIndex(
      (mutation) => mutation.mutation_id === outcome.mutation_id,
    );
    if (index < 0) {
      return;
    }

    const [removed] = this.pendingMutations.splice(index, 1);
    this.mutationIds.delete(removed.mutation_id);
    this.idempotencyKeys.delete(removed.idempotency_key);
  }

  acknowledge(mutationId: string): void {
    this.applyOutcome({
      contract_version: "sync-outcome.v1",
      mutation_id: mutationId,
      disposition: "acknowledged",
    });
  }

  size(): number {
    return this.pendingMutations.length;
  }
}
