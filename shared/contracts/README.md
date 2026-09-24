# Shared API Contracts v1

These schemas are authoritative for both Web and Desktop clients.

- Decimal-like financial and unit values cross the API as canonical decimal strings, never floating-point JSON numbers.
- Dates use ISO-8601 representation.
- IDs are strings.
- Nullable fields are explicitly nullable.
- Schema versions are part of the contract identity.
- API serialization must invoke Domain methods for calculated values; it must never serialize a bound method/reference.
- Web and Desktop consume the same contract.
