export interface LanguagePreferenceStore { load():Promise<string|null>; save(languageTag:string):Promise<void>; }
export class InMemoryLanguagePreferenceStore implements LanguagePreferenceStore { private value:string|null=null; async load(){return this.value;} async save(languageTag:string){if(!languageTag.trim())throw new Error("INVALID_LANGUAGE_PREFERENCE");this.value=languageTag.trim();} }
