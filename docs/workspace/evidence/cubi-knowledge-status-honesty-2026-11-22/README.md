# Knowledge card status honesty — 2026-11-22

## What changed

The Enterprise knowledge centre painted every card's `publication_status` with
the success tone, whatever the server returned. The knowledge API also exposes
per-locale translation state. Both are now rendered from the value received.

| Layer | File | Change |
| --- | --- | --- |
| View | `apps/web/src/enterprise/pages/knowledge.ts` | `publicationTone()` / `translationTone()`; cards carry `data-testid="knowledge-card-<status>"` |
| Search | same | translation badges use the same tone map instead of always neutral |
| Tests | `apps/web/src/enterprise-knowledge.test.ts` | every status maps to its tone; unpublished never success |
| Browser | `apps/web/e2e/preview-e2e.mjs` | a success-toned card must carry `publication_status: published` |

## Tone map

| Publication | Tone |
| --- | --- |
| `published` | success |
| `validated` | info |
| `draft` | warning |
| `rejected`, `retired` | danger |
| anything else | neutral |

| Translation | Tone |
| --- | --- |
| `published`, `approved` | success |
| `translated` | info |
| `draft`, `review_required` | warning |
| `missing`, `retired` | neutral |

Only `published` is answerable guidance, which matches
`CardStatus.PUBLISHED` in `src/construction_pm/knowledge/api.py`.

## Verification

- `npm run typecheck` — clean
- `npm test` — 1298 + 16 passed (2 new cases)
- `CUBI_CHROME_NO_SANDBOX=1 npm run test:e2e:preview` — 127 recorded checks,
  including `Enterprise knowledge center states its real published state`
  with the statuses it saw.

## Not claimed

The preview deployment has no published cards, so the browser assertion proves
the invariant (no success tone without `published`) and the unit tests cover
the rest of the map. Rendering a real draft/translated card needs a store with
those rows.
