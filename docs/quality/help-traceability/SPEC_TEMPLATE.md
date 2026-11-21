# Specification template

Every section document follows this shape. Keeping it identical makes the
reference machine-checkable and lets a new session resume without context.

## 1. Traceability matrix

One row per functional item. Tables stay readable; long prose belongs in the
page specification below.

| Column | Required content |
| --- | --- |
| `Env` | `Engineering`, `Enterprise` or `Shared` |
| `Page / module` | Exact CUBI page or module |
| `Row ID` | Reuse the ID from `docs/traceability/*.json` when one exists |
| `Functional item` | Exact control, field, command, filter or operation |
| `Help topic` | Exact official topic title |
| `Help URL` | Direct HTML Help URL, verified |
| `Help section` | Section/subsection inside the topic that describes the behavior |
| `User Guide` | Exact section title, only when a direct URL is verified |
| `User Guide URL` | Direct section URL |
| `Expected behavior` | What the documented operation does |
| `Inputs` | Required and optional fields or selections |
| `Validation` | Rejected values and the expected error code/message |
| `Dependencies` | Related modules, data or permissions |
| `Expected result` | Observable outcome |
| `Scenario` | ID of the acceptance scenario below |
| `Status` | `DOCUMENTED`, `HELP_VERIFIED`, `TEST_SPECIFIED`, `FUNCTIONALLY_VERIFIED`, `PARTIAL`, `BLOCKED`, `NOT_APPLICABLE` |
| `Evidence` | Test ID, issue or observed result |

Rules:

- A row without a verified URL is not `HELP_VERIFIED`.
- `NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT` is used when the
  official documentation does not cover the CUBI behavior.
- `HELP REFERENCE NOT YET VERIFIED` is used when a topic exists in principle but
  has not been opened. It is never replaced with an unrelated topic.
- A CUBI behavior that diverges from Help is documented as a divergence with
  the reason, not silently "fixed" in the docs.

## 2. Page specification

For each page:

```markdown
### <Page name> (`<route>`)

- **Purpose** — one paragraph.
- **Entry conditions** — session, tenant, project, data state.
- **Permissions** — roles that may read, write, administer.
- **Structure** — windows, tabs and panels in order.
- **Fields** — name, meaning, type, required/optional, default.
- **Commands** — toolbar, menu and context-menu actions.
- **Filters** — fields, operators, combinability, reset behavior.
- **Sorting / grouping** — levels, direction, persistence.
- **Search** — scope (selected/filtered/all) and result behavior.
- **Dialogs** — trigger, fields, validation, commit/cancel.
- **Validation** — rule, trigger, message and error code.
- **Save / cancel** — what persists, what reverts, revision behavior.
- **Dependencies** — services, data and modules.
- **Expected results** — observable post-conditions.
- **Error scenarios** — code, status, user-visible effect.
- **Help references** — topic, URL and section.
- **Acceptance criteria** — scenario IDs that must pass.
```

## 3. Acceptance scenario

```markdown
#### <SCENARIO-ID> — <title>

| Field | Content |
| --- | --- |
| Environment | Engineering / Enterprise / Shared |
| Page | route and surface |
| Feature | exact operation |
| Preconditions | session, roles, tenant, project, existing data |
| Test data | concrete values, including boundary values |
| User action | ordered steps |
| Expected result | observable state and persisted values |
| Negative scenario | invalid input and expected rejection |
| Permission scenario | role that must be denied and expected response |
| Persistence scenario | reload / logout / new session outcome |
| Related Help | exact topic and URL |
```

A scenario verifies behavior, not the presence of a control. Assertions name a
value or state that can be observed in the UI, the API response or the stored
record.

Scenario IDs use `<AREA>-<FEATURE>-<NN>`, for example
`ENG-ACT-COLUMNS-03`. They are unique across this directory and are referenced
from Issues when a defect is found.

## 4. Defect record

When the implementation contradicts the documented behavior:

```markdown
| Field | Content |
| --- | --- |
| Defect | short title |
| Page / row | traceability row ID |
| Help reference | topic, URL, section |
| Reproduction | numbered steps |
| Expected | documented behavior |
| Observed | actual behavior with status code |
| Issue | GitHub issue URL, assigned to Agent 1 |
```

The defect is recorded here and in a GitHub Issue. The implementation is not
changed by this workstream.
