/**
 * CSRF protection is a signed double submit. The login response sets a
 * readable `cubi_csrf` cookie whose value is an HMAC of the HttpOnly session
 * token under a server-held secret. Mutating requests must echo that value in
 * the `X-CSRF-Token` header; the server recomputes it and rejects a mismatch.
 */
export const CSRF_COOKIE_NAME = "cubi_csrf";
export const CSRF_HEADER_NAME = "X-CSRF-Token";

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function readCookieValue(
  name: string,
  cookieHeader: string = typeof document === "undefined" ? "" : document.cookie,
): string | null {
  for (const part of cookieHeader.split(";")) {
    const separator = part.indexOf("=");
    if (separator < 0) continue;
    if (part.slice(0, separator).trim() !== name) continue;
    const raw = part.slice(separator + 1).trim();
    try {
      return decodeURIComponent(raw);
    } catch {
      return raw;
    }
  }
  return null;
}

export function withCsrfHeader(
  method: string,
  headers: Record<string, string> = {},
  cookieHeader?: string,
): Record<string, string> {
  if (!MUTATING_METHODS.has(method.toUpperCase())) return headers;
  const token = readCookieValue(CSRF_COOKIE_NAME, cookieHeader);
  if (!token) return headers;
  if (Object.keys(headers).some((key) => key.toLowerCase() === CSRF_HEADER_NAME.toLowerCase())) {
    return headers;
  }
  return { ...headers, [CSRF_HEADER_NAME]: token };
}
