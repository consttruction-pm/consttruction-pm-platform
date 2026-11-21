# Verified studio Help references

Date: 2026-11-21
Base commit: `f3f981f097ad26e22990a54a067ff512cd6dc5fa` (origin/main, PR #2103)
Branch: `feat/cubi-help-verified`

## Problem

Every studio recorded `HELP_REFERENCE_PENDING` and the Inspector showed no link.
The recorded topics named plausible Oracle pages, but the product rules require
opening the exact page before claiming a reference, and the client had no way to
distinguish a verified page from a guess.

## Verification

Each candidate URL was fetched on 2026-11-21. All returned `200`; the page title
matched the recorded topic:

| Studio | Page title | URL |
|---|---|---|
| Import staging | Importing and exporting data - Future period bucket planning FAQ | `https://docs.oracle.com/cd/G48902_01/client_help/en_US/48617.htm` |
| Schedule scenario | Scheduling Projects | `https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedulingprojects.htm` |
| Risk analysis | Risks | `https://docs.oracle.com/cd/G48902_01/client_help/en_US/risks.htm` |
| Project analysis | Earned Value | `https://docs.oracle.com/cd/G48902_01/client_help/en_US/earned_value.htm` |
| Decision & approval | Approving or Denying Budget Change Requests | `https://docs.oracle.com/cd/G48897_01/p6help/en/44036.htm` |

The earlier candidate for Decision (`.../p6help/en/51331.htm`) resolved to
"Reviewing Team Member Status Updates" and was **not** used. The retired
`the_gantt_chart.htm` page is valid but no longer corresponds to a studio-level
topic after the scenario topic was narrowed to "Scheduling Projects".

## What changed

- `Studio` gains `help_url`; the context payload returns `help_url`.
- `StudioStatus.HELP_REFERENCE_VERIFIED` replaces the blanket pending status for
  the five studios. They are only marked verified because the exact page was
  opened and recorded.
- `verifiedHelpUrl()` in `apps/web/src/workbench/model.ts` refuses any value that
  is not `https://docs.oracle.com/...`; the Inspector only renders a link through
  that function, with `target="_blank"` and `rel="noopener noreferrer"`.
- Per-control rows in `ENGINEERING_AI_WORKBENCH_HELP_MATRIX.md` remain
  `HELP_REFERENCE_PENDING`; a studio-level link is not presented as a per-control
  deep link.

## Verification runs

| Command | Result |
|---|---|
| `pytest tests/test_ai_workbench_http.py tests/test_ai_workbench_orchestration.py -q` | 56 passed |
| `npx tsx --test src/workbench-model.test.ts src/workbench-render.test.ts` | 36 passed |
| `npm test` | web suite + 16 preview-server passed, 0 failed |
| `npm run typecheck` | clean |
| `npm run build` | bundles emitted |
| `CUBI_CHROME_NO_SANDBOX=1 npm run test:e2e:preview` | passed, 115 checks, 57 screenshots |

New E2E record:

```json
{
  "name": "studio Help links are the recorded official references",
  "count": 5,
  "hosts": ["docs.oracle.com", "docs.oracle.com", "docs.oracle.com", "docs.oracle.com", "docs.oracle.com"],
  "pending_controls": 0
}
```

The journey also asserts every link opens with `target="_blank"` and
`rel` containing `noopener`.

## Limits

- The verification is at the studio level. Not every control in the Help matrix
  has an individually opened page; those rows stay pending.
- The E2E runs against the preview runtime; the link origin rule is unit-tested
  independently of the runtime.
- No vendor branding is introduced. The Inspector says "Open official
  reference"; the UI remains CUBI-branded.
