export type ProjectContext = {
  tenant_id: string;
  project_id: string;
  revision: number;
};

export type ClientError = {
  code: string;
  retryable: boolean;
  message_key: string;
  available_actions: string[];
};

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: ClientError };

export interface ApiTransport {
  get<T>(path: string, context: ProjectContext): Promise<ApiResult<T>>;
  post<TRequest, TResponse>(
    path: string,
    request: TRequest,
    context: ProjectContext,
    idempotencyKey?: string,
  ): Promise<ApiResult<TResponse>>;
}

export class FetchApiTransport implements ApiTransport {
  constructor(private readonly baseUrl: string) {}

  async get<T>(path: string, context: ProjectContext): Promise<ApiResult<T>> {
    return this.request<T>(path, {
      method: "GET",
      headers: this.contextHeaders(context),
    });
  }

  async post<TRequest, TResponse>(
    path: string,
    request: TRequest,
    context: ProjectContext,
    idempotencyKey?: string,
  ): Promise<ApiResult<TResponse>> {
    const headers = {
      ...this.contextHeaders(context),
      "Content-Type": "application/json",
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
    };
    return this.request<TResponse>(path, {
      method: "POST",
      headers,
      body: JSON.stringify(request),
    });
  }

  private contextHeaders(context: ProjectContext): Record<string, string> {
    return {
      "X-Tenant-Id": context.tenant_id,
      "X-Project-Id": context.project_id,
      "X-Project-Revision": String(context.revision),
    };
  }

  private async request<T>(
    path: string,
    init: RequestInit,
  ): Promise<ApiResult<T>> {
    try {
      const response = await fetch(new URL(path, this.baseUrl), init);
      const payload = await response.json().catch(() => null);

      if (response.ok) {
        return { ok: true, data: payload as T };
      }

      return {
        ok: false,
        error: {
          code: String(payload?.code ?? "API_ERROR"),
          retryable: Boolean(payload?.retryable ?? false),
          message_key: String(payload?.message_key ?? "error.api"),
          available_actions: Array.isArray(payload?.available_actions)
            ? payload.available_actions.map(String)
            : [],
        },
      };
    } catch {
      return {
        ok: false,
        error: {
          code: "NETWORK_ERROR",
          retryable: true,
          message_key: "error.network",
          available_actions: ["retry"],
        },
      };
    }
  }
}
