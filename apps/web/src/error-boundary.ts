import type { ClientError } from "./client.js";
import type { ApplicationErrorCategory } from "../../../shared/client-contracts/application-error";

export type ConflictPresentation = {
  category?: ApplicationErrorCategory;
  code: string;
  retryable: boolean;
  actions: string[];
  message?: string;
  message_key?: string;
};

export function presentClientError(error: ClientError): ConflictPresentation {
  return {
    category: error.category,
    code: error.code,
    retryable: error.retryable,
    actions: [...error.available_actions],
    message: error.message,
    message_key: error.message_key,
  };
}
