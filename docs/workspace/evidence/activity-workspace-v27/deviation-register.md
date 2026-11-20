# V27 Deviation Register — Activities Workspace

- Tested head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Every entry is deliberate, evidenced and owned. None is hidden inside a
  "passed" claim.

| ID | Deviation | Type | Evidence | Impact | Owner / next action |
|---|---|---|---|---|---|
| D-V27-01 | Official HTML Help host returns HTTP 403 | BLOCKED reference | `help-topic-inventory.md` §1 (fetch 2026-11-18) | Cannot re-verify topic text, option names or defaults today | Supply the 815-page PDF or allow Help access |
| D-V27-02 | Version 26 Help PDF is not present in the repo/workspace | MISSING reference | repository search 2026-11-18 | Same as above; no page-level citations added | Product owner supplies the PDF |
| D-V27-03 | Full Screen cannot enter in HeadlessChrome | ENVIRONMENT | `workspace-responsive-v26` scenario 07 records `supported:false` only when UA matches `HeadlessChrome` | Real browsers still fail the assertion if fullscreen breaks; only the headless env is exempted | Re-run scenario 07 in a headed browser for a strict pass |
| D-V27-04 | Codes, Notebook, Steps and per-activity Document links have no write contract | CONTRACT/API GAP | `backend-contract-matrix.md` R4–R7; `activity-details-matrix.md` | These four tabs are read-only/incomplete; no simulated persistence | Platform defines the contracts; UI follows |
| D-V27-05 | No dedicated Lookahead filter dialog | FUNCTIONAL GAP | `filter-type-matrix.md` §5 | Relative dates + ranges provide the capability, not the vendor dialog | Implement when Help text is available |
| D-V27-06 | No pixel-level vendor screenshot comparison | SCOPE LIMITATION | `visual-fidelity-matrix.md` §5 | Fidelity is structural/behavioural; no pixel-diff claim | Obtain lawful reference captures if required |
| D-V27-07 | One user layout per project/view; New/Save As/Import replace that slot | BACKEND LIMIT | `layout-selector-v26`, `layout-trace-v26` | Named layout collections are not available | Layout API evolution, out of this PR |
| D-V27-08 | Clipboard, Delete, Find Next, Leveling and Commit shortcuts are intentionally blocked | CONTRACT GAP | `keyboard-shortcut-matrix.md` | The chords explain why instead of acting | Add contracts, then enable |
| D-V27-09 | Four Python tests fail on this Windows host for environment reasons | ENVIRONMENT | `test-coverage-matrix.md` §2 | Broad suite: 4676 passed, 4 env failures (`resource`, `pypdf`, POSIX `/tmp` path) | CI on the intended platform; not caused by V27 |
| D-V27-10 | "Calendar (CUBI)" is the 17th Details tab and is a CUBI extension | DELIBERATE EXTENSION | `activity-details-matrix.md` #17 | Adds calendar context; does not replace any official tab | Keep, labelled as CUBI |
| D-V27-11 | Task / Discussion / Feedback Details tabs are not implemented | EDITION BOUNDARY | `reference/oracle-p6-reference-index.md` ("EPPM only") | Desktop Professional does not require them | Out of scope unless CUBI adds an EPPM-equivalent service |
| D-V27-12 | Reports toolbar family is declared but has no buttons in the reference state | STATE COVERAGE | toolbar inventory: 11 declared families, 10 populated; 57 buttons | Declaring the family without buttons is not a broken control; it is empty by design | Add report-toolbar commands when the reporting surface is in scope |
| D-V27-13 | No vendor names, logos or product branding in the UI | DELIBERATE | shell review | Only CUBI identity appears | Keep |
| D-V27-14 | Some suite JSON records `testedCodeSha = f349d474` although the working tree matched `b71cd61f4` | EVIDENCE PRECISION | `test-coverage-matrix.md` §3 | The suites ran before the code commit; re-run key suites record `b71cd61f4` | Re-run remaining suites after the next commit if a strict SHA match is required |
| D-V27-15 | Activity clipboard / delete / fill-down / dissolve / additional-view / leveling / baselines / update-progress / report-wizard commands are disabled | CONTRACT GAP | `menu-command-matrix.md` | Disabled with a localized reason; never faked | Platform contracts |
| D-V27-16 | No production or external deployment was performed | DELIBERATE | directive | Verification is local full-stack preview only | Owner decides deployment separately |

## Not a deviation

- The 1280×720 overflow (V26 R1) is **fixed**: document scroll width equals the
  viewport at 1280 in both LTR and RTL (`workspace-responsive-v26` 11/11).
- The V26 grid-refresh gap (R2) is **fixed** and browser-verified.
- The V26 missing `activity.percent_complete_type` cell (R3) is **fixed** in the
  read model, seed, layout, test and browser column.
