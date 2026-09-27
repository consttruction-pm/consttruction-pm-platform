# Stage 86 — Language Pack Integrity Verification

## Scope
Verify a downloaded language-pack artifact before activation. Checksum verification is concrete; signature verification is an injected trust-boundary adapter.

## Security boundary
- SHA-256 is computed from the exact artifact bytes.
- A checksum mismatch blocks signature acceptance.
- Signature verification does not embed private keys or signing policy in the client.
- Activation, rollback, key rotation and revocation remain separate lifecycle stages.

## Acceptance
- Valid checksum accepted.
- Tampered artifact rejected.
- Missing/invalid signature rejected.
- Signature verifier is injectable and deterministic in tests.
