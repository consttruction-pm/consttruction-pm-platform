import type { LanguageManagerController } from "../../client-sync/src/language-manager-controller.ts";
import type { LanguagePackDownloadManifest } from "../../client-sync/src/language-pack-download.ts";
import type { LanguagePackDownloadTransport, LanguagePackVerifier } from "../../client-sync/src/language-pack-download.ts";
import type { LanguagePackCatalog } from "../../client-sync/src/language-pack-catalog.ts";
import { WebLanguageManagerView, type LanguageManagerWebOptions } from "./language-manager-view.ts";

export type MountLanguageManagerOptions = Omit<
  LanguageManagerWebOptions,
  "root"
> & {
  root: HTMLElement;
};

export async function mountLanguageManager(
  options: MountLanguageManagerOptions,
): Promise<WebLanguageManagerView> {
  const view = new WebLanguageManagerView(options);
  await view.mount();
  return view;
}
