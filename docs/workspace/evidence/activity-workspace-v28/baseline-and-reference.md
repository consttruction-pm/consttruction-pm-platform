# V28 Stage 1 — Repository Baseline and Reference Verification

- Mission: complete the CUBI Activities workspace against P6 Professional V26 Help + the attached 815-page PDF.
- Date: 2026-11-18
- Environment: Hasan's Qoder Desktop, Windows 10.0.17763; local full-stack preview only.
- No merge, no deploy, no Vercel work.

## 1. Repository state at mission start

| Item | Value |
|---|---|
| `origin/main` | `9408552bcfb2b0e874333845a3ba437b8430a46b` |
| Working branch | `feat/2047-activity-workspace-v26` |
| Branch HEAD | `b3df87eb6c517ea9f7e837d31832848e5edcbab6` |
| Working tree | clean; no stashes |
| Issue | #2047 `OPEN` — "Engineering P1: complete Activity workspace windows and Version 26 dialogs" |
| PR | #2048 `OPEN`, `MERGEABLE`, head `b3df87eb6` |
| Exact-head CI on `b3df87eb6` | 10/10 pass (`test 3.11/3.12/3.13`, typecheck web/client-sync/desktop/mobile, `web`, Vercel automation) |
| Last code commit | `b71cd61f4` — V27 percent-complete column, save refresh, 1280×720 fit |
| Commits since last code change | documentation/evidence only (`6926d6a4e`, `1dfd9e1a9`, `145615c03`, `b3df87eb6`) |

The three V27 fixes are preserved and not re-opened except through regression tests:

1. R1 — 1280×720 geometry.
2. R2 — grid/Gantt re-read after a General save.
3. R3 — `activity.percent_complete_type`.

## 2. Reference verification

### 2.1 HTML Help

| Attempt | Result |
|---|---|
| `https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm` on 2026-11-18 | **HTTP 403 Forbidden**; no content returned |

The HTML source remains unavailable. It is recorded as **BLOCKED**, not assumed.

### 2.2 Attached PDF (now available)

| Property | Verified value |
|---|---|
| Path | `D:\کنترل پروژه\p6-professional-help.pdf` |
| Size | 3,105,001 bytes |
| Document title (cover) | **Primavera P6 Professional Help** |
| Document ID | **G57535-02** |
| Date | **October 2026** (page footer: October 9, 2026) |
| Page count | **815** (verified by text extraction page separators) |
| Extracted text | 2,700,597 characters, fully text-searchable (no OCR needed) |
| TOC | 24 Roman pages (`Page i of xxiv` … `Page xxiv of xxiv`) with printed page numbers |

The PDF is the primary available reference. Every feature cited in the V28 matrices
must carry a printed page number from this file. HTML remains the preferred source
if access is restored; differences will be recorded rather than resolved silently.

### 2.3 PDF chapter → PDF-page map (verified)

| Chapter | PDF pages | Printed page range |
|---|---:|---|
| 1 Welcome | 27 | 1–… |
| 2 Getting Started | 30 | 1–… |
| 3 Structuring Projects | 123 | 1–… |
| 5 Developing Projects | 195–262 | 1–68 |
| 6 Managing Projects | 263–323 | 1–61 |
| 7 Customizing Activity Layouts | 324–371 | 1–48 |
| 8 Tracking Projects | 372–402 | 1–31 |
| 9 Grouping, Filtering, and Summarizing Data | 403–423 | 1–21 |
| 11 Tools | 424–503 | 1–… |
| 13 Reference | 504–815 | 1–… |

Offset rule for chapters 5 and 7: **PDF page = printed page + 194** (chapter 5)
and **PDF page = printed page + 323** (chapter 7). Chapter 9 offset is +402.

## 3. Shared-file ownership check (before any V28 edit)

Open PRs that still modify the same shared files:

| PR | Shared files it touches |
|---|---|
| #1716 | `apps/web/src/main.ts`, `apps/web/src/workspace-view.ts`, `apps/web/src/workspace-desktop-shell.ts`, `apps/web/styles.css`, `apps/web/public/styles.css` |
| #1983 | `apps/web/src/main.ts`, `apps/web/src/workspace-view.ts`, `apps/web/src/workspace-activity-details.test.ts`, `apps/web/styles.css`, `apps/web/public/styles.css`, `src/construction_pm/backend_p0/workspace_read_provider.py` |
| #1711 | `apps/web/src/main.ts`, `apps/web/src/workspace-view.ts`, `apps/web/src/workspace-desktop-shell.ts`, `apps/web/styles.css`, `apps/web/public/styles.css` |

Our branch already contains the V27 changes to `main.ts`, the two `styles.css`
files and `workspace_read_provider.py`, disclosed in PR #2048. **V28 will not make
further shared-file changes without a demonstrated need**; client-only files
(`workspace-activity-filters.ts`, dialogs, tests, e2e) are preferred. Any unavoidable
shared edit will be listed here and in the PR body before it is pushed.

## 4. Evidence rules for this mission

- A topic is not "complete" because a menu item, button, test file or screenshot exists.
- Every matrix row states: Help topic + printed PDF page, CUBI equivalent, backend contract, test, status.
- HTML 403 and unavailable backend contracts are recorded as **BLOCKED/VERIFY**, never filled with invented behavior.
- Only local preview ports and isolated SQLite databases are used; each E2E run records its own exit code and evidence.
