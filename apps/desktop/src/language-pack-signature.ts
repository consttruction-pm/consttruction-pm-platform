import { webcrypto } from "node:crypto";

import {
  RegistryBackedLanguagePackSignatureVerifier,
  LanguagePackSigningKeyRegistry,
  type LanguagePackSignatureCrypto,
  type LanguagePackSigningKey,
} from "../../client-sync/src/language-pack-signature.js";

function copyBytes(bytes: Uint8Array): ArrayBuffer {
  const buffer = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(buffer).set(bytes);
  return buffer;
}

export class NodeLanguagePackSignatureCrypto implements LanguagePackSignatureCrypto {
  async digestSha256(data: Uint8Array): Promise<Uint8Array> {
    return new Uint8Array(
      await webcrypto.subtle.digest("SHA-256", copyBytes(data)),
    );
  }

  async verifyEd25519(
    publicKey: Uint8Array,
    signature: Uint8Array,
    message: Uint8Array,
  ): Promise<boolean> {
    const key = await webcrypto.subtle.importKey(
      "raw",
      copyBytes(publicKey),
      { name: "Ed25519" },
      false,
      ["verify"],
    );
    return webcrypto.subtle.verify(
      { name: "Ed25519" },
      key,
      copyBytes(signature),
      copyBytes(message),
    );
  }
}

export class NodeLanguagePackSignatureVerifier
  extends RegistryBackedLanguagePackSignatureVerifier
{
  constructor(
    keys: readonly LanguagePackSigningKey[],
    clock?: () => Date,
  ) {
    super(
      new LanguagePackSigningKeyRegistry(keys),
      new NodeLanguagePackSignatureCrypto(),
      clock,
    );
  }
}
