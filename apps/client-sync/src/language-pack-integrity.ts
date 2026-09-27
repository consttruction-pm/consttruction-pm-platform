import {createHash} from "node:crypto";
import type {LanguagePackManifest} from "./language-pack-manifest.ts";

export type LanguagePackSignatureVerifier=(payload:Uint8Array,signature:string,keyId:string|null)=>boolean;

export function verifyLanguagePackChecksum(artifact:Uint8Array,manifest:LanguagePackManifest):boolean {
 const expected=manifest.integrity.checksum;
 if(!/^sha256:[0-9a-fA-F]{64}$/.test(expected)) throw new Error("INVALID_LANGUAGE_PACK_CHECKSUM");
 const actual="sha256:"+createHash("sha256").update(artifact).digest("hex");
 return actual.toLowerCase()===expected.toLowerCase();
}

export function verifyLanguagePackIntegrity(artifact:Uint8Array,manifest:LanguagePackManifest,verifySignature:LanguagePackSignatureVerifier):void {
 if(!verifyLanguagePackChecksum(artifact,manifest)) throw new Error("LANGUAGE_PACK_CHECKSUM_MISMATCH");
 if(!manifest.integrity.signature) throw new Error("LANGUAGE_PACK_SIGNATURE_MISSING");
 if(!verifySignature(artifact,manifest.integrity.signature,manifest.integrity.signing_key_id)) throw new Error("LANGUAGE_PACK_SIGNATURE_INVALID");
}
