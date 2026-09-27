import type {LanguagePackManifest} from "./language-pack-manifest.ts";
import type {LanguagePackResource} from "./language-pack-resource-validation.ts";
import {AtomicLanguagePackStore, type ActivatedLanguagePack} from "./language-pack-activation.ts";
import type {LanguagePackSignatureVerifier} from "./language-pack-integrity.ts";

export type LanguagePackActivationResult={active:ActivatedLanguagePack;updated:boolean};

const MAX_ROLLBACK_HISTORY=5;

export class UpdateableLanguagePackStore extends AtomicLanguagePackStore{
 private readonly history:ActivatedLanguagePack[]=[];

 override activate(
  artifact:Uint8Array,
  manifest:LanguagePackManifest,
  resources:readonly LanguagePackResource[],
  verifySignature:LanguagePackSignatureVerifier,
 ):ActivatedLanguagePack{
  const current=this.getActive();
  const next=super.activate(artifact,manifest,resources,verifySignature);
  if(current){
   this.history.unshift(current);
   if(this.history.length>MAX_ROLLBACK_HISTORY) this.history.pop();
  }
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
  const restored=this.history.shift();
  if(!restored) throw new Error("LANGUAGE_PACK_ROLLBACK_UNAVAILABLE");
  // Publish only a previously validated immutable snapshot.
  this.active=restored;
  return restored;
 }
}
