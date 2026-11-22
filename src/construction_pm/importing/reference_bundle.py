"""Deterministic import bundle derived from the validated reference workbook.

The workbook is the operator's input. This module freezes the engineering and
enterprise rows into a compact, versioned JSON document so the guarded preview
can register the three demo projects without carrying a spreadsheet at runtime
and without inventing a second source of truth: every value here still comes
from the workbook, and every calculation remains CUBI's.

Derived/analytics sheets are deliberately excluded; they are recomputed by the
canonical services.

Contract: ``cubi-reference-import-bundle.v1``
"""

from __future__ import annotations

import gzip
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from .reference_projects import ReferenceDataset

BUNDLE_CONTRACT = "cubi-reference-import-bundle.v1"

# Engineering-core and enterprise sheets that are persisted by value.
INCLUDED_SHEETS: tuple[str, ...] = (
    "Project Register",
    "Project Settings",
    "EPS",
    "OBS",
    "WBS",
    "Project Milestones",
    "Project Codes",
    "Activity Codes",
    "Resource Codes",
    "Cost Codes",
    "Activities",
    "Activity Relationships",
    "Activity Constraints",
    "Activity Steps",
    "Activity Expenses",
    "Activity Documents",
    "Activity Progress",
    "Activity Status History",
    "Baselines",
    "Baseline Activities",
    "Schedule Options",
    "Calendars",
    "Calendar Workweeks",
    "Calendar Shifts",
    "Calendar Exceptions",
    "Resource Calendars",
    "Activity Calendar Assignments",
    "Resource Master",
    "Resource Roles",
    "Resource Skills",
    "Resource Rates",
    "Resource Availability",
    "Resource Assignments",
    "Resource Assignment Spreads",
    "Resource Actuals",
    "Equipment Register",
    "Material Register",
    "Labor Register",
    "Cost Accounts",
    "Project Budgets",
    "Activity Budgets",
    "Cost Periods",
    "Actual Costs",
    "Commitments",
    "Expenses",
    "Risk Register",
    "Risk Responses",
    "Issue Register",
    "Change Requests",
    "Contracts",
    "Contract Packages",
    "Procurement Register",
    "Vendor Register",
    "Document Register",
    "Document Revisions",
    "Quality Register",
    "Inspection Requests",
    "HSE Register",
    "NCR Register",
    "Punch List",
    "Lessons Learned",
    "Organization",
    "Project Teams",
    "Responsibility Assignments",
    "Team Tasks",
    "Workflow Templates",
    "Workflow Instances",
    "Approval Records",
    "Forms Register",
    "Timesheets",
    "Communication Log",
)

EXCLUDED_SHEETS: Mapping[str, str] = {
    "README": "source governance",
    "Data Dictionary": "field definitions, not data",
    "Data Validation": "source self-check; recomputed by the validator",
    "Schedule Run Inputs": "run manifest is written by the engine stage",
    "Audit Import Manifest": "written by the import application, not imported",
    # Derived analytics: never imported as facts.
    "Earned Value": "derived; recompute with the canonical EVM service",
    "EVM Periods": "derived; recompute",
    "EVM Forecast": "derived; recompute",
    "Cost Variance": "derived; recompute",
    "Schedule Variance": "derived; recompute",
    "EVM Dashboard Data": "derived; recompute",
    "Dashboard KPIs": "derived read model",
    "Portfolio Summary": "derived read model",
    "Milestone Trend": "derived read model",
    "Planned vs Actual": "derived read model",
    "Resource Histogram Data": "derived from capacity service",
    "Cost S-Curve Data": "derived read model",
    "Progress S-Curve Data": "derived read model",
    "Risk Matrix Data": "derived aggregate",
    "Procurement Dashboard": "derived read model",
    "Document Status Dashboard": "derived read model",
    "Resource Usage": "derived from assignments and spreads",
    "Cash Flow": "derived read model",
    "Labor Register": "headcount aggregate, not a resource truth",
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value).strip()


def _row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {_slug(str(key)): _value(value) for key, value in row.items()}


def _project_rows(dataset: ReferenceDataset, sheet: str, project_id: str) -> list[dict[str, Any]]:
    return [_row(row) for row in dataset.rows(sheet, project_id)]


def _calendar_project_map(dataset: ReferenceDataset) -> dict[str, str]:
    return {
        str(row.get("Calendar ID") or "").strip(): str(row.get("Project ID") or "").strip()
        for row in dataset.rows("Calendars")
        if str(row.get("Calendar ID") or "").strip()
    }


def build_bundle(dataset: ReferenceDataset) -> dict[str, Any]:
    """Freeze the workbook into one deterministic, per-project document."""

    calendar_project = _calendar_project_map(dataset)
    projects: dict[str, Any] = {}
    for project_id in dataset.project_ids:
        register = dataset.rows("Project Register", project_id)
        settings = dataset.rows("Project Settings", project_id)
        entry: dict[str, Any] = {
            "project": _row(register[0]) if register else {},
            "settings": _row(settings[0]) if settings else {},
        }
        for sheet in INCLUDED_SHEETS:
            if sheet in ("Project Register", "Project Settings"):
                continue
            key = _slug(sheet)
            if "Project ID" in (dataset.sheet(sheet).columns if dataset.sheet(sheet) else ()):
                entry[key] = _project_rows(dataset, sheet, project_id)
            else:
                # Sheets keyed by calendar ownership rather than Project ID.
                owner_only = "Calendar ID" in (
                    dataset.sheet(sheet).columns if dataset.sheet(sheet) else ()
                )
                if owner_only:
                    entry[key] = [
                        _row(row)
                        for row in dataset.rows(sheet)
                        if calendar_project.get(
                            str(row.get("Calendar ID") or "").strip()
                        )
                        == project_id
                    ]
                else:
                    entry[key] = [_row(row) for row in dataset.rows(sheet)]
        projects[project_id] = entry

    register = dataset.rows("Project Register")
    return {
        "contract": BUNDLE_CONTRACT,
        "source": {
            "file": dataset.source.name,
            "sha256": dataset.source_sha256,
            "status_date": _value(register[0].get("Status Date")) if register else None,
            "classification": "DEMO/SYNTHETIC",
            "sheet_count": len(dataset.sheets),
            "project_ids": list(dataset.project_ids),
        },
        "projects": projects,
        "excluded": dict(EXCLUDED_SHEETS),
    }


def dumps(bundle: Mapping[str, Any]) -> bytes:
    return json.dumps(
        bundle,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def write_bundle(bundle: Mapping[str, Any], path: str | Path) -> Path:
    """Write the bundle as deterministic gzip (mtime fixed, no file name)."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dumps(bundle)
    with target.open("wb") as raw:
        # An empty filename and a fixed mtime make the archive byte-identical
        # for the same bundle, so the committed artifact is reviewable by hash.
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
            compressed.write(payload)
    return target


def load_bundle(path: str | Path) -> dict[str, Any]:
    with gzip.open(Path(path), "rb") as handle:
        payload = json.loads(handle.read().decode("utf-8"))
    if payload.get("contract") != BUNDLE_CONTRACT:
        raise ValueError(
            f"BUNDLE_CONTRACT_MISMATCH:{payload.get('contract')!r}"
        )
    return payload


__all__ = [
    "BUNDLE_CONTRACT",
    "EXCLUDED_SHEETS",
    "INCLUDED_SHEETS",
    "build_bundle",
    "dumps",
    "load_bundle",
    "write_bundle",
]
