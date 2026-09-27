import type { LanguagePackManifest } from "../../client-sync/src/language-pack-manifest.js";
import type { LanguagePackResource } from "../../client-sync/src/language-pack-resource-validation.js";
import type { LanguagePackSignatureVerifier } from "../../client-sync/src/language-pack-integrity.js";
import type { ActivatedLanguagePack } from "../../client-sync/src/language-pack-activation.js";
import type { WebSyncRuntime } from "./sync-runtime.js";

export type LanguageManagerRouteState = Readonly<{
  active: ActivatedLanguagePack | null;
  offline: boolean;
  status: "idle" | "updating" | "rolling-back" | "error";
  error: string | null;
}>;

export type LanguageManagerRouteOptions = Readonly<{
  manifest: LanguagePackManifest;
  artifact: Uint8Array;
  resources: readonly LanguagePackResource[];
  verifySignature: LanguagePackSignatureVerifier;
}>;

export type LanguageManagerRoute = Readonly<{
  getState(): LanguageManagerRouteState;
  useOffline(): ActivatedLanguagePack;
  rollback(): ActivatedLanguagePack;
  update(options: LanguageManagerRouteOptions): LanguageManagerRouteState;
  mount(container: HTMLElement): void;
}>;

export function createLanguageManagerRoute(
  runtime: WebSyncRuntime,
  initial: LanguageManagerRouteState = {
    active: runtime.languagePacks().getActive(),
    offline: false,
    status: "idle",
    error: null,
  },
): LanguageManagerRoute {
  let state = initial;

  const publish = (container?: HTMLElement): void => {
    if (container) renderLanguageManagerRoute(container, state);
  };

  let mounted: HTMLElement | null = null;

  const setError = (error: unknown): LanguageManagerRouteState => {
    state = {
      ...state,
      status: "error",
      error: error instanceof Error ? error.message : String(error),
    };
    publish(mounted ?? undefined);
    return state;
  };

  return {
    getState: () => state,

    useOffline: () => {
      try {
        const active = runtime.languagePacks().activateOffline();
        state = { active, offline: true, status: "idle", error: null };
        publish(mounted ?? undefined);
        return active;
      } catch (error) {
        setError(error);
        throw error;
      }
    },

    rollback: () => {
      try {
        state = { ...state, status: "rolling-back", error: null };
        publish(mounted ?? undefined);
        const active = runtime.languagePacks().rollback();
        state = { active, offline: false, status: "idle", error: null };
        publish(mounted ?? undefined);
        return active;
      } catch (error) {
        setError(error);
        throw error;
      }
    },

    update: (options) => {
      try {
        state = { ...state, status: "updating", error: null };
        publish(mounted ?? undefined);
        const result = runtime.languagePacks().update(
          options.artifact,
          options.manifest,
          options.resources,
          options.verifySignature,
        );
        state = {
          active: result.updated
            ? runtime.languagePacks().getActive()
            : state.active,
          offline: false,
          status: "idle",
          error: null,
        };
        publish(mounted ?? undefined);
        return state;
      } catch (error) {
        return setError(error);
      }
    },

    mount: (container) => {
      mounted = container;
      renderLanguageManagerRoute(container, state);
    },
  };
}

export function renderLanguageManagerRoute(
  container: HTMLElement,
  state: LanguageManagerRouteState,
): void {
  const version = state.active?.manifest.version ?? "—";
  const language = state.active?.manifest.language_tag ?? "—";
  const status = state.error ?? state.status;

  container.innerHTML = `
    <section data-language-manager-route aria-labelledby="language-manager-title">
      <header>
        <h1>Language Manager</h1>
        <div data-language-pack-status>${escapeHtml(status)}</div>
      </header>
      <dl>
        <div><dt id="language-manager-language-label">Language</dt><dd data-language-tag aria-labelledby="language-manager-language-label">${escapeHtml(language)}</dd></div>
        <div><dt id="language-manager-version-label">Version</dt><dd data-language-version aria-labelledby="language-manager-version-label">${escapeHtml(version)}</dd></div>
        <div><dt id="language-manager-offline-label">Offline</dt><dd data-language-offline aria-labelledby="language-manager-offline-label">${state.offline ? "true" : "false"}</dd></div>
      </dl>
    </section>
  `;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character] ?? character);
}
