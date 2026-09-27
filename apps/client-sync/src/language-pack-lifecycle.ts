import type {LanguagePackManifest} from "./language-pack-manifest.ts";
import type {LanguagePackResource} from "./language-pack-resource-validation.ts";
import type {LanguagePackSignatureVerifier} from "./language-pack-integrity.ts";
import {UpdateableLanguagePackStore,type LanguagePackActivationResult} from "./language-pack-update.ts";
import {OfflineLanguagePackStore} from "./language-pack-offline.ts";
import type {ActivatedLanguagePack} from "./language-pack-activation.ts";

export class LanguagePackLifecycle{
 private readonly updates=new UpdateableLanguagePackStore();
 private readonly offline=new OfflineLanguagePackStore();

 activateInitial(
  artifact:Uint8Array,manifest:LanguagePackManifest,resources:readonly LanguagePackResource[],
  verifySignature:LanguagePackSignatureVerifier,
 ):ActivatedLanguagePack{
  const active=this.updates.activate(artifact,manifest,resources,verifySignature);
  this.offline.cacheActivatedPack(active);
  return active;
 }

 update(
  artifact:Uint8Array,manifest:LanguagePackManifest,resources:readonly LanguagePackResource[],
  verifySignature:LanguagePackSignatureVerifier,
 ):LanguagePackActivationResult{
  const result=this.updates.update(artifact,manifest,resources,verifySignature);
  this.offline.cacheActivatedPack(result.active);
  return result;
 }

 rollback():ActivatedLanguagePack{
  const restored=this.updates.rollback();
  this.offline.cacheActivatedPack(restored);
  return restored;
 }

 activateOffline():ActivatedLanguagePack{return this.offline.activateOffline();}
 getActive():ActivatedLanguagePack|null{return this.updates.getActive();}
}
