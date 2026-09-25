# Global Translation Key Convention v1.0

Translation keys are language-neutral stable identifiers shared across Web, Desktop, Mobile and AI/Smart Guide presentation layers.

## Rules
1. Keys identify product concepts, not translated sentences.
2. Keys use stable dot-separated namespaces.
3. No client may rename a shared key independently.
4. Structured IDs, enum values, activity/resource codes and calculation fields are never translation keys.
5. Every released key needs a default-language value and translation coverage metadata.
6. Plurals, gender, variables and rich text use structured message metadata rather than string concatenation.
7. RTL/LTR is a language property, not embedded in text.
8. Terminology-sensitive P6/project-controls terms must map to glossary identifiers.
9. Deleted keys require a deprecation window before removal from a released pack.
10. CI must detect missing, orphaned and duplicate keys across clients.

## Example namespaces
`nav.*` navigation
`activity.*` activity/WBS concepts
`schedule.*` scheduling concepts
`progress.*` progress/EVM concepts
`resource.*` resources
`cost.*` cost
`document.*` documents
`contract.*` contracts/claims
`field.*` field workflows
`ai.*` AI/Smart Guide
`validation.*` validation/errors
`report.*` reports/print
`system.*` system/security
`glossary.*` controlled terminology