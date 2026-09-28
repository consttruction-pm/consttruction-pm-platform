export type LanguageDirection = "ltr" | "rtl";
export type FontStyle = "normal" | "italic" | "oblique";
export interface LanguageTypography {
  fontFamily: string;
  fallbackFamilies: string[];
  fontStyle: FontStyle;
  fontWeight: number;
  lineHeight: string;
  letterSpacing: string;
  fontFeatureSettings: string;
  fontVariantLigatures: string;
  fontKerning: "auto" | "normal" | "none";
}
export interface LanguageCapabilitySet { ui:boolean; help:boolean; aiText:boolean; voiceInput:boolean; voiceOutput:boolean; offlineAi:boolean; }
export interface InstalledLanguagePack { languageTag:string; version:string; active:boolean; verified:boolean; capabilities:LanguageCapabilitySet; }
export interface LanguageRegistryEntry {
 languageTag:string;
 direction:LanguageDirection;
 locale:string;
 fallbackChain:string[];
 capabilities:LanguageCapabilitySet;
 typography:LanguageTypography;
}
export interface LanguagePreference { preferredLanguage:string; fallbackChain:string[]; installedPacks:InstalledLanguagePack[]; offlinePreferred:boolean; }
export interface ResolvedLanguage {
 languageTag:string;
 source:"preferred"|"fallback"|"default";
 direction:LanguageDirection;
 locale:string;
 packVersion:string|null;
 offline:boolean;
 typography:LanguageTypography;
}

export class ClientLanguageManager {
 private readonly registry:readonly LanguageRegistryEntry[];
 private readonly defaultLanguage:string;
 private preference:LanguagePreference;
 constructor(registry:readonly LanguageRegistryEntry[], defaultLanguage:string, preference:LanguagePreference) {
  this.registry=registry; this.defaultLanguage=defaultLanguage; this.preference=preference;
 }
 getPreference():LanguagePreference { return {preferredLanguage:this.preference.preferredLanguage,fallbackChain:[...this.preference.fallbackChain],installedPacks:this.preference.installedPacks.map(p=>({...p})),offlinePreferred:this.preference.offlinePreferred}; }
 setPreferredLanguage(languageTag:string):ResolvedLanguage { this.preference={...this.preference,preferredLanguage:languageTag}; return this.resolve(); }
 syncInstalledPackState(installedPacks:readonly {languageTag:string;version:string;verified:boolean}[]):ResolvedLanguage {
  this.preference={...this.preference,installedPacks:installedPacks.map(pack=>{const entry=this.registry.find(i=>i.languageTag===pack.languageTag); if(!entry)return null; return {languageTag:pack.languageTag,version:pack.version,active:true,verified:pack.verified,capabilities:entry.capabilities};}).filter((p):p is InstalledLanguagePack=>p!==null)}; return this.resolve();
 }
 resolve():ResolvedLanguage {
  const candidates=[{tag:this.preference.preferredLanguage,source:"preferred" as const},...this.preference.fallbackChain.map(tag=>({tag,source:"fallback" as const})),{tag:this.defaultLanguage,source:"default" as const}];
  for(const candidate of candidates){const entry=this.registry.find(i=>i.languageTag===candidate.tag); if(!entry)continue; const pack=this.preference.installedPacks.find(i=>i.languageTag===candidate.tag&&i.verified); if(pack)return {languageTag:entry.languageTag,source:candidate.source,direction:entry.direction,locale:entry.locale,packVersion:pack.version,offline:true,typography:{...entry.typography,fallbackFamilies:[...entry.typography.fallbackFamilies]}};}
  const defaultEntry=this.registry.find(i=>i.languageTag===this.defaultLanguage);
  if(defaultEntry)return {languageTag:defaultEntry.languageTag,source:"default",direction:defaultEntry.direction,locale:defaultEntry.locale,packVersion:null,offline:false,typography:{...defaultEntry.typography,fallbackFamilies:[...defaultEntry.typography.fallbackFamilies]}};
  throw new Error("no registered language is available");
 }
 canRunOffline(languageTag:string):boolean { const entry=this.registry.find(i=>i.languageTag===languageTag); const pack=this.preference.installedPacks.find(i=>i.languageTag===languageTag&&i.verified); return Boolean(entry?.capabilities.ui&&pack?.capabilities.ui); }
}
