import type {LanguagePackManifest} from "./language-pack-manifest.ts";

export type LanguagePackResource={path:string;bytes:Uint8Array};
export interface ValidatedLanguagePackResources extends ReadonlyMap<string,Uint8Array>{}

const declaredResourcePaths=(manifest:LanguagePackManifest):string[]=>[
 manifest.resources.translation,manifest.resources.glossary,manifest.resources.help,manifest.resources.reports,
 manifest.resources.voice_input,manifest.resources.voice_output,manifest.resources.offline_ai_model,
].filter((path):path is string=>path!==null);

class ImmutableLanguagePackResourceMap implements ValidatedLanguagePackResources{
 private readonly store:Map<string,Uint8Array>;
 constructor(values:ReadonlyMap<string,Uint8Array>){this.store=new Map(values);}
 get size():number{return this.store.size;}
 get(path:string):Uint8Array|undefined{
  const value=this.store.get(path);
  return value?new Uint8Array(value):undefined;
 }
 has(path:string):boolean{return this.store.has(path);}
 *entries():IterableIterator<[string,Uint8Array]>{
  for(const [path,bytes] of this.store) yield [path,new Uint8Array(bytes)];
 }
 keys():IterableIterator<string>{return this.store.keys();}
 *values():IterableIterator<Uint8Array>{
  for(const bytes of this.store.values()) yield new Uint8Array(bytes);
 }
 [Symbol.iterator]():IterableIterator<[string,Uint8Array]>{return this.entries();}
 forEach(callbackfn:(value:Uint8Array,key:string,map:ReadonlyMap<string,Uint8Array>)=>void,thisArg?:unknown):void{
  for(const [key,value] of this.store) callbackfn.call(thisArg,new Uint8Array(value),key,this);
 }
}

export function validateLanguagePackResourcePath(path:string):void{
 if(!path || path.includes("\0") || path.startsWith("/") || path.startsWith("\\") || path.includes("\\")){
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
  if(!declaredSet.has(resource.path)) throw new Error("UNDECLARED_LANGUAGE_PACK_RESOURCE");
  if(!(resource.bytes instanceof Uint8Array)) throw new Error("INVALID_LANGUAGE_PACK_RESOURCE");
  if(result.has(resource.path)) throw new Error("DUPLICATE_LANGUAGE_PACK_RESOURCE");
  result.set(resource.path,new Uint8Array(resource.bytes));
 }
 for(const path of declaredSet){
  if(!result.has(path)) throw new Error("LANGUAGE_PACK_RESOURCE_MISSING");
 }
 return new ImmutableLanguagePackResourceMap(result);
}
