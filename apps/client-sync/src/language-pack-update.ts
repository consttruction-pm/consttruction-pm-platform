import type {LanguagePackManifest} from "./language-pack-manifest.ts";
import type {LanguagePackResource, ValidatedLanguagePackResources} from "./language-pack-resource-validation.ts";
import {AtomicLanguagePackStore, type ActivatedLanguagePack} from "./language-pack-activation.ts";
import type {LanguagePackSignatureVerifier} from "./language-pack-integrity.ts";

export type LanguagePackActivationResult={active:ActivatedLanguagePack;updated:boolean};

export class UpdateableLanguagePackStore extends AtomicLanguagePackStore{
 private previous:ActivatedLanguagePack|null=null;

 override activate(
  artifact:Uint8Array,
  manifest:LanguagePackManifest,
  resources:readonly LanguagePackResource[],
  verifySignature:LanguagePackSignatureVerifier,
 ):ActivatedLanguagePack{
  const current=this.getActive();
  const next=super.activate(artifact,manifest,resources,verifySignature);
  this.previous=current;
  return next;
 }

 update(
  artifact:Uint8Array,
  manifest:LanguagePackManifest,
  resources:readonly LanguagePackResource[],
  verifySignature:LanguagePackSignatureVerifier,
 ):LanguagePackActivationResult{
  const current=this.getActive();
  const active=this.activate(artifact,manifest,resources,verifySignature);
  return {active,updated:current?.manifest.version!==active.manifest.version||current?.manifest.package_id!==active.manifest.package_id};
 }

 rollback():ActivatedLanguagePack{
  if(!this.previous) throw new Error("LANGUAGE_PACK_ROLLBACK_UNAVAILABLE");
  const current=this.getActive();
  const restored=this.previous;
  this.previous=current;
  // Publish only a previously validated immutable snapshot.
  (this as {active?:ActivatedLanguagePack}).active=restored;
  return restored;
 }
}
