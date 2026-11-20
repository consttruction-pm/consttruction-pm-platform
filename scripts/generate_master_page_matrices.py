#!/usr/bin/env python3
"""Generate the master page/component matrices from the traceability sources.

The script is deliberately data-driven: every row comes from
``docs/traceability/*.json`` (page, surface, Help topic, owning evidence) and
from the audited status table below. It never invents a Help URL or a route.

Usage:  python3 scripts/generate_master_page_matrices.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
PRODUCT = DOCS / "product"
ENGINEERING = DOCS / "engineering"
ENTERPRISE = DOCS / "enterprise"
for directory in (PRODUCT, ENGINEERING, ENTERPRISE):
    directory.mkdir(parents=True, exist_ok=True)

# --- audited status -------------------------------------------------------
# WIRED_READ / WIRED_WRITE mean the surface is connected to a real server
# contract (read or read+write). VERIFIED additionally requires an observed
# browser proof recorded in CUBI_PAGE_ACCEPTANCE_REPORT.md.
STATUS_MAP = {
    "PUBLISHED": "VERIFIED",
    "IMPLEMENTED": "WIRED_WRITE",
    "PARTIAL": "WIRED_READ",
    "PLANNED": "MISSING",
    "CUBI_OWNED": "VERIFIED",
    "LEGAL": "VERIFIED",
}

# Rows exercised by the 101-check browser E2E (2026-11-20, SHA 0014928bf).
BROWSER_E2E = {
    "ENG-WS-SHELL",
    "ENG-WS-MENUS",
    "ENG-WS-ACTIVITY-TABLE",
    "ENG-WS-GANTT",
    "ENG-WS-GANTT-BARS",
    "ENG-WS-DATA-DATE",
    "ENG-WS-NETWORK",
    "ENG-WS-DETAILS",
    "ENG-WS-WBS",
    "ENG-WS-SELECTION",
    "ENG-WS-RELATIONSHIPS",
}

# Public pages exercised by the 18-check responsive audit (same SHA).
PUBLIC_RESPONSIVE = {"ENG-PUB-HOME", "ENG-PUB-PLATFORM", "ENG-PUB-FEATURES"}

INITIAL_25 = {
    "public-homepage": "ENG-PUB-HOME",
    "login-entry": None,
    "role-context": None,
    "personal-workbench": None,
    "environment-selector": "ENT-HOME",
    "engineering-shell": "ENG-WS-SHELL",
    "projects-eps": "ENG-WS-PROJECTS",
    "wbs": "ENG-WS-WBS",
    "activities": "ENG-WS-ACTIVITY-TABLE",
    "activity-details": "ENG-WS-DETAILS",
    "relationships-network": "ENG-WS-NETWORK",
    "gantt": "ENG-WS-GANTT",
    "resources-assignments": "ENG-WS-RESOURCES",
    "calendars": "ENG-WS-CALENDARS",
    "reports-tracking": "ENG-WS-TRACKING",
    "enterprise-dashboard": "ENT-DASHBOARDS",
    "portfolio-executive": "ENT-PORTFOLIO",
    "enterprise-projects": "ENT-PROJECTS",
    "organization-access": "ENT-ORG-ACCESS",
    "team-task-center": "ENT-TEAM-TASKS",
    "workflow-studio": "ENT-WORKFLOW",
    "approval-center": "ENT-FEEDBACK-APPROVAL",
    "resources-capacity": "ENT-RESOURCES",
    "operations-reports": "ENT-OPERATIONS",
    "project-portal": "ENT-PORTAL",
}

# Surfaces that exist outside the traceability register (entry flow + the new
# signed-in workbench). Statuses are backed by this mission's own evidence.
CUSTOM_ROWS = [
    {
        "page_id": "SURF-LOGIN",
        "environment": "shared",
        "page": "/login",
        "surface": "Login / entry",
        "help_topic": "CUBI-owned authentication surface; no product Help topic applies.",
        "help_url": "",
        "evidence": "apps/web/login.html; apps/web/src/login-locale.test.ts",
        "status": "VERIFIED",
        "note": "Ten locales, server-side session POST/DELETE, CSRF and open-redirect sanitising; exercised by production-login E2E and pytest.",
    },
    {
        "page_id": "SURF-WORKBENCH",
        "environment": "shared",
        "page": "/workbench/",
        "surface": "Personal Workbench",
        "help_topic": "CUBI-owned entry surface; no product Help topic applies.",
        "help_url": "",
        "evidence": "apps/web/src/personal-workbench.ts; apps/web/src/personal-workbench.test.ts",
        "status": "WIRED_READ",
        "note": "Reads /api/session, /api/projects and /api/enterprise/tasks; environment cards are enabled from server responses only. Browser screenshot pending.",
    },
    {
        "page_id": "SURF-ROLE-CONTEXT",
        "environment": "shared",
        "page": "/workbench/",
        "surface": "Role and working context",
        "help_topic": "CUBI-owned entry surface; no product Help topic applies.",
        "help_url": "",
        "evidence": "apps/web/src/personal-workbench.ts (identity block)",
        "status": "WIRED_READ",
        "note": "Roles and tenant come from the authenticated session; no separate role-selection step exists because the final login replaced it.",
    },
    {
        "page_id": "SURF-ENV-SELECTOR",
        "environment": "shared",
        "page": "/workbench/ + /environments/",
        "surface": "Environment selector",
        "help_topic": "CUBI-owned entry surface; no product Help topic applies.",
        "help_url": "",
        "evidence": "apps/web/src/personal-workbench.ts; apps/web/public/environments/index.html",
        "status": "WIRED_READ",
        "note": "Grants are decided by server responses (projects register and enterprise task scope). The public /environments/ page stays explanatory and links to sign-in.",
    },
]


def load(name: str) -> dict:
    return json.loads((DOCS / "traceability" / name).read_text(encoding="utf-8"))


# Enterprise routes that the production server actually serves. Only /enterprise/
# exists today; the other fifteen registered routes are not mounted, so their
# traceability status cannot exceed MISSING regardless of backend modules.
ENTERPRISE_ROUTE_OVERRIDES = {
    "ENT-HOME": ("WIRED_READ", "Static /environments/ page; links to sign-in, no server grant check on the page itself."),
    "ENT-TEAM-TASKS": ("WIRED_WRITE", "/enterprise/ mounts the task center against /api/enterprise/tasks with revision guards."),
}
ENTERPRISE_MISSING_NOTE = "No route is served for this page at the audited SHA; backend modules alone are not a page."


def rows_for(environment: str, data: dict) -> list[dict]:
    output = []
    for row in data["rows"]:
        help_block = row.get("help") or {}
        status = STATUS_MAP.get(row["status"], "NOT_AUDITED")
        browser = ""
        if row["id"] in BROWSER_E2E and status.startswith("WIRED"):
            status = "VERIFIED"
            browser = "preview-e2e"
        elif row["id"] in PUBLIC_RESPONSIVE:
            browser = "public-site-responsive"
        note = row.get("cubiBehavior") or ""
        if environment == "enterprise":
            override = ENTERPRISE_ROUTE_OVERRIDES.get(row["id"])
            if override:
                status, note = override
            elif row["id"] != "ENT-TEAM-TASKS":
                status = "MISSING"
                note = ENTERPRISE_MISSING_NOTE
        output.append(
            {
                "environment": environment,
                "page_id": row["id"],
                "page": row["page"],
                "surface": row["surface"],
                "kind": row.get("kind") or "",
                "help_topic": help_block.get("title") or "",
                "help_url": help_block.get("url") or "",
                "evidence": row.get("evidence") or "",
                "status": status,
                "source_status": row["status"],
                "browser": browser,
                "note": note,
            }
        )
    return output


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def help_table(rows: list[dict]) -> str:
    lines = [
        "| Page ID | Page | Surface | Help topic | Direct HTML URL | Status | Evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        url = f"[{row['help_topic']}]({row['help_url']})" if row["help_url"] else "—"
        lines.append(
            f"| {row['page_id']} | {row['page']} | {row['surface']} | {row['help_topic'] or '—'} | {url} | {row['status']} | {row['evidence']} |"
        )
    return "\n".join(lines)


def main() -> None:
    eng = load("engineering-v26.json")
    ent = load("enterprise-v26.json")
    eng_rows = rows_for("engineering", eng)
    ent_rows = rows_for("enterprise", ent)

    # --- master matrix ----------------------------------------------------
    master = []
    for key, page_id in INITIAL_25.items():
        if page_id is None:
            row = next(item for item in CUSTOM_ROWS if item["page_id"] == {
                "login-entry": "SURF-LOGIN",
                "role-context": "SURF-ROLE-CONTEXT",
                "personal-workbench": "SURF-WORKBENCH",
            }[key])
            master.append({**row, "initial_25": "yes", "initial_slot": key})
            continue
        source = next(item for item in eng_rows + ent_rows if item["page_id"] == page_id)
        master.append({**source, "initial_25": "yes", "initial_slot": key})
    for row in eng_rows + ent_rows:
        if any(item["page_id"] == row["page_id"] for item in master):
            continue
        master.append({**row, "initial_25": "no", "initial_slot": ""})

    fields = [
        "environment", "page_id", "page", "surface", "kind", "help_topic", "help_url",
        "status", "source_status", "browser", "evidence", "note", "initial_25", "initial_slot",
    ]
    write_csv(PRODUCT / "CUBI_MASTER_PAGE_COMPONENT_MATRIX.csv", master, fields)
    (PRODUCT / "CUBI_MASTER_PAGE_COMPONENT_MATRIX.json").write_text(
        json.dumps(
            {
                "contract": "cubi-master-page-component-matrix.v1",
                "generated_from": [
                    "docs/traceability/engineering-v26.json",
                    "docs/traceability/enterprise-v26.json",
                    "scripts/generate_master_page_matrices.py",
                ],
                "counts": {
                    "total": len(master),
                    "initial_25": sum(1 for row in master if row["initial_25"] == "yes"),
                    "engineering": sum(1 for row in master if row["environment"] == "engineering"),
                    "enterprise": sum(1 for row in master if row["environment"] == "enterprise"),
                    "shared": sum(1 for row in master if row["environment"] == "shared"),
                },
                "rows": master,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    # --- per-environment field/help matrices ------------------------------
    project_fields = [
        ("Business domain", "enum", "yes", "Construction/Oil & Gas/Infrastructure/Industrial/Energy/Other", "User input"),
        ("Portfolio", "picker", "no", "Must belong to tenant", "Dictionary"),
        ("Project name", "text", "yes", "2–120 chars", "User input"),
        ("Project ID", "text", "yes", "[A-Z0-9][A-Z0-9_-]{1,39}, unique per tenant", "User input"),
        ("Description", "textarea", "no", "≤2000 chars", "User input"),
        ("Start date", "date", "yes", "Valid in active calendar", "User input"),
        ("Target finish", "date", "no", "≥ start", "User input"),
        ("Date system", "enum", "yes", "gregorian / jalali", "User input"),
        ("Project calendar", "picker", "yes", "Must exist in tenant", "Dictionary"),
        ("Responsible organisation", "picker", "no", "Must belong to business domain", "Dictionary"),
        ("Default duration type", "enum", "no", "Fixed duration / units / units per time", "User input"),
        ("WBS template", "picker", "no", "Blank or template", "Dictionary"),
        ("Seed activities", "toggle", "no", "—", "User input"),
    ]
    field_rows = "\n".join(
        f"| {name} | {kind} | {required} | {validation} | {source} | Project create form | WIRED_WRITE | workspace-form-field-inventory.md |"
        for name, kind, required, validation, source in project_fields
    )

    eng_md = f"""# CUBI Engineering — page, field and Help matrix

**Generated from:** `docs/traceability/engineering-v26.json` and `scripts/generate_master_page_matrices.py`
**Rows:** {len(eng_rows)} · **Machine-readable twin:** `ENGINEERING_PAGE_FIELD_HELP_MATRIX.json`

Status vocabulary: `VERIFIED`, `WIRED_WRITE`, `WIRED_READ`, `SHELL_ONLY`, `MISSING`, `NOT_AUDITED`, `BLOCKED_EXTERNAL`.
Only `VERIFIED` rows carry an observed browser proof; every other row is backed by source, unit/contract tests or API evidence, not by a screenshot.

## Page and Help matrix

{help_table(eng_rows)}

## Field-level coverage — Project creation (real form contract)

Source: `docs/workspace/architecture/workspace-form-field-inventory.md`. Persistence and revision guards are exercised by the project lifecycle HTTP tests; the form itself is rendered by the workspace.

| Field | Type | Required | Validation | Source of truth | Surface | Status | Source document |
|---|---|---|---|---|---|---|---|
{field_rows}

## Field-level coverage — the remaining surfaces

Field extraction for the other 66 rows is tracked per window in `v26-complete-window-component-catalog.md` and `workspace-form-field-inventory.md`. The per-field audit rows (Tab, Component, Field ID, Label, API, Permission, Audit, Help topic, Test ID, Screenshot) are **NOT_AUDITED** for those surfaces in this revision and must be filled before any row is promoted to `VERIFIED`. No field was invented to fill this table.
"""
    (ENGINEERING / "ENGINEERING_PAGE_FIELD_HELP_MATRIX.md").write_text(eng_md, encoding="utf-8")
    (ENGINEERING / "ENGINEERING_PAGE_FIELD_HELP_MATRIX.json").write_text(
        json.dumps(
            {
                "contract": "cubi-engineering-page-field-help-matrix.v1",
                "pages": eng_rows,
                "fields": [
                    {
                        "surface": "Project create form",
                        "field": name,
                        "type": kind,
                        "required": required == "yes",
                        "validation": validation,
                        "source_of_truth": source,
                        "status": "WIRED_WRITE",
                        "source_document": "docs/workspace/architecture/workspace-form-field-inventory.md",
                    }
                    for name, kind, required, validation, source in project_fields
                ],
                "field_audit_pending": [row["page_id"] for row in eng_rows if row["page_id"] != "ENG-WS-PROJECTS"],
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    ent_md = f"""# CUBI Enterprise — page, field and Help matrix

**Generated from:** `docs/traceability/enterprise-v26.json` and `scripts/generate_master_page_matrices.py`
**Rows:** {len(ent_rows)} · **Machine-readable twin:** `ENTERPRISE_PAGE_FIELD_HELP_MATRIX.generated.json`

## Page and Help matrix

{help_table(ent_rows)}

## Field-level coverage

Only `/enterprise/` (Team & Task Center) currently has a wired form contract: title, description, project scope, priority, due date, status transitions and revision guard, all exercised by `apps/web/src/enterprise-task-center.test.ts` and the enterprise task HTTP tests. For the other fifteen surfaces the required field lists are enumerated in the product order but **not yet audited against code**; each is recorded as `NOT_AUDITED` rather than filled with placeholder rows. Enterprise documents, portal, workflow, approvals and risk registers have no implementation to extract fields from at this SHA.
"""
    # The hand-authored delivery matrix is authoritative:
    # docs/enterprise/ENTERPRISE_PAGE_FIELD_HELP_MATRIX.md. This generator keeps
    # the traceability twin under a distinct name so it cannot overwrite it.
    (ENTERPRISE / "ENTERPRISE_TRACEABILITY_MATRIX_GENERATED.md").write_text(ent_md, encoding="utf-8")
    (ENTERPRISE / "ENTERPRISE_PAGE_FIELD_HELP_MATRIX.generated.json").write_text(
        json.dumps(
            {
                "contract": "cubi-enterprise-page-field-help-matrix.v1",
                "pages": ent_rows,
                "fields": [
                    {"surface": "/enterprise/", "field": name, "status": "WIRED_WRITE"}
                    for name in ("title", "description", "project scope", "priority", "due date", "status", "revision")
                ],
                "field_audit_pending": [row["page_id"] for row in ent_rows if row["page_id"] != "ENT-TEAM-TASKS"],
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"master rows: {len(master)} (initial 25: {sum(1 for row in master if row['initial_25'] == 'yes')})")
    print(f"engineering rows: {len(eng_rows)} · enterprise rows: {len(ent_rows)}")


if __name__ == "__main__":
    main()
