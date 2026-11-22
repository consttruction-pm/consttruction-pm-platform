"""Validate the three reference projects workbook before anything is persisted.

The workbook is the operator's master data. This module reads every sheet,
checks the engineering-core referential integrity and returns a deterministic
report with per-sheet and per-project counts. It never writes to a database and
never calculates schedule, cost or earned value: CUBI Engineering owns those.

Contract: ``cubi-reference-import-source.v1``
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "cubi-reference-import-source.v1"

# Sheets that carry the engineering chain. A missing one is an error; every
# other sheet in the workbook is read and counted but may be absent in a test
# fixture.
REQUIRED_SHEETS: tuple[str, ...] = (
    "Project Register",
    "Project Settings",
    "EPS",
    "OBS",
    "WBS",
    "Activities",
    "Activity Relationships",
    "Calendars",
    "Calendar Workweeks",
    "Resource Master",
    "Equipment Register",
    "Resource Assignments",
    "Baselines",
    "Baseline Activities",
    "Activity Progress",
    "Earned Value",
)

RELATIONSHIP_TYPES = frozenset({"FS", "SS", "FF", "SF"})
ACTIVITY_STATUSES = frozenset(
    {"Not Started", "In Progress", "Completed", "Suspended"}
)

Severity = str  # "error" | "warning"


@dataclass(frozen=True)
class Sheet:
    """One worksheet with its header row and normalised row mappings."""

    name: str
    columns: tuple[str, ...]
    rows: tuple[Mapping[str, Any], ...]

    def column_index(self, column: str) -> int:
        return self.columns.index(column) if column in self.columns else -1


@dataclass(frozen=True)
class ImportIssue:
    code: str
    severity: Severity
    sheet: str
    record: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "sheet": self.sheet,
            "record": self.record,
            "detail": self.detail,
        }


@dataclass
class ReferenceDataset:
    source: Path
    source_sha256: str
    sheets: Mapping[str, Sheet]
    project_ids: tuple[str, ...]

    def sheet(self, name: str) -> Sheet | None:
        return self.sheets.get(name)

    def rows(self, name: str, project_id: str | None = None) -> tuple[Mapping[str, Any], ...]:
        sheet = self.sheets.get(name)
        if sheet is None:
            return ()
        if project_id is None:
            return sheet.rows
        return tuple(row for row in sheet.rows if _text(row.get("Project ID")) == project_id)

    def counts(self) -> dict[str, dict[str, object]]:
        """Record counts per sheet, total and per project."""

        counts: dict[str, dict[str, object]] = {}
        for name, sheet in self.sheets.items():
            per_project: dict[str, int] = {project: 0 for project in self.project_ids}
            outside = 0
            for row in sheet.rows:
                project = _text(row.get("Project ID"))
                if project in per_project:
                    per_project[project] += 1
                elif project:
                    outside += 1
            entry: dict[str, object] = {"total": len(sheet.rows), "projects": per_project}
            if outside:
                entry["outside_projects"] = outside
            counts[name] = entry
        return counts


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def read_workbook(path: str | Path) -> dict[str, Sheet]:
    """Read every worksheet into header-keyed rows.

    Empty header cells are dropped; a duplicate header is a hard failure because
    it would silently overwrite a column.
    """

    from openpyxl import load_workbook

    source = Path(path)
    workbook = load_workbook(source, data_only=True, read_only=True)
    sheets: dict[str, Sheet] = {}
    try:
        for name in workbook.sheetnames:
            worksheet = workbook[name]
            header_row: tuple[Any, ...] | None = None
            rows: list[Mapping[str, Any]] = []
            for raw in worksheet.iter_rows(values_only=True):
                if header_row is None:
                    header_row = raw
                    columns = tuple(
                        _text(cell) for cell in raw if cell is not None and _text(cell)
                    )
                    if len(set(columns)) != len(columns):
                        raise ValueError(f"DUPLICATE_HEADER:{name}")
                    continue
                if all(_text(cell) == "" for cell in raw):
                    continue
                record = {
                    columns[index]: raw[index] if index < len(raw) else None
                    for index in range(len(columns))
                }
                rows.append(record)
            sheets[name] = Sheet(
                name=name,
                columns=() if header_row is None else tuple(
                    _text(cell) for cell in header_row if cell is not None and _text(cell)
                ),
                rows=tuple(rows),
            )
    finally:
        workbook.close()
    return sheets


def load_dataset(path: str | Path) -> ReferenceDataset:
    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    sheets = read_workbook(source)
    register = sheets.get("Project Register")
    project_ids = tuple(
        _text(row.get("Project ID"))
        for row in (() if register is None else register.rows)
        if _text(row.get("Project ID"))
    )
    return ReferenceDataset(
        source=source,
        source_sha256=digest,
        sheets=sheets,
        project_ids=project_ids,
    )


def _index(rows: Iterable[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = _text(row.get(key))
        if value:
            indexed.setdefault(value, row)
    return indexed


def validate_dataset(dataset: ReferenceDataset) -> list[ImportIssue]:
    """Return every integrity issue, deterministic by sheet and record id."""

    issues: list[ImportIssue] = []

    def issue(code: str, sheet: str, record: str, detail: str, severity: Severity = "error") -> None:
        issues.append(ImportIssue(code, severity, sheet, record, detail))

    for name in REQUIRED_SHEETS:
        if dataset.sheet(name) is None:
            issue("SHEET_MISSING", name, "", "required sheet is absent from the workbook")

    expected_projects = len(dataset.project_ids)
    if expected_projects != 3:
        issue(
            "PROJECT_COUNT",
            "Project Register",
            "",
            f"exactly three reference projects are required, found {expected_projects}",
        )
    if len(set(dataset.project_ids)) != expected_projects:
        issue("PROJECT_DUPLICATE", "Project Register", "", "project ids are not unique")
    projects = set(dataset.project_ids)

    # Every sheet with a Project ID must reference a registered project.
    for name, sheet in dataset.sheets.items():
        for row in sheet.rows:
            project = _text(row.get("Project ID"))
            if project and project not in projects:
                issue(
                    "PROJECT_UNKNOWN",
                    name,
                    project,
                    f"Project ID {project!r} is not in the project register",
                )

    # References that must stay inside one project.
    def require_same_project(
        sheet: str,
        row: Mapping[str, Any],
        record_key: str,
        foreign: Mapping[str, Mapping[str, Any]],
        foreign_key: str,
        field_name: str,
    ) -> None:
        record = _text(row.get(record_key))
        value = _text(row.get(field_name))
        project = _text(row.get("Project ID"))
        if not value:
            issue(f"{field_name.upper().replace(' ', '_')}_MISSING", sheet, record, f"{field_name} is empty")
            return
        target = foreign.get(value)
        if target is None:
            issue(
                f"{field_name.upper().replace(' ', '_')}_UNKNOWN",
                sheet,
                record,
                f"{field_name} {value!r} does not exist in {foreign_key}",
            )
            return
        if _text(target.get("Project ID")) != project:
            issue(
                f"{field_name.upper().replace(' ', '_')}_PROJECT_MISMATCH",
                sheet,
                record,
                f"{field_name} {value!r} belongs to another project",
            )

    eps = _index(dataset.rows("EPS"), "EPS ID")
    obs = _index(dataset.rows("OBS"), "OBS ID")
    wbs = _index(dataset.rows("WBS"), "WBS ID")
    calendars = _index(dataset.rows("Calendars"), "Calendar ID")
    activities = _index(dataset.rows("Activities"), "Activity ID")
    # P6 models equipment as a resource, and this workbook keeps equipment in
    # its own register. Both registers feed the same resource index, so an
    # Equipment assignment resolves against the equipment register rather than
    # being reported as missing.
    resources = _index(dataset.rows("Resource Master"), "Resource ID")
    equipment = _index(dataset.rows("Equipment Register"), "Equipment ID")
    resource_index = {**equipment, **resources}
    baselines = _index(dataset.rows("Baselines"), "Baseline ID")

    for row in dataset.rows("WBS"):
        record = _text(row.get("WBS ID"))
        parent = _text(row.get("Parent WBS ID"))
        project = _text(row.get("Project ID"))
        if parent:
            if parent == record:
                issue("WBS_SELF_PARENT", "WBS", record, "a WBS node cannot be its own parent")
            else:
                target = wbs.get(parent)
                if target is None:
                    issue("WBS_PARENT_UNKNOWN", "WBS", record, f"parent {parent!r} does not exist")
                elif _text(target.get("Project ID")) != project:
                    issue("WBS_PARENT_PROJECT_MISMATCH", "WBS", record, "parent belongs to another project")
        if _text(row.get("EPS ID")):
            require_same_project("WBS", row, "WBS ID", eps, "EPS", "EPS ID")

    for row in dataset.rows("Activities"):
        record = _text(row.get("Activity ID"))
        require_same_project("Activities", row, "Activity ID", wbs, "WBS", "WBS ID")
        require_same_project("Activities", row, "Activity ID", calendars, "Calendars", "Calendar ID")
        if _text(row.get("Responsible OBS ID")):
            require_same_project("Activities", row, "Activity ID", obs, "OBS", "Responsible OBS ID")
        duration = _number(row.get("Original Duration Days"))
        if duration is None or duration < 0:
            issue("ACTIVITY_DURATION_INVALID", "Activities", record, "original duration must be a non-negative number")
        status = _text(row.get("Status"))
        if status and status not in ACTIVITY_STATUSES:
            issue("ACTIVITY_STATUS_INVALID", "Activities", record, f"status {status!r} is not a P6 activity status")

    for row in dataset.rows("Activity Relationships"):
        record = _text(row.get("Relationship ID"))
        require_same_project("Activity Relationships", row, "Relationship ID", activities, "Activities", "Predecessor ID")
        require_same_project("Activity Relationships", row, "Relationship ID", activities, "Activities", "Successor ID")
        relationship_type = _text(row.get("Relationship Type"))
        if relationship_type and relationship_type not in RELATIONSHIP_TYPES:
            issue(
                "RELATIONSHIP_TYPE_INVALID",
                "Activity Relationships",
                record,
                f"relationship type {relationship_type!r} is not FS/SS/FF/SF",
            )
        if _number(row.get("Lag")) is None:
            issue("RELATIONSHIP_LAG_INVALID", "Activity Relationships", record, "lag must be numeric")

    for row in dataset.rows("Resource Master"):
        record = _text(row.get("Resource ID"))
        require_same_project("Resource Master", row, "Resource ID", calendars, "Calendars", "Calendar ID")
        rate = _number(row.get("Standard Rate USD per h"))
        if rate is None or rate < 0:
            issue("RESOURCE_RATE_INVALID", "Resource Master", record, "standard rate must be a non-negative number")
        units = _number(row.get("Maximum Units"))
        if units is None or units <= 0:
            issue("RESOURCE_UNITS_INVALID", "Resource Master", record, "maximum units must be greater than zero")

    for row in dataset.rows("Equipment Register"):
        record = _text(row.get("Equipment ID"))
        require_same_project("Equipment Register", row, "Equipment ID", calendars, "Calendars", "Calendar ID")
        rate = _number(row.get("Hourly Rate USD"))
        if rate is None or rate < 0:
            issue("EQUIPMENT_RATE_INVALID", "Equipment Register", record, "hourly rate must be a non-negative number")

    for row in dataset.rows("Resource Assignments"):
        record = _text(row.get("Assignment ID"))
        require_same_project("Resource Assignments", row, "Assignment ID", activities, "Activities", "Activity ID")
        require_same_project(
            "Resource Assignments",
            row,
            "Assignment ID",
            resource_index,
            "Resource Master / Equipment Register",
            "Resource ID",
        )
        for field_name in ("Budgeted Units h", "Actual Units h", "Remaining Units h"):
            value = _number(row.get(field_name))
            if value is None or value < 0:
                issue("ASSIGNMENT_UNITS_INVALID", "Resource Assignments", record, f"{field_name} must be a non-negative number")

    for row in dataset.rows("Baseline Activities"):
        record = _text(row.get("Activity ID"))
        require_same_project("Baseline Activities", row, "Activity ID", activities, "Activities", "Activity ID")
        require_same_project("Baseline Activities", row, "Activity ID", baselines, "Baselines", "Baseline ID")

    for row in dataset.rows("Activity Progress"):
        require_same_project("Activity Progress", row, "Activity ID", activities, "Activities", "Activity ID")
        for field_name in ("Physical %", "Duration %", "Units %"):
            value = _number(row.get(field_name))
            if value is None or not 0 <= value <= 100:
                issue(
                    "PROGRESS_PERCENT_INVALID",
                    "Activity Progress",
                    _text(row.get("Activity ID")),
                    f"{field_name} must be between 0 and 100",
                )

    for project in dataset.project_ids:
        baselines_for_project = [
            row for row in dataset.rows("Baselines") if _text(row.get("Project ID")) == project
        ]
        if len(baselines_for_project) != 1:
            issue(
                "BASELINE_COUNT",
                "Baselines",
                project,
                f"expected exactly one immutable baseline, found {len(baselines_for_project)}",
            )

    issues.extend(_detect_cycles(dataset))
    issues.sort(key=lambda item: (item.sheet, item.record, item.code, item.detail))
    return issues


def _detect_cycles(dataset: ReferenceDataset) -> list[ImportIssue]:
    """Reject a relationship graph that contains a cycle (a schedule cannot run)."""

    issues: list[ImportIssue] = []
    for project in dataset.project_ids:
        edges: dict[str, set[str]] = {}
        for row in dataset.rows("Activity Relationships", project):
            predecessor = _text(row.get("Predecessor ID"))
            successor = _text(row.get("Successor ID"))
            if not predecessor or not successor or predecessor == successor:
                if predecessor and predecessor == successor:
                    issues.append(
                        ImportIssue(
                            "RELATIONSHIP_SELF_LOOP",
                            "error",
                            "Activity Relationships",
                            _text(row.get("Relationship ID")),
                            "an activity cannot be its own predecessor",
                        )
                    )
                continue
            edges.setdefault(predecessor, set()).add(successor)

        state: dict[str, int] = {}

        def visit(node: str, path: tuple[str, ...]) -> list[str] | None:
            if state.get(node) == 1:
                return path[path.index(node):] if node in path else path
            if state.get(node) == 2:
                return None
            state[node] = 1
            for successor in sorted(edges.get(node, ())):
                found = visit(successor, (*path, node))
                if found:
                    return found
            state[node] = 2
            return None

        for node in sorted(edges):
            cycle = visit(node, ())
            if cycle:
                trail = " → ".join((*cycle, cycle[0])) if cycle else node
                issues.append(
                    ImportIssue(
                        "RELATIONSHIP_CYCLE",
                        "error",
                        "Activity Relationships",
                        project,
                        f"relationship graph contains a cycle: {trail}",
                    )
                )
                break
    return issues


@dataclass
class ImportReport:
    dataset: ReferenceDataset
    issues: list[ImportIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ImportIssue]:
        return [item for item in self.issues if item.severity == "error"]

    @property
    def warnings(self) -> list[ImportIssue]:
        return [item for item in self.issues if item.severity != "error"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": CONTRACT_VERSION,
            "source": {
                "file": self.dataset.source.name,
                "sha256": self.dataset.source_sha256,
                "sheets": len(self.dataset.sheets),
                "projects": list(self.dataset.project_ids),
            },
            "ok": self.ok,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "counts": self.dataset.counts(),
            "issues": [item.as_dict() for item in self.issues],
        }


def build_report(path: str | Path) -> ImportReport:
    dataset = load_dataset(path)
    return ImportReport(dataset=dataset, issues=validate_dataset(dataset))
