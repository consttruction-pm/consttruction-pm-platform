export type LanguagePackCatalogItem={packageId:string;languageTag:string;version:string;minAppVersion:string;maxAppVersion:string|null;compressedSizeBytes:number;downloadUri:string;checksum:string;signature:string;capabilities:{ui:boolean;help:boolean;aiText:boolean;voiceInput:boolean;voiceOutput:boolean;offlineAi:boolean}};
export type LanguagePackCatalog={schemaVersion:string;generatedAt:string;defaultLanguage:string;items:readonly LanguagePackCatalogItem[]};

export function selectCompatiblePack(catalog:LanguagePackCatalog,languageTag:string,appVersion:string):LanguagePackCatalogItem|null {
 const candidates=catalog.items.filter(i=>i.languageTag===languageTag && compareVersions(appVersion,i.minAppVersion)>=0 && (i.maxAppVersion===null||compareVersions(appVersion,i.maxAppVersion)<=0));
 return [...candidates].sort((a,b)=>compareVersions(b.version,a.version))[0]??null;
}
function compareVersions(a:string,b:string):number {
 const av=parse(a),bv=parse(b);
 for(let i=0;i<Math.max(av.length,bv.length);i++){const x=av[i]??0,y=bv[i]??0;if(x!==y)return x-y;} return 0;
}
function parse(v:string):number[]{const core=v.trim().split("+")[0].split("-")[0];if(!/^\\d+(\\.\\d+)*$/.test(core))throw new Error("INVALID_VERSION");return core.split(".").map(Number);}
export function isNewerPackAvailable(installedVersion:string|null,candidateVersion:string|null):boolean {
 return candidateVersion!==null && (installedVersion===null||compareVersions(candidateVersion,installedVersion)>0);
}