export type LanguagePackManifest = {
  package_id:string; language_tag:string; version:string;
  app_compatibility:{min_version:string; max_version:string|null};
  artifact:{format:"zip"|"zstd"|"tar.zst"; compressed_size_bytes:number; download_uri:string; delta_from:string|null};
  resources:{translation:string; glossary:string; help:string; reports:string; voice_input:string|null; voice_output:string|null; offline_ai_model:string|null};
  integrity:{checksum:string; signature:string; signing_key_id:string|null};
  capabilities:{ui:boolean; help:boolean; ai_text:boolean; voice_input:boolean; voice_output:boolean; offline_ai:boolean};
};

export function validateLanguagePackManifest(value:unknown):LanguagePackManifest {
  if(!value || typeof value!=="object") throw new Error("INVALID_LANGUAGE_PACK_MANIFEST");
  const m=value as Record<string,unknown>;
  const required=["package_id","language_tag","version","app_compatibility","artifact","resources","integrity","capabilities"];
  if(required.some(k=>!(k in m))) throw new Error("INVALID_LANGUAGE_PACK_MANIFEST");
  const integrity=m.integrity as Record<string,unknown>;
  if(typeof integrity?.checksum!=="string" || !/^sha256:[0-9a-fA-F]{64}$/.test(integrity.checksum)) throw new Error("INVALID_LANGUAGE_PACK_CHECKSUM");
  return value as LanguagePackManifest;
}