import {
  OfflineMutationQueue,
  type SyncMutation,
  type SyncOutcome,
} from "./mutation-queue.ts";

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
