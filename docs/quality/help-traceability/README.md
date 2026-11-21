# Help traceability and acceptance specifications (Agent 2)

This directory is the independent, Help-based functional reference for CUBI
Engineering, CUBI Enterprise, Knowledge, Assistant and AI Workbench.

It exists to make the product more accurate, traceable and testable **without
owning or changing the implementation**. Agent 1 owns product code, runtime,
routing, API contracts, database and deployment. This workstream owns
documentation, official Help traceability and acceptance-test specifications.

## What this directory is

- A per-page functional specification: purpose, permissions, fields, commands,
  validation, dependencies, expected results and errors.
- A page-by-page crosswalk from each CUBI surface to an **official** Help topic
  (exact title, direct HTML Help URL, section) and, where a direct section URL
  exists, the P6 Professional V26 User Guide.
- Executable or directly implementable acceptance scenarios with preconditions,
  data, action, expected result, negative path, permission path, persistence
  path and Help reference.
- A progress index that lets a new session resume without chat history.

## What this directory is not

- It is not a second page↔Help index. `docs/traceability/` already owns that:
  `engineering-v26.json` and `enterprise-v26.json` are the single source of
  truth for rows, IDs, statuses and implementation evidence. This directory
  **consumes** those rows and adds behavior and test specifications.
- It is not an implementation plan, architecture, AI runtime, scheduler or
  database design. Those belong to Agent 1 and the existing architecture docs.
- It never authorizes a product change. A discovered defect becomes a scoped
  GitHub Issue assigned to Agent 1.

## Official baselines

| Environment | Help baseline | Entry point |
| --- | --- | --- |
| CUBI Engineering | P6 Professional V26 HTML Help (`G48902-01`) | <https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm> |
| CUBI Enterprise | P6 EPPM V26 HTML Help (`G48897-01`) | <https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm> |
| Engineering detail | P6 Professional V26 User Guide (`G57529-01`) | <https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/toc.htm> |

The official HTML Help Table of Contents is mandatory. PDF, screenshots, third
party tutorials and memory are not substitutes. See
[`OFFICIAL_HELP_BASELINE.md`](OFFICIAL_HELP_BASELINE.md) for the verified
inventory and the current link-check result.

## Vocabulary

Page and feature status:

| Status | Meaning |
| --- | --- |
| `DOCUMENTED` | The page/feature specification is written and reviewed. |
| `HELP_VERIFIED` | Every cited Help URL was opened, is listed in the official TOC and its title matches. |
| `TEST_SPECIFIED` | Acceptance scenarios exist and are executable or directly implementable. |
| `FUNCTIONALLY_VERIFIED` | An executed test or observed runtime result proves the behavior. Never inferred from documentation. |
| `PARTIAL` | A documented subset exists; the gap is named in the section. |
| `BLOCKED` | An external dependency prevents verification; the dependency is named. |
| `NOT_APPLICABLE` | No official Help topic applies; CUBI-specific or legal. |

Work status:

`NOT_STARTED` → `IN_PROGRESS` → `DOCUMENTED` → `HELP_VERIFIED` →
`TEST_SPECIFIED` → `PR_OPEN` → `MERGED`.

A Help reference is `HELP_VERIFIED` only after a real request returned the
topic. A section is `MERGED` only after a verified merge commit.

## Structure

| File | Role |
| --- | --- |
| `PROGRESS_INDEX.md` | Section plan, status, last verified commit, next task, open PR/Issues, gaps. |
| `OFFICIAL_HELP_BASELINE.md` | Baseline identifiers, TOC verification, link-check method and result. |
| `SPEC_TEMPLATE.md` | Required shape of a page specification and an acceptance scenario. |
| `ENGINEERING_*.md` | Engineering sections, in dependency order. |
| `ENTERPRISE_*.md` | Enterprise sections. |
| `KNOWLEDGE_ASSISTANT_*.md` | Knowledge, Assistant and AI Workbench acceptance. |
| `LOCALIZATION_ACCEPTANCE.md` | Ten-locale acceptance matrix. |
| `evidence/` | Machine link-verification reports. |

## How a row is written

Every functional item cites:

1. the exact CUBI page and control;
2. the exact official Help topic title, direct URL and the section/subsection
   where the behavior is described;
3. the User Guide topic and direct URL only when a direct section URL is
   verified;
4. expected behavior, inputs, validation, dependencies and observable result;
5. one acceptance scenario with positive, negative, permission and persistence
   paths;
6. status and evidence.

If the official Help does not describe a CUBI behavior, the row states
`NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT`.

If a topic cannot be located, the row states `HELP REFERENCE NOT YET VERIFIED`.
A missing reference is never replaced with an unrelated topic.

## Verification

```bash
python scripts/verify_help_traceability.py --out docs/quality/help-traceability/evidence/help-link-verification-YYYY-MM-DD.json
```

The script reads the canonical traceability JSON, parses both official Tables of
Contents and checks every URL: HTTP 200, TOC membership, title match. Exit code
0 means every row passed. It never modifies product code or data.

The web test `apps/web/src/traceability.test.ts` remains the guard for the JSON
contract itself (unique IDs, route coverage, existing evidence paths, no vendor
branding in customer UI).

## Working rules

1. Read the current `docs/traceability` rows before writing a section; reuse the
   row ID and Help URL, do not re-invent them.
2. Deliver one section per PR. Run the link check, commit, open the PR, wait for
   CI, merge, then update `PROGRESS_INDEX.md` in the next section's PR or a
   small follow-up.
3. Never edit implementation files. If a defect is found, open an Issue with the
   page, Help topic, reproduction steps and expected behavior, then continue.
4. Record only what was observed. Documentation alone is not verification.
