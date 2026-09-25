import type { LanguagePackResourceReader } from "./language-resource-loader.js";

export interface RawDeflateDecoder {
  decode(compressed: Uint8Array): Promise<Uint8Array>;
}

type ZipEntry = {
  path: string;
  flags: number;
  method: number;
  compressedSize: number;
  uncompressedSize: number;
  crc32: number;
  localHeaderOffset: number;
};

const EOCD_SIGNATURE = 0x06054b50;
const CENTRAL_SIGNATURE = 0x02014b50;
const LOCAL_SIGNATURE = 0x04034b50;
const MAX_EOCD_SEARCH = 22 + 65535;
const UTF8_FLAG = 0x0800;
const ENCRYPTED_FLAG = 0x0001;

export class ZipLanguagePackExtractor implements LanguagePackResourceReader {
  constructor(private readonly deflateDecoder: RawDeflateDecoder) {}

  async readText(artifact: Uint8Array, resourcePath: string): Promise<string> {
    validateResourcePath(resourcePath);
    const entry = findEntry(artifact, resourcePath);
    if (!entry) {
      throw new Error("LANGUAGE_RESOURCE_NOT_FOUND");
    }
    if ((entry.flags & ENCRYPTED_FLAG) !== 0) {
      throw new Error("UNSUPPORTED_ENCRYPTED_LANGUAGE_PACK");
    }

    const compressed = readLocalFileData(artifact, entry);
    let content: Uint8Array;

    if (entry.method === 0) {
      content = compressed;
    } else if (entry.method === 8) {
      content = await this.deflateDecoder.decode(compressed);
    } else {
      throw new Error("UNSUPPORTED_LANGUAGE_PACK_COMPRESSION");
    }

    if (content.byteLength !== entry.uncompressedSize) {
      throw new Error("LANGUAGE_RESOURCE_SIZE_MISMATCH");
    }
    if (crc32(content) !== entry.crc32) {
      throw new Error("LANGUAGE_RESOURCE_CRC_MISMATCH");
    }

    try {
      return new TextDecoder("utf-8", { fatal: true }).decode(content);
    } catch {
      throw new Error("INVALID_LANGUAGE_RESOURCE_ENCODING");
    }
  }
}

function findEntry(artifact: Uint8Array, resourcePath: string): ZipEntry | null {
  const directory = parseCentralDirectory(artifact);
  return directory.find((entry) => entry.path === resourcePath) ?? null;
}

function parseCentralDirectory(artifact: Uint8Array): ZipEntry[] {
  const eocdOffset = findEndOfCentralDirectory(artifact);
  if (eocdOffset < 0) {
    throw new Error("INVALID_LANGUAGE_PACK_ZIP");
  }

  const view = new DataView(
    artifact.buffer,
    artifact.byteOffset,
    artifact.byteLength,
  );
  const entryCount = view.getUint16(eocdOffset + 10, true);
  const directorySize = view.getUint32(eocdOffset + 12, true);
  const directoryOffset = view.getUint32(eocdOffset + 16, true);

  if (
    entryCount === 0xffff ||
    directorySize === 0xffffffff ||
    directoryOffset === 0xffffffff
  ) {
    throw new Error("UNSUPPORTED_LANGUAGE_PACK_ZIP64");
  }

  if (
    directoryOffset < 0 ||
    directorySize < 0 ||
    directoryOffset + directorySize > artifact.byteLength
  ) {
    throw new Error("INVALID_LANGUAGE_PACK_ZIP_DIRECTORY");
  }

  const entries: ZipEntry[] = [];
  let offset = directoryOffset;

  for (let index = 0; index < entryCount; index += 1) {
    if (
      offset + 46 > artifact.byteLength ||
      view.getUint32(offset, true) !== CENTRAL_SIGNATURE
    ) {
      throw new Error("INVALID_LANGUAGE_PACK_ZIP_ENTRY");
    }

    const flags = view.getUint16(offset + 8, true);
    const method = view.getUint16(offset + 10, true);
    const crc = view.getUint32(offset + 16, true);
    const compressedSize = view.getUint32(offset + 20, true);
    const uncompressedSize = view.getUint32(offset + 24, true);
    const nameLength = view.getUint16(offset + 28, true);
    const extraLength = view.getUint16(offset + 30, true);
    const commentLength = view.getUint16(offset + 32, true);
    const diskStart = view.getUint16(offset + 34, true);
    const localHeaderOffset = view.getUint32(offset + 42, true);

    if (
      diskStart !== 0 ||
      compressedSize === 0xffffffff ||
      uncompressedSize === 0xffffffff ||
      localHeaderOffset === 0xffffffff
    ) {
      throw new Error("UNSUPPORTED_LANGUAGE_PACK_ZIP64");
    }

    const nameStart = offset + 46;
    const recordEnd = nameStart + nameLength + extraLength + commentLength;
    if (recordEnd > artifact.byteLength || recordEnd > directoryOffset + directorySize) {
      throw new Error("INVALID_LANGUAGE_PACK_ZIP_ENTRY");
    }

    const nameBytes = artifact.subarray(nameStart, nameStart + nameLength);
    let path: string;
    try {
      path = new TextDecoder("utf-8", {
        fatal: (flags & UTF8_FLAG) !== 0,
      }).decode(nameBytes);
    } catch {
      throw new Error("UNSUPPORTED_LANGUAGE_PACK_FILENAME_ENCODING");
    }
    validateArchiveEntryPath(path);

    entries.push({
      path,
      flags,
      method,
      compressedSize,
      uncompressedSize,
      crc32: crc,
      localHeaderOffset,
    });
    offset = recordEnd;
  }

  return entries;
}

function readLocalFileData(
  artifact: Uint8Array,
  entry: ZipEntry,
): Uint8Array {
  const view = new DataView(
    artifact.buffer,
    artifact.byteOffset,
    artifact.byteLength,
  );
  const offset = entry.localHeaderOffset;
  if (offset + 30 > artifact.byteLength || view.getUint32(offset, true) !== LOCAL_SIGNATURE) {
    throw new Error("INVALID_LANGUAGE_PACK_LOCAL_HEADER");
  }

  const nameLength = view.getUint16(offset + 26, true);
  const extraLength = view.getUint16(offset + 28, true);
  const dataStart = offset + 30 + nameLength + extraLength;
  const dataEnd = dataStart + entry.compressedSize;
  if (dataStart < 0 || dataEnd > artifact.byteLength) {
    throw new Error("INVALID_LANGUAGE_PACK_DATA_RANGE");
  }

  return artifact.slice(dataStart, dataEnd);
}

function findEndOfCentralDirectory(artifact: Uint8Array): number {
  const start = Math.max(0, artifact.byteLength - MAX_EOCD_SEARCH);
  for (let offset = artifact.byteLength - 22; offset >= start; offset -= 1) {
    if (
      offset >= 0 &&
      offset + 4 <= artifact.byteLength &&
      new DataView(
        artifact.buffer,
        artifact.byteOffset,
        artifact.byteLength,
      ).getUint32(offset, true) === EOCD_SIGNATURE
    ) {
      return offset;
    }
  }
  return -1;
}

function validateResourcePath(resourcePath: string): void {
  if (
    !resourcePath ||
    resourcePath.startsWith("/") ||
    resourcePath.startsWith("\\")
  ) {
    throw new Error("INVALID_LANGUAGE_RESOURCE_PATH");
  }
  const normalized = resourcePath.replaceAll("\\", "/");
  if (normalized.split("/").some((segment) => segment === "..")) {
    throw new Error("INVALID_LANGUAGE_RESOURCE_PATH");
  }
}

function validateArchiveEntryPath(path: string): void {
  if (
    !path ||
    path.includes("\\") ||
    path.startsWith("/") ||
    path.split("/").some((segment) => segment === "..")
  ) {
    throw new Error("INVALID_LANGUAGE_PACK_ENTRY_PATH");
  }
}

const CRC_TABLE = createCrcTable();

function crc32(bytes: Uint8Array): number {
  let value = 0xffffffff;
  for (const byte of bytes) {
    value = (value >>> 8) ^ CRC_TABLE[(value ^ byte) & 0xff]!;
  }
  return (value ^ 0xffffffff) >>> 0;
}

function createCrcTable(): readonly number[] {
  const table: number[] = [];
  for (let byte = 0; byte < 256; byte += 1) {
    let value = byte;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value & 1) !== 0 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
    }
    table.push(value >>> 0);
  }
  return table;
}
