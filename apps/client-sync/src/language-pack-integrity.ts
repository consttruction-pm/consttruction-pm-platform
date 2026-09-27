import {createHash} from "node:crypto";
import type {LanguagePackManifest} from "./language-pack-manifest.ts";

export type LanguagePackSignatureVerifier=(payload:Uint8Array,signature:string,keyId:string|null)=>boolean;

const SIGNING_PAYLOAD_VERSION="language-pack-signing-payload.v1";

export function canonicalizeLanguagePackSigningPayload(manifest:LanguagePackManifest):Uint8Array {
 const payload={
  schema_version:SIGNING_PAYLOAD_VERSION,
  package_id:manifest.package_id,
  language_tag:manifest.language_tag,
  version:manifest.version,
  app_compatibility:{
   min_version:manifest.app_compatibility.min_version,
   max_version:manifest.app_compatibility.max_version,
  },
  artifact:{
   format:manifest.artifact.format,
   compressed_size_bytes:manifest.artifact.compressed_size_bytes,
   download_uri:manifest.artifact.download_uri,
   delta_from:manifest.artifact.delta_from,
  },
  resources:{
   translation:manifest.resources.translation,
   glossary:manifest.resources.glossary,
   help:manifest.resources.help,
   reports:manifest.resources.reports,
   voice_input:manifest.resources.voice_input,
   voice_output:manifest.resources.voice_output,
   offline_ai_model:manifest.resources.offline_ai_model,
  },
  integrity:{
   checksum:manifest.integrity.checksum.toLowerCase(),
   signing_key_id:manifest.integrity.signing_key_id,
  },
  capabilities:{
   ui:manifest.capabilities.ui,
   help:manifest.capabilities.help,
   ai_text:manifest.capabilities.ai_text,
   voice_input:manifest.capabilities.voice_input,
   voice_output:manifest.capabilities.voice_output,
   offline_ai:manifest.capabilities.offline_ai,
  },
 };
 return new TextEncoder().encode(JSON.stringify(payload));
}

export function verifyLanguagePackChecksum(artifact:Uint8Array,manifest:LanguagePackManifest):boolean {
 const expected=manifest.integrity.checksum;
 if(!/^sha256:[0-9a-fA-F]{64}$/.test(expected)) throw new Error("INVALID_LANGUAGE_PACK_CHECKSUM");
 const actual="sha256:"+createHash("sha256").update(artifact).digest("hex");
 return actual.toLowerCase()===expected.toLowerCase();
}

export function verifyLanguagePackIntegrity(artifact:Uint8Array,manifest:LanguagePackManifest,verifySignature:LanguagePackSignatureVerifier):void {
 if(!verifyLanguagePackChecksum(artifact,manifest)) throw new Error("LANGUAGE_PACK_CHECKSUM_MISMATCH");
 if(!manifest.integrity.signature) throw new Error("LANGUAGE_PACK_SIGNATURE_MISSING");
 const signingPayload=canonicalizeLanguagePackSigningPayload(manifest);
 if(!verifySignature(signingPayload,manifest.integrity.signature,manifest.integrity.signing_key_id)) throw new Error("LANGUAGE_PACK_SIGNATURE_INVALID");
}
