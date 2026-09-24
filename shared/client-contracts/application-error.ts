export type ApplicationErrorCategory =
  | "validation"
  | "context"
  | "conflict"
  | "authorization"
  | "not_found"
  | "persistence";

export type ApplicationError = {
  category: ApplicationErrorCategory;
  code: string;
  message: string;
  retryable: boolean;
};

export type ApplicationErrorEnvelope = { error: ApplicationError };

export function isApplicationErrorEnvelope(value: unknown): value is ApplicationErrorEnvelope {
  if (!value || typeof value !== "object") return false;
  const error = (value as { error?: unknown }).error;
  if (!error || typeof error !== "object") return false;
  const candidate = error as Record<string, unknown>;
  return (
    typeof candidate.category === "string" &&\n    ["validation", "context", "conflict", "authorization", "not_found", "persistence"].includes(candidate.category) &&
    typeof candidate.code === "string" && candidate.code.length > 0 &&
    typeof candidate.message === "string" && candidate.message.length > 0 &&
    typeof candidate.retryable === "boolean"
  );
}
