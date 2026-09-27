import type {LanguagePackManifest} from "./language-pack-manifest.ts";
import {verifyLanguagePackIntegrity,type LanguagePackSignatureVerifier} from "./language-pack-integrity.ts";
import {validateLanguagePackResources,type LanguagePackResource,type ValidatedLanguagePackResources} from "./language-pack-resource-validation.ts";

export type ActivatedLanguagePack={
 manifest:LanguagePackManifest;
 resources:ValidatedLanguagePackResources;
};

export class AtomicLanguagePackStore{
 protected active:ActivatedLanguagePack|null=null;

 getActive():ActivatedLanguagePack|null{return this.active;}

 activate(artifact:Uint8Array,manifest:LanguagePackManifest,resources:readonly LanguagePackResource[],verifySignature:LanguagePackSignatureVerifier):ActivatedLanguagePack{
  verifyLanguagePackIntegrity(artifact,manifest,verifySignature);
  const validatedResources=validateLanguagePackResources(manifest,resources);
  const frozenManifest:LanguagePackManifest=Object.freeze({\n   ...manifest,\n   app_compatibility:Object.freeze({...manifest.app_compatibility}),\n   artifact:Object.freeze({...manifest.artifact}),\n   resources:Object.freeze({...manifest.resources}),\n   integrity:Object.freeze({...manifest.integrity}),\n   capabilities:Object.freeze({...manifest.capabilities}),\n  });\n  const candidate:ActivatedLanguagePack=Object.freeze({manifest:frozenManifest,resources:validatedResources});
  this.active=candidate;
  return candidate;
 }
}
