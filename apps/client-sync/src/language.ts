export type LanguageDirection = "ltr" | "rtl";
export interface LanguageCapabilitySet { ui:boolean; help:boolean; aiText:boolean; voiceInput:boolean; voiceOutput:boolean; offlineAi:boolean; }
export interface InstalledLanguagePack { languageTag:string; version:string; active:boolean; verified:boolean; capabilities:LanguageCapabilitySet; }
export interface LanguageRegistryEntry { languageTag:string; direction:LanguageDirection; locale:string; fallbackChain:string[]; capabilities:LanguageCapabilitySet; }
export interface LanguagePreference { preferredLanguage:string; fallbackChain:string[]; installedPacks:InstalledLanguagePack[]; offlinePreferred:boolean; }
export interface ResolvedLanguage { languageTag:string; source:"preferred"|"fallback"|"default"; direction:LanguageDirection; locale:string; packVersion:string|null; offline:boolean; }

export class ClientLanguageManager {
 constructor(private readonly registry:readonly LanguageRegistryEntry[], private readonly defaultLanguage:string, private preference:LanguagePreference) {}
 getPreference():LanguagePreference { return {preferredLanguage:this.preference.preferredLanguage,fallbackChain:[...this.preference.fallbackChain],installedPacks:this.preference.installedPacks.map(p=>({...p})),offlinePreferred:this.preference.offlinePreferred}; }
 setPreferredLanguage(languageTag:string):ResolvedLanguage { this.preference={...this.preference,preferredLanguage:languageTag}; return this.resolve(); }
 syncInstalledPackState(installedPacks:readonly {languageTag:string;version:string;verified:boolean}[]):ResolvedLanguage {
  this.preference={...this.preference,installedPacks:installedPacks.map(pack=>{const entry=this.registry.find(i=>i.languageTag===pack.languageTag); if(!entry)return null; return {languageTag:pack.languageTag,version:pack.version,active:true,verified:pack.verified,capabilities:entry.capabilities};}).filter((p):p is InstalledLanguagePack=>p!==null)}; return this.resolve();
 }
 resolve():ResolvedLanguage {
  const candidates=[{tag:this.preference.preferredLanguage,source:"preferred" as const},...this.preference.fallbackChain.map(tag=>({tag,source:"fallback" as const})),{tag:this.defaultLanguage,source:"default" as const}];
  let firstRegistered:ResolvedLanguage|null=null;
  for(const candidate of candidates){const entry=this.registry.find(i=>i.languageTag===candidate.tag); if(!entry)continue; const pack=this.preference.installedPacks.find(i=>i.languageTag===candidate.tag&&i.verified); if(pack)return {languageTag:entry.languageTag,source:candidate.source,direction:entry.direction,locale:entry.locale,packVersion:pack.version,offline:true}; if(!firstRegistered)firstRegistered={languageTag:entry.languageTag,source:candidate.source,direction:entry.direction,locale:entry.locale,packVersion:null,offline:false};}
  if(firstRegistered)return firstRegistered; throw new Error("no registered language is available");
 }
 canRunOffline(languageTag:string):boolean { const entry=this.registry.find(i=>i.languageTag===languageTag); const pack=this.preference.installedPacks.find(i=>i.languageTag===languageTag&&i.verified); return Boolean(entry?.capabilities.ui&&pack?.capabilities.ui); }
}
