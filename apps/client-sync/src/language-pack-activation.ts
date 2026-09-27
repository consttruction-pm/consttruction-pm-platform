import type {LanguagePackManifest} from "./language-pack-manifest.ts";
import {verifyLanguagePackIntegrity,type LanguagePackSignatureVerifier} from "./language-pack-integrity.ts";
import {validateLanguagePackResources,type LanguagePackResource,type ValidatedLanguagePackResources} from "./language-pack-resource-validation.ts";

export type ActivatedLanguagePack={
 manifest:LanguagePackManifest;
 resources:ValidatedLanguagePackResources;
};

export class AtomicLanguagePackStore{
 private active:ActivatedLanguagePack|null=null;

 getActive():ActivatedLanguagePack|null{return this.active;}

 activate(artifact:Uint8Array,manifest:LanguagePackManifest,resources:readonly LanguagePackResource[],verifySignature:LanguagePackSignatureVerifier):ActivatedLanguagePack{
  verifyLanguagePackIntegrity(artifact,manifest,verifySignature);
  const validatedResources=validateLanguagePackResources(manifest,resources);
  const candidate:ActivatedLanguagePack=Object.freeze({manifest,resources:validatedResources});
  this.active=candidate;
  return candidate;
 }
}
