import type {LanguagePackManifest} from "./language-pack-manifest.ts";
import type {LanguagePackResource} from "./language-pack-resource-validation.ts";
import type {LanguagePackSignatureVerifier} from "./language-pack-integrity.ts";
import {LanguagePackLifecycle} from "./language-pack-lifecycle.ts";
import type {LanguagePackActivationResult} from "./language-pack-update.ts";
import type {ActivatedLanguagePack} from "./language-pack-activation.ts";

export class LanguagePackClientRuntime{
 private readonly lifecycle=new LanguagePackLifecycle();

 activateInitial(
  artifact:Uint8Array,
  manifest:LanguagePackManifest,
  resources:readonly LanguagePackResource[],
  verifySignature:LanguagePackSignatureVerifier,
 ):ActivatedLanguagePack{
  return this.lifecycle.activateInitial(artifact,manifest,resources,verifySignature);
 }

 update(
  artifact:Uint8Array,
  manifest:LanguagePackManifest,
  resources:readonly LanguagePackResource[],
  verifySignature:LanguagePackSignatureVerifier,
 ):LanguagePackActivationResult{
  return this.lifecycle.update(artifact,manifest,resources,verifySignature);
 }

 rollback():ActivatedLanguagePack{
  return this.lifecycle.rollback();
 }

 activateOffline():ActivatedLanguagePack{
  return this.lifecycle.activateOffline();
 }

 getActive():ActivatedLanguagePack|null{
  return this.lifecycle.getActive();
 }
}
