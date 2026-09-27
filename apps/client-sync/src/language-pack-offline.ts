import type {LanguagePackManifest} from "./language-pack-manifest.ts";
import type {LanguagePackResource} from "./language-pack-resource-validation.ts";
import type {LanguagePackSignatureVerifier} from "./language-pack-integrity.ts";
import {AtomicLanguagePackStore,isActivatedLanguagePack,type ActivatedLanguagePack} from "./language-pack-activation.ts";

export type CachedLanguagePack={artifact:Uint8Array;manifest:LanguagePackManifest;resources:readonly LanguagePackResource[]};

export class OfflineLanguagePackStore{
 private cached:ActivatedLanguagePack|null=null;
 private readonly verifierStore=new AtomicLanguagePackStore();

 cacheVerifiedPack(
  pack:CachedLanguagePack,
  verifySignature:LanguagePackSignatureVerifier,
 ):ActivatedLanguagePack{
  const active=this.verifierStore.activate(pack.artifact,pack.manifest,pack.resources,verifySignature);
  return this.cacheActivatedPack(active);
 }

 cacheActivatedPack(pack:ActivatedLanguagePack):ActivatedLanguagePack{
  if(!isActivatedLanguagePack(pack)) throw new Error("LANGUAGE_PACK_ACTIVATION_PROVENANCE_INVALID");
  this.cached=pack;
  return this.cached;
 }

 activateOffline():ActivatedLanguagePack{
  if(!this.cached) throw new Error("LANGUAGE_PACK_OFFLINE_CACHE_UNAVAILABLE");
  return this.cached;
 }

 hasVerifiedCache(packageId:string,version:string):boolean{
  return this.cached?.manifest.package_id===packageId&&this.cached.manifest.version===version;
 }
}
