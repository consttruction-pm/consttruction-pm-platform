import type { ProjectContext } from "../../../shared/client-contracts/project-context";
import {
  type ApplicationErrorCategory,
  isApplicationErrorEnvelope,
} from "../../../shared/client-contracts/application-error";

export type { ProjectContext } from "../../../shared/client-contracts/project-context";

export type ClientError = {
  category?: ApplicationErrorCategory;
  code: string;
  retryable: boolean;
  message?: string;
  message_key?: string;
  available_actions: string[];
  expected_revision?: number;
  actual_revision?: number;
  details?: Record<string, unknown>;
};

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: ClientError };

export interface ApiTransport {
  get<T>(path: string, context: ProjectContext): Promise<ApiResult<T>>;
  post<TRequest, TResponse>(path: string, request: TRequest, context: ProjectContext, idempotencyKey?: string): Promise<ApiResult<TResponse>>;
}

export class FetchApiTransport implements ApiTransport {
  constructor(private readonly baseUrl: string) {}

  async get<T>(path: string, context: ProjectContext): Promise<ApiResult<T>> {
    return this.request<T>(path, { method: "GET", headers: this.contextHeaders(context) });
  }

  async post<TRequest, TResponse>(path: string, request: TRequest, context: ProjectContext, idempotencyKey?: string): Promise<ApiResult<TResponse>> {
    const headers = {
      ...this.contextHeaders(context),
      "Content-Type": "application/json",
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
    };
    return this.request<TResponse>(path, { method: "POST", headers, body: JSON.stringify(request) });
  }

  private contextHeaders(context: ProjectContext): Record<string, string> {
    return { "X-Tenant-Id": context.tenant_id, "X-Project-Id": context.project_id, "X-Project-Revision": String(context.revision) };
  }

  private async request<T>(path: string, init: RequestInit): Promise<ApiResult<T>> {
    const response = await fetch(new URL(path, this.baseUrl), init);
    const payload = await response.json().catch(() => null);
    if (response.ok) return { ok: true, data: payload as T };

    if (isApplicationErrorEnvelope(payload)) {
      return {
        ok: false,
        error: {
          category: payload.error.category,
          code: payload.error.code,
          retryable: payload.error.retryable,
          message: payload.error.message,
          available_actions: Array.isArray((payload.error as Record<string, unknown>).available_actions)
            ? ((payload.error as Record<string, unknown>).available_actions as unknown[]).map(String)
            : [],
          expected_revision: typeof (payload.error as Record<string, unknown>).expected_revision === "number"
            ? (payload.error as Record<string, unknown>).expected_revision as number
            : undefined,
          actual_revision: typeof (payload.error as Record<string, unknown>).actual_revision === "number"
            ? (payload.error as Record<string, unknown>).actual_revision as number
            : undefined,
          details: (payload.error as Record<string, unknown>).details &&
            typeof (payload.error as Record<string, unknown>).details === "object"
            ? { ...((payload.error as Record<string, unknown>).details as Record<string, unknown>) }
            : undefined,
        },
      };
    }

    return {
      ok: false,
      error: {
        code: String(payload?.code ?? "API_ERROR"),
        retryable: Boolean(payload?.retryable ?? false),
        message_key: String(payload?.message_key ?? "error.api"),
        available_actions: Array.isArray(payload?.available_actions) ? payload.available_actions.map(String) : [],
      },
    };
  }
}
