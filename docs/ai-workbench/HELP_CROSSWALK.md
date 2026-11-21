# Help Crosswalk

Every studio records a `help_topic`, a `help_status` and, when verified, an
exact `help_url` on the server. The Workbench renders a link only for an
`https://docs.oracle.com/` reference recorded here; it never guesses a URL.

## Document entry

The Workbench document is registered in `docs/traceability/engineering-v26.json`
as `ENG-WS-AI-WORKBENCH` (`/ai-workbench/`, `CUBI_OWNED`). It intentionally has
**no official Help topic**: the Workbench is CUBI-owned and no vendor page
describes it, so `resolveContextualHelp` falls back to internal documentation
for this route rather than borrowing a vendor topic.

## Verified studio references

Each page below was opened on 2026-11-21: it returned `200`, its title matched
the recorded topic, and the topic covers the studio's authoritative behaviour.
The Inspector renders the link with `target="_blank"` and
`rel="noopener noreferrer"`; CUBI branding is unchanged and no vendor brand is
displayed.

| Studio | `help_topic` | Exact `help_url` | Status |
|---|---|---|---|
| Project Import Review & Staging | Importing and exporting data | `https://docs.oracle.com/cd/G48902_01/client_help/en_US/48617.htm` | `HELP_REFERENCE_VERIFIED` |
| Schedule Scenario Studio | Scheduling Projects | `https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedulingprojects.htm` | `HELP_REFERENCE_VERIFIED` |
| Risk Analysis Studio | Risks | `https://docs.oracle.com/cd/G48902_01/client_help/en_US/risks.htm` | `HELP_REFERENCE_VERIFIED` |
| Project Analysis Studio | Earned Value | `https://docs.oracle.com/cd/G48902_01/client_help/en_US/earned_value.htm` | `HELP_REFERENCE_VERIFIED` |
| Decision & Approval Workspace | Approving or Denying Budget Change Requests | `https://docs.oracle.com/cd/G48897_01/p6help/en/44036.htm` | `HELP_REFERENCE_VERIFIED` |

The sources are the two official references named by the product rules:

- P6 Professional V26 HTML Help TOC:
  <https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm>
- P6 EPPM V26 HTML Help TOC:
  <https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm>

## Boundary of the verification

The verified URL is the studio-level reference. Individual control rows in
`ENGINEERING_AI_WORKBENCH_HELP_MATRIX.md` stay `HELP_REFERENCE_PENDING` until
that exact control's page is opened; a studio link is not presented as proof
that every control has its own deep link.

## What changed in the registry

- `Studio.help_url` is part of the server context payload (`help_url`).
- `StudioStatus.HELP_REFERENCE_VERIFIED` replaces the previous blanket pending
  status for the five studios above.
- The client refuses any URL that is not `https://docs.oracle.com/…` before
  rendering a link (`verifiedHelpUrl`).
- Tests pin the five exact URLs in the Python registry test and the client
  origin rule in `workbench-model.test.ts`.
