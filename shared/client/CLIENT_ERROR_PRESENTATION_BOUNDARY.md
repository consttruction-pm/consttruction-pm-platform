# Client Error Presentation Boundary

## Purpose

Define the framework-neutral boundary for presenting the authoritative application_error_v1 contract in Web, Desktop, and Mobile clients.

## Stable fields

Clients receive four presentation fields:

- category — one of validation, context, conflict, authorization, not_found, persistence.
- code — stable machine-readable error identifier.
- retryable — authoritative retryability flag.
- message — authoritative fallback text; it is not a stable discriminator and may be localized or replaced by client presentation text.

The stable identity of an error is (category, code). retryable controls retry semantics but does not change that identity.

## Client rules

1. Branch on category and code, never on message text.
2. Preserve retryable as authoritative transport semantics.
3. Localize presentation text using category/code keys; do not require server messages to be Persian or English.
4. Keep the server message as fallback context when useful, without treating it as a contract key.
5. Do not invent new calculation, scheduling, calendar, financial, Progress, or revision semantics while presenting an error.
6. The same category/code/retryable input must produce equivalent semantic presentation state across Web/Desktop/Mobile.

## Scope

This boundary is presentation-only. It does not alter ApplicationError payloads, retry policy, conflict resolution, or authoritative business behavior.
