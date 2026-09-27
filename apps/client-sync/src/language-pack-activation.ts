import type {LanguagePackManifest} from "./language-pack-manifest.ts";
import {verifyLanguagePackIntegrity,type LanguagePackSignatureVerifier} from "./language-pack-integrity.ts";
import {validateLanguagePackResources,type LanguagePackResource,type ValidatedLanguagePackResources} from "./language-pack-resource-validation.ts";

const ACTIVATED_LANGUAGE_PACK_BRAND=Symbol("construction-pm.activated-language-pack");

type ActivatedLanguagePackBrand=typeof ACTIVATED_LANGUAGE_PACK_BRAND;

export type ActivatedLanguagePack={
 readonly manifest:LanguagePackManifest;
 readonly resources:ValidatedLanguagePackResources;
 readonly [ACTIVATED_LANGUAGE_PACK_BRAND]:ActivatedLanguagePackBrand;
};

export class AtomicLanguagePackStore{
 protected active:ActivatedLanguagePack|null=null;

 getActive():ActivatedLanguagePack|null{return this.active;}

 activate(artifact:Uint8Array,manifest:LanguagePackManifest,resources:readonly LanguagePackResource[],verifySignature:LanguagePackSignatureVerifier):ActivatedLanguagePack{
  verifyLanguagePackIntegrity(artifact,manifest,verifySignature);
  const validatedResources=validateLanguagePackResources(manifest,resources);
  const frozenManifest:LanguagePackManifest=Object.freeze({
   ...manifest,
   app_compatibility:Object.freeze({...manifest.app_compatibility}),
   artifact:Object.freeze({...manifest.artifact}),
   resources:Object.freeze({...manifest.resources}),
   integrity:Object.freeze({...manifest.integrity}),
   capabilities:Object.freeze({...manifest.capabilities}),
  });
  const candidate:ActivatedLanguagePack=Object.freeze({
   manifest:frozenManifest,
   resources:validatedResources,
   [ACTIVATED_LANGUAGE_PACK_BRAND]:ACTIVATED_LANGUAGE_PACK_BRAND,
  });
  this.active=candidate;
  return candidate;
 }
}
