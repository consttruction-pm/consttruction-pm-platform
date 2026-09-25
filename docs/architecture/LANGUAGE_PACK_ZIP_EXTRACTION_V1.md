# Language Pack ZIP Extraction Specification v1

## Purpose

Provide one deterministic ZIP resource-extraction implementation for language packs so Web, Desktop and Mobile do not create incompatible archive semantics.

## Supported format

The current concrete engine supports standard ZIP archives with:
- Single-disk archives.
- Stored entries (method 0).
- Deflate entries (method 8), decoded through a platform adapter.
- UTF-8 resource paths.
- Standard ZIP sizes within 32-bit fields.

ZIP64, encrypted entries, unsupported compression methods and invalid archive/path structures are rejected explicitly.

## Integrity checks

A resource is returned only after:
1. The requested resource path passes traversal/absolute-path validation.
2. The central directory and local-file header are structurally valid.
3. The compressed data range is inside the artifact.
4. The decompressed size matches the central-directory size.
5. CRC-32 matches the central-directory value.
6. Resource text is valid UTF-8.

This layer validates archive/resource integrity. Package-level SHA-256 and signature verification remain the responsibility of the existing Language Pack download/cache verification layer.

## Platform adapters

- Shared: ZIP parser, resource lookup, CRC-32, UTF-8 decoding and security checks.
- Web: `WebRawDeflateDecoder` uses the platform Compression Streams API.
- Desktop: `NodeRawDeflateDecoder` uses Node's `inflateRaw`.
- Mobile: the Shared `RawDeflateDecoder` contract is exposed to the native shell so Kotlin/Swift/React-Native/Tauri host code can supply its platform-approved decoder.

## Explicit non-goals

This implementation does not claim support for Zstandard or TAR.ZST artifacts even though the manifest contract can describe those formats. Those formats require separate, explicitly tested adapters.
