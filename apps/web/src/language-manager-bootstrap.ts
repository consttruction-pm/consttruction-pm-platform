import type { LanguageManagerController } from "../../client-sync/src/language-manager-controller.js";
import { WebLanguageManagerView, type LanguageManagerWebOptions } from "./language-manager-view.js";

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
