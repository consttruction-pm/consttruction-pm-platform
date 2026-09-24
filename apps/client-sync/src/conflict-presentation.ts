import type { SyncMutation, SyncOutcome } from "./mutation-queue.ts";

export type SyncConflictPresentation = {
  mutation_id: string;
  error_code: string;
  expected_revision: number;
  available_actions: readonly string[];
  message_key: string;
};

const STALE_REVISION_ACTIONS = [
  "discard",
  "refresh_and_retry",
  "defer",
] as const;

export function presentSyncConflict(
  mutation: SyncMutation,
  outcome: SyncOutcome,
): SyncConflictPresentation | null {
  if (outcome.disposition !== "conflict") return null;

  const errorCode = outcome.error_code ?? "SYNC_CONFLICT";
  const actions =
    errorCode === "STALE_REVISION" ? STALE_REVISION_ACTIONS : ["defer"];

  return {
    mutation_id: mutation.mutation_id,
    error_code: errorCode,
    expected_revision: mutation.expected_revision,
    available_actions: actions,
    message_key: `sync.error.${errorCode}`,
  };
}
