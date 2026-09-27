import type {LanguagePackManifest} from "./language-pack-manifest.ts";
import type {LanguagePackResource} from "./language-pack-resource-validation.ts";
import {verifyLanguagePackIntegrity,type LanguagePackSignatureVerifier} from "./language-pack-integrity.ts";
import {validateLanguagePackResources} from "./language-pack-resource-validation.ts";
import type {ActivatedLanguagePack} from "./language-pack-activation.ts";

export type CachedLanguagePack={artifact:Uint8Array;manifest:LanguagePackManifest;resources:readonly LanguagePackResource[]};

export class OfflineLanguagePackStore{
 private cached:ActivatedLanguagePack|null=null;

 cacheVerifiedPack(
  pack:CachedLanguagePack,
  verifySignature:LanguagePackSignatureVerifier,
 ):ActivatedLanguagePack{
  verifyLanguagePackIntegrity(pack.artifact,pack.manifest,verifySignature);
  const resources=validateLanguagePackResources(pack.manifest,pack.resources);
  return this.cacheActivatedPack({manifest:pack.manifest,resources});
 }

 activateOffline():ActivatedLanguagePack{
  if(!this.cached) throw new Error("LANGUAGE_PACK_OFFLINE_CACHE_UNAVAILABLE");
  return this.cached;
 }

 hasVerifiedCache(packageId:string,version:string):boolean{
  return this.cached?.manifest.package_id===packageId&&this.cached.manifest.version===version;
 }
}
