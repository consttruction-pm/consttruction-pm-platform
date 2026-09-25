# Language Manager UI QA Checklist v1.0

## Purpose
Validate that Web/Desktop/Mobile language management remains multilingual, offline-capable, capability-aware, and independent from project truth.

## Core scenarios
- Load registry with LTR and RTL languages.
- Display human-readable names using the active UI locale.
- Switch between installed verified languages without network.
- Download a compatible pack and show progress.
- Reject checksum/signature failures.
- Show Update only when catalog version is newer.
- Remove an installed inactive pack.
- Reject removal of the active pack.
- Activate a verified cached pack after application restart.
- Keep the previous active pack when replacement resource loading fails.
- Reject absolute and parent-traversal resource paths.
- Preserve project identifiers, calculations, codes and structured data when UI language changes.

## AI/Voice scenarios
- Preferred language changes AI model selection.
- Local AI is selected only when verified compatible model + device capability + offline policy allow it.
- Voice input and output are independently gated.
- Missing local model falls back to online execution when policy permits.
- UI never claims offline capability from storage alone; registry/model capability metadata is authoritative.

## Accessibility
- Root lang matches the active language tag.
- Root dir matches the active registry direction.
- Table has an accessible name.
- Table headers use column scope.
- Download progress has a localized accessible label.
- Keyboard activation works for all actions.
- Error state is exposed through a status region.
- No color-only status meaning is required.

## Certification evidence
A release claim requires:
1. Executed client typecheck evidence for all four clients.
2. Executed shared runtime tests.
3. Cross-client language switching regression.
4. Offline restart/activation regression.
5. Security/resource-path regression.
6. Accessibility regression evidence.

CI failures with zero executed steps are infrastructure evidence only and must not be converted into product-test pass/fail claims.