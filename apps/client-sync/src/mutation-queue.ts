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
export type SyncDisposition = "acknowledged" | "retry" | "conflict" | "rejected";
export type SyncOutcome = { contract_version: "sync-outcome.v1"; mutation_id: string; disposition: SyncDisposition; error_code?: string | null; retry_after_seconds?: number | null; };
export type AuthoritativeSyncOutcome = {
  contract_version: "client-sync-outcome.v1";
  status: "applied" | "replayed" | "conflict" | "rejected";
  operation?: string | null;
  revision?: number | null;
  error_code?: string | null;
  retryable?: boolean | null;
  idempotency_key?: string | null;
};

export function toAuthoritativeSyncOutcome(
  mutation: SyncMutation,
  outcome: SyncOutcome,
): AuthoritativeSyncOutcome {
  if (outcome.contract_version !== "sync-outcome.v1") {
    throw new Error("UNSUPPORTED_OUTCOME_CONTRACT");
  }
  if (outcome.mutation_id !== mutation.mutation_id) {
    throw new Error("MUTATION_ID_MISMATCH");
  }
  if (outcome.disposition === "retry") {
    throw new Error("UNREPRESENTABLE_RETRY_OUTCOME");
  }
  if (outcome.retry_after_seconds !== null && outcome.retry_after_seconds !== undefined) {
    throw new Error("UNREPRESENTABLE_RETRY_METADATA");
  }
  const status = outcome.disposition === "acknowledged" ? "applied" : outcome.disposition;
  return {
    contract_version: "client-sync-outcome.v1",
    status,
    operation: mutation.operation,
    error_code: outcome.error_code ?? null,
    retryable: null,
    idempotency_key: mutation.idempotency_key,
  };
}

export function fromAuthoritativeSyncOutcome(
  mutation: SyncMutation,
  outcome: AuthoritativeSyncOutcome,
): SyncOutcome {
  if (outcome.contract_version !== "client-sync-outcome.v1") {
    throw new Error("UNSUPPORTED_AUTHORITATIVE_OUTCOME_CONTRACT");
  }
  if (outcome.idempotency_key != null && outcome.idempotency_key !== mutation.idempotency_key) {
    throw new Error("IDEMPOTENCY_KEY_MISMATCH");
  }
  if (outcome.operation != null && outcome.operation !== mutation.operation) {
    throw new Error("OPERATION_MISMATCH");
  }
  if (outcome.revision != null) {
    throw new Error("UNREPRESENTABLE_REVISION");
  }
  if (outcome.retryable != null) {
    throw new Error("UNREPRESENTABLE_RETRYABLE");
  }
  const disposition: SyncDisposition =
    outcome.status === "applied" || outcome.status === "replayed"
      ? "acknowledged"
      : outcome.status;
  return {
    contract_version: "sync-outcome.v1",
    mutation_id: mutation.mutation_id,
    disposition,
    error_code: outcome.error_code ?? null,
  };
}

export class OfflineMutationQueue {
  private readonly pendingMutations: SyncMutation[] = [];
  private readonly mutationIds = new Set<string>();
  private readonly idempotencyKeys = new Map<string,string>();
  enqueue(mutation: SyncMutation): void {
    if (mutation.contract_version !== "sync-mutation.v1") throw new Error("UNSUPPORTED_MUTATION_CONTRACT");
    if (!Number.isSafeInteger(mutation.expected_revision) || mutation.expected_revision < 0) throw new Error("INVALID_EXPECTED_REVISION");
    if (!mutation.mutation_id || !mutation.idempotency_key) throw new Error("INVALID_MUTATION_METADATA");
    const existingMutation=this.idempotencyKeys.get(mutation.idempotency_key);
    if (existingMutation && existingMutation !== mutation.mutation_id) throw new Error("IDEMPOTENCY_KEY_REUSE");
    if (this.mutationIds.has(mutation.mutation_id)) return;
    this.pendingMutations.push(Object.freeze({...mutation}));
    this.mutationIds.add(mutation.mutation_id); this.idempotencyKeys.set(mutation.idempotency_key,mutation.mutation_id);
  }
  retryAtRevision(mutationId:string, expectedRevision:number):SyncMutation {
    if (!Number.isSafeInteger(expectedRevision) || expectedRevision < 0) throw new Error("INVALID_EXPECTED_REVISION");
    const index=this.pendingMutations.findIndex(m=>m.mutation_id===mutationId);
    if(index<0) throw new Error("MUTATION_NOT_PENDING");
    const current=this.pendingMutations[index];
    if(current.expected_revision===expectedRevision) return current;
    const mutation=Object.freeze({...current,expected_revision:expectedRevision,idempotency_key:current.idempotency_key+":r"+expectedRevision});
    const existingMutation=this.idempotencyKeys.get(mutation.idempotency_key);
    if(existingMutation && existingMutation!==mutationId) throw new Error("IDEMPOTENCY_KEY_REUSE");
    this.idempotencyKeys.delete(current.idempotency_key); this.idempotencyKeys.set(mutation.idempotency_key,mutationId); this.pendingMutations[index]=mutation; return mutation;
  }
  pending():readonly SyncMutation[]{return this.pendingMutations.slice();}
  peek():SyncMutation|undefined{return this.pendingMutations[0];}
  applyOutcome(outcome:SyncOutcome):void {
    if(outcome.contract_version!=="sync-outcome.v1") throw new Error("UNSUPPORTED_OUTCOME_CONTRACT");
    if(outcome.disposition!=="acknowledged") return;
    const index=this.pendingMutations.findIndex(m=>m.mutation_id===outcome.mutation_id); if(index<0)return;
    const [removed]=this.pendingMutations.splice(index,1); this.mutationIds.delete(removed.mutation_id); this.idempotencyKeys.delete(removed.idempotency_key);
  }
  acknowledge(mutationId:string):void{this.applyOutcome({contract_version:"sync-outcome.v1",mutation_id:mutationId,disposition:"acknowledged"});}
  size():number{return this.pendingMutations.length;}
}
