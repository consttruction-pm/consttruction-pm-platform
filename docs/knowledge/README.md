# CUBI Engineering Knowledge Base

**Status:** Knowledge sources, curriculum and implementation contract registered. Production ingestion and retrieval are not yet implemented or verified.
**Authority:** Product Principle 13 — fully CUBI-owned, model-free Engineering Command Assistant.
**Implementation tracker:** [Issue #1540](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1540).

## Documents

- [Authoritative source register](CUBI_PROJECT_MANAGEMENT_KNOWLEDGE_SOURCE_REGISTER.md)
- [Machine-readable source registry](source-registry.json)
- [Step-by-step Project Management Academy curriculum](CUBI_PROJECT_MANAGEMENT_ACADEMY_CURRICULUM.md)
- [Model-free knowledge-base architecture](../architecture/CUBI_MODEL_FREE_KNOWLEDGE_BASE_INGESTION.md)

## Binding architecture

CUBI's assistant is a command-oriented, deterministic engineering system, not an open-ended chatbot. Its command understanding, dictionaries, grammar, parsers, engineering rules, knowledge records and response assembly must be CUBI-owned.

Prohibited: third-party AI/ML models or inference runtimes, local/remote model providers, embedding/vector services, AI APIs/keys, model fallbacks, generative summarizers, pretrained AI OCR/voice/translation services and unrestricted transcript memory.

The assistant may retrieve approved knowledge, but it may not:
- grant itself or a user project permissions;
- make up missing project inputs, values, calculations or evidence;
- change project data without a typed proposal, server-side authorization and required user approval;
- calculate schedule, calendar, resource, cost, progress, EVM or financial results outside the authoritative Shared Domain/Calculation Core;
- publish candidate knowledge without rights review, evidence, privacy review and authorized human approval.

## Knowledge model

Use durable, versioned records with stable identifiers, source/version/page/section provenance, scope, lifecycle state, inputs, outputs, units, assumptions, formula contract, validity conditions, limits, validation evidence, reviewer/approver and lineage.

Keep user-private, project-private, tenant-shared, general-candidate and general-published scopes isolated. General knowledge may contain only validated, privacy-reviewed methods and generalized rules; it must not contain another user's project data, identifiers, names, costs, quantities, dates, schedules, files or transcripts.

Use deterministic full-text/lexical search, exact identifiers, controlled taxonomy and versioned synonyms. No semantic embeddings or vector retrieval.

## Source-use rules

A public URL is not permission to copy or persist a copyrighted work. Record rights decisions before fetching or storing content. Oracle, PMI and ISO sources are reference-only until the relevant license/permission explicitly allows the intended internal processing. Do not publish protected PDFs or copied passages in CUBI or GitHub. Create original CUBI-authored explanations and retain narrow source/page references.

UK Government and GAO materials may have public reuse terms; verify attribution, third-party material and exact document notices before ingestion. Tag jurisdiction-specific guidance; do not misrepresent it as universal law.

## Status

These documents register sources and define the build contract only. They do not prove a production knowledge database, source-ingestion worker, admin console, search index, academy runtime, backup/restore or cross-user retrieval is implemented. Those require code, migrations, security tests, exact-head CI and end-to-end verification under #1540.
