import type {LanguagePackManifest} from "./language-pack-manifest.ts";

export type LanguagePackResource={path:string;bytes:Uint8Array};
export type ValidatedLanguagePackResources=ReadonlyMap<string,Uint8Array>;

const declaredResourcePaths=(manifest:LanguagePackManifest):string[]=>[
 manifest.resources.translation,manifest.resources.glossary,manifest.resources.help,manifest.resources.reports,
 manifest.resources.voice_input,manifest.resources.voice_output,manifest.resources.offline_ai_model,
].filter((path):path is string=>path!==null);

export function validateLanguagePackResourcePath(path:string):void{
 if(!path || path.includes("\0") || path.startsWith("/") || path.startsWith("\") || path.includes("\")){
  throw new Error("INVALID_LANGUAGE_PACK_RESOURCE_PATH");
 }
 const segments=path.split("/");
 if(segments.some(segment=>segment===""||segment==="."||segment==="..")){
  throw new Error("INVALID_LANGUAGE_PACK_RESOURCE_PATH");
 }
}

export function validateLanguagePackResources(manifest:LanguagePackManifest,resources:readonly LanguagePackResource[]):ValidatedLanguagePackResources{
 const declared=declaredResourcePaths(manifest);
 const declaredSet=new Set(declared);
 if(declaredSet.size!==declared.length) throw new Error("DUPLICATE_LANGUAGE_PACK_RESOURCE");
 const result=new Map<string,Uint8Array>();
 for(const resource of resources){
  validateLanguagePackResourcePath(resource.path);
  if(!(resource.bytes instanceof Uint8Array)) throw new Error("INVALID_LANGUAGE_PACK_RESOURCE");
  if(result.has(resource.path)) throw new Error("DUPLICATE_LANGUAGE_PACK_RESOURCE");
  result.set(resource.path,resource.bytes);
 }
 for(const path of declaredSet){
  if(!result.has(path)) throw new Error("LANGUAGE_PACK_RESOURCE_MISSING");
 }
 return result;
}
