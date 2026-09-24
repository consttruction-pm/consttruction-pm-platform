import type { ClientError } from "./client.js";

export type ConflictPresentation = {
  code: string;
  retryable: boolean;
  actions: string[];
  message_key: string;
};

export function presentClientError(error: ClientError): ConflictPresentation {
  return {
    code: error.code,
    retryable: error.retryable,
    actions: [...error.available_actions],
    message_key: error.message_key,
  };
}
