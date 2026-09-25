import {
  OfflineMutationQueue,
  type SyncMutation,
  type SyncOutcome,
} from "./mutation-queue.ts";

import type { SyncProjectRevision } from "./revision-transport.ts";

export interface ClientSyncRevisionTransport {
  refresh(context: {
    tenant_id: string;
    project_id: string;
    revision: number;
  }): Promise<SyncProjectRevision>;
}

export interface ClientSyncTransport {
  submit(mutation: SyncMutation): Promise<SyncOutcome>;
}

export class ClientSyncRunner {
  private readonly queue: OfflineMutationQueue;
  private readonly transport: ClientSyncTransport;

  constructor(queue: OfflineMutationQueue, transport: ClientSyncTransport) {
    this.queue = queue;
    this.transport = transport;
  }

  async refreshConflictRevision(mutationId: string, revisionTransport: ClientSyncRevisionTransport): Promise<SyncProjectRevision> {
    const mutation = this.queue.pending().find((item) => item.mutation_id === mutationId);
    if (!mutation) throw new Error("MUTATION_NOT_PENDING");

    const revision = await revisionTransport.refresh({
      tenant_id: mutation.tenant_id,
      project_id: mutation.project_id,
      revision: mutation.expected_revision,
    });
    if (
      revision.tenant_id !== mutation.tenant_id ||
      revision.project_id !== mutation.project_id ||
      !Number.isSafeInteger(revision.revision) || revision.revision < 0
    ) {
      throw new Error("INVALID_PROJECT_REVISION_RESPONSE");
    }
    return revision;
  }

  async retryConflictAtAuthoritativeRevision(
    mutationId: string,
    revisionTransport: ClientSyncRevisionTransport,
  ): Promise<SyncMutation> {
    const revision = await this.refreshConflictRevision(mutationId, revisionTransport);
    return this.queue.retryAtRevision(mutationId, revision.revision);
  }

  async runOnce(): Promise<readonly SyncOutcome[]> {
    const outcomes: SyncOutcome[] = [];
    for (const mutation of this.queue.pending()) {
      const outcome = await this.transport.submit(mutation);
      if (outcome.mutation_id !== mutation.mutation_id) throw new Error("MUTATION_ID_MISMATCH");
      outcomes.push(outcome);
      this.queue.applyOutcome(outcome);
      if (outcome.disposition !== "acknowledged") break;
    }
    return outcomes;
  }
}
