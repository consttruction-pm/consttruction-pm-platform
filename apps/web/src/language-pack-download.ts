import type {
  LanguagePackDownloadManifest,
  LanguagePackDownloadTransport,
  LanguagePackVerifier,
} from "../../client-sync/src/language-pack-download.js";

export class FetchLanguagePackTransport implements LanguagePackDownloadTransport {
  async download(
    uri: string,
    onChunk?: (chunk: Uint8Array) => void,
  ): Promise<Uint8Array> {
    const response = await fetch(uri, { credentials: "omit" });
    if (!response.ok) {
      throw new Error("LANGUAGE_PACK_DOWNLOAD_HTTP_" + response.status);
    }

    if (!response.body) {
      const data = new Uint8Array(await response.arrayBuffer());
      onChunk?.(data);
      return data;
    }

    const reader = response.body.getReader();
    const chunks: Uint8Array[] = [];
    let total = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!value) continue;
      const chunk = new Uint8Array(value);
      chunks.push(chunk);
      total += chunk.byteLength;
      onChunk?.(chunk);
    }

    const result = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) {
      result.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return result;
  }
}

export type WebSignatureVerifier = (
  artifact: Uint8Array,
  manifest: LanguagePackDownloadManifest,
) => Promise<boolean>;

export class WebLanguagePackVerifier implements LanguagePackVerifier {
  constructor(private readonly signatureVerifier: WebSignatureVerifier) {}

  async verify(
    artifact: Uint8Array,
    manifest: LanguagePackDownloadManifest,
  ): Promise<boolean> {
    const digest = await crypto.subtle.digest("SHA-256", artifact);
    const actual = [...new Uint8Array(digest)]
      .map((value) => value.toString(16).padStart(2, "0"))
      .join("");

    if (!manifest.checksum.startsWith("sha256:")) {
      return false;
    }
    if (actual.toLowerCase() !== manifest.checksum.slice("sha256:".length).toLowerCase()) {
      return false;
    }

    return this.signatureVerifier(artifact, manifest);
  }
}
