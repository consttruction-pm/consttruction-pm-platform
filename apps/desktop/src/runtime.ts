import { ClientLanguageRuntime } from "../../client-sync/src/language-runtime.js";
import { LanguageManagerController } from "../../client-sync/src/language-manager-controller.js";
import type { LanguageRegistryEntry } from "../../client-sync/src/language.ts";
import {
  PersistentLanguagePackStore,
  type PersistentLanguagePackBackend,
} from "../../client-sync/src/persistent-language-pack-store.js";
import type { LanguagePreferenceStore } from "../../client-sync/src/language-preference-store.js";
import type {
  LanguagePackDownloadManifest,
  LanguagePackDownloadProgress,
  LanguagePackDownloadTransport,
  LanguagePackVerifier,
} from "../../client-sync/src/language-pack-download.js";
import { ApiRevisionTransport, type VersionedSyncRevisionApi } from "../../client-sync/src/revision-transport.js";
import {
  OfflineMutationQueue,
  type SyncMutation,
  type SyncOutcome,
} from "../../client-sync/src/mutation-queue.js";
import { ClientSyncRunner } from "../../client-sync/src/sync-runner.js";
import { ApiSyncTransport, type VersionedSyncApi } from "../../client-sync/src/api-sync-transport.js";
import { presentSyncConflict, type SyncConflictPresentation } from "../../client-sync/src/conflict-presentation.js";

export type OfflineMode = "offline" | "online";
export type DesktopProjectState = { tenant_id: string; project_id: string; revision: number; mode: OfflineMode };

export class DesktopRuntime {
  private readonly languageRuntime: ClientLanguageRuntime;
  constructor(
    private readonly languagePackBackend?: PersistentLanguagePackBackend,
    languagePreferenceStore?: LanguagePreferenceStore,
  ) {
    this.languageRuntime = new ClientLanguageRuntime(
      languagePackBackend
        ? new PersistentLanguagePackStore(languagePackBackend)
        : null,
      languagePreferenceStore ?? null,
    );
  }
  private state: DesktopProjectState | null = null;
  private readonly mutationQueue = new OfflineMutationQueue();
  openProject(tenant_id: string, project_id: string, revision: number, mode: OfflineMode = "offline"): DesktopProjectState {
    if (!tenant_id || !project_id || revision < 0) throw new Error("INVALID_PROJECT_CONTEXT");
    this.state = Object.freeze({ tenant_id, project_id, revision, mode }); return this.state;
  }
  current(): DesktopProjectState { if (!this.state) throw new Error("PROJECT_NOT_OPEN"); return this.state; }
  setMode(mode: OfflineMode): DesktopProjectState { const current = this.current(); this.state = Object.freeze({ ...current, mode }); return this.state; }
  advanceRevision(revision: number): DesktopProjectState { const current = this.current(); if (revision < current.revision) throw new Error("REVISION_REGRESSION"); this.state = Object.freeze({ ...current, revision }); return this.state; }
  queueMutation(mutation: SyncMutation): void { const current = this.current(); if (mutation.tenant_id !== current.tenant_id || mutation.project_id !== current.project_id) throw new Error("PROJECT_CONTEXT_MISMATCH"); this.mutationQueue.enqueue(mutation); }
  pendingMutationCount(): number { return this.mutationQueue.size(); }
  acknowledgeMutation(mutationId: string): void { this.mutationQueue.acknowledge(mutationId); }
  async syncOnce(api: VersionedSyncApi): Promise<readonly SyncOutcome[]> { return new ClientSyncRunner(this.mutationQueue, new ApiSyncTransport(api)).runOnce(); }
  presentConflict(mutation: SyncMutation, outcome: SyncOutcome): SyncConflictPresentation | null { return presentSyncConflict(mutation, outcome); }
  async refreshRevision(api: VersionedSyncRevisionApi): Promise<DesktopProjectState> {
    const current = this.current();
    const result = await new ApiRevisionTransport(api).refresh({
      tenant_id: current.tenant_id,
      project_id: current.project_id,
      revision: current.revision,
    });
    return this.advanceRevision(result.revision);
  }

  async retryStaleRevision(mutationId: string, outcome: SyncOutcome, revisionApi: VersionedSyncRevisionApi): Promise<SyncMutation> {
    if (outcome.mutation_id !== mutationId || outcome.disposition !== "conflict" || outcome.error_code !== "STALE_REVISION") {
      throw new Error("INVALID_STALE_REVISION_RETRY");
    }
    const current = this.current();
    const mutation = this.mutationQueue.pending().find((item) => item.mutation_id === mutationId);
    if (!mutation) throw new Error("MUTATION_NOT_PENDING");
    const revision = await new ApiRevisionTransport(revisionApi).refresh({
      tenant_id: current.tenant_id,
      project_id: current.project_id,
      revision: mutation.expected_revision,
    });
    if (revision.revision < current.revision) throw new Error("REVISION_REGRESSION");
    const retried = this.mutationQueue.retryAtRevision(mutationId, revision.revision);
    this.advanceRevision(revision.revision);
    return retried;
  }

  configureLanguage(
    registry: Parameters<ClientLanguageRuntime["configure"]>[0],
    defaultLanguage: string,
    preference: Parameters<ClientLanguageRuntime["configure"]>[2],
  ) {
    return this.languageRuntime.configure(registry, defaultLanguage, preference);
  }

  currentLanguage() {
    return this.languageRuntime.current();
  }

  createLanguageManagerController(
    registry: readonly LanguageRegistryEntry[],
  ): LanguageManagerController {
    if (!this.languageRuntime.isConfigured()) {
      throw new Error("LANGUAGE_RUNTIME_NOT_CONFIGURED");
    }
    if (!this.languagePackBackend) {
      throw new Error("LANGUAGE_PACK_STORE_NOT_CONFIGURED");
    }
    return new LanguageManagerController(
      this.languageRuntime,
      registry,
      new PersistentLanguagePackStore(this.languagePackBackend),
    );
  }


  setPreferredLanguage(languageTag: string) {
    return this.languageRuntime.setPreferredLanguage(languageTag);
  }

  async persistPreferredLanguage(languageTag: string) {
    return this.languageRuntime.persistPreferredLanguage(languageTag);
  }

  async restorePreferredLanguage() {
    return this.languageRuntime.restorePreferredLanguage();
  }

  canUseLanguageOffline(languageTag: string): boolean {
    return this.languageRuntime.canRunOffline(languageTag);
  }

  async downloadLanguagePack(
    manifest: LanguagePackDownloadManifest,
    transport: LanguagePackDownloadTransport,
    verifier: LanguagePackVerifier,
    onProgress?: (progress: LanguagePackDownloadProgress) => void,
  ): Promise<void> {
    await this.languageRuntime.downloadAndCacheLanguagePack(
      manifest,
      transport,
      verifier,
      onProgress,
    );
  }

}
