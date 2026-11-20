/**
 * Session and environment access model.
 *
 * The server is the only authority. This module classifies the roles that the
 * server returned so the UI can explain access; it never grants access, and
 * every mutating API call is re-authorized server-side.
 */

import type { SessionInfo } from "./api.js";

export const ENTERPRISE_ROLES = ["enterprise_admin", "enterprise_user", "enterprise_viewer"] as const;
export type EnterpriseTier = "admin" | "user" | "viewer";

export type EnvironmentAccess = {
  engineering: { allowed: boolean; reason: string };
  enterprise: { allowed: boolean; tier: EnterpriseTier | null; reason: string };
};

export function enterpriseTier(roles: readonly string[]): EnterpriseTier | null {
  if (roles.includes("enterprise_admin")) return "admin";
  if (roles.includes("enterprise_user")) return "user";
  if (roles.includes("enterprise_viewer")) return "viewer";
  return null;
}

export function isEnterpriseWriter(roles: readonly string[]): boolean {
  const tier = enterpriseTier(roles);
  return tier === "admin" || tier === "user";
}

export function environmentAccess(session: SessionInfo | null): EnvironmentAccess {
  if (!session) {
    return {
      engineering: { allowed: false, reason: "Sign in to enter an environment." },
      enterprise: { allowed: false, tier: null, reason: "Sign in to enter an environment." },
    };
  }
  const tier = enterpriseTier(session.roles);
  return {
    engineering: {
      allowed: true,
      reason: "Project permissions are checked by the Engineering server on every request.",
    },
    enterprise: tier
      ? { allowed: true, tier, reason: `Enterprise ${tier} entitlement is present on this server session.` }
      : {
          allowed: false,
          tier: null,
          reason: "This session carries project roles only. Enterprise requires enterprise_viewer, enterprise_user or enterprise_admin, granted by an administrator.",
        },
  };
}

const LAST_ENV_KEY = "cubi.enterprise.last-environment";

export type EnvironmentId = "engineering" | "enterprise";

export function readLastEnvironment(): EnvironmentId | null {
  try {
    const value = window.localStorage.getItem(LAST_ENV_KEY);
    return value === "engineering" || value === "enterprise" ? value : null;
  } catch {
    return null;
  }
}

export function rememberLastEnvironment(id: EnvironmentId): void {
  try {
    window.localStorage.setItem(LAST_ENV_KEY, id);
  } catch {
    // Non-fatal preference.
  }
}

export function displayName(userId: string): string {
  const cleaned = userId.replace(/^(preview-|user-)/, "").replace(/[._-]+/g, " ").trim();
  if (!cleaned) return userId;
  return cleaned.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function initials(userId: string): string {
  const parts = displayName(userId).split(/\s+/).filter(Boolean);
  return (parts[0]?.[0] ?? "?").toUpperCase() + (parts[1]?.[0] ?? "").toUpperCase();
}

export function formatDateTime(value: string | null | undefined, locale: string): string {
  if (!value) return "—";
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  try {
    return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(parsed);
  } catch {
    return new Date(parsed).toISOString();
  }
}

export function formatDate(value: string | null | undefined, locale: string): string {
  if (!value) return "—";
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  try {
    return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(parsed);
  } catch {
    return new Date(parsed).toISOString().slice(0, 10);
  }
}
