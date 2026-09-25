# Language Pack Signature Envelope v1

The production language-pack verifier accepts signatures in this exact form:

`ed25519.v1:<key-id>:<base64url-signature>`

The signature is over the canonical UTF-8 message generated from package identity, language tag, version, app compatibility, compressed artifact size, SHA-256 checksum and all Translation/Glossary/Help/Reports resource paths.

Security lifecycle:
- **active** keys can verify within their validity window.
- **retired** keys can continue to verify existing packs while their validity window remains open.
- **revoked** keys are immediately rejected.
- Multiple valid keys may coexist during rotation.
- Private signing keys are never stored or executed by Web/Desktop/Mobile clients.

The key registry is a trust input and must itself be delivered through an authenticated/trusted release mechanism. This verifier does not claim to establish trust in an untrusted key registry.

Web uses the Web Crypto API Ed25519 verification path; Node/Desktop uses Node Web Crypto. Current platform documentation confirms Ed25519 support in WebCrypto and Node WebCrypto. citeturn375637search0turn375637search2turn375637search3
