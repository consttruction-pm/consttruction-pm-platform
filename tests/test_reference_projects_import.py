from __future__ import annotations

from datetime import date

import pytest
from openpyxl import Workbook

from construction_pm.importing import build_report

PROJECTS = ("REF-1", "REF-2", "REF-3")


def _write(tmp_path, *, drop: str | None = None, activity_wbs: str | None = None,
           relationships: list[tuple[str, str]] | None = None,
           resources: list[tuple] | None = None,
           equipment: list[tuple] | None = None,
           projects: tuple[str, ...] = PROJECTS):
    workbook = Workbook()
    workbook.remove(workbook.active)

    def add(name: str, header: list[str], rows: list[tuple]) -> None:
        worksheet = workbook.create_sheet(name)
        worksheet.append(header)
        for row in rows:
            worksheet.append(row)

    add("Project Register",
        ["Project ID", "Project Name", "Target Budget USD", "Status Date"],
        [(pid, f"Project {pid}", 1_000, date(2026, 11, 22)) for pid in projects])
    add("Project Settings",
        ["Project ID", "Status Date", "Default Currency"],
        [(pid, date(2026, 11, 22), "USD") for pid in projects])
    add("EPS", ["EPS ID", "Project ID", "EPS Name", "Parent EPS ID"],
        [(f"{pid}-EPS", pid, "Root", None) for pid in projects])
    add("OBS", ["OBS ID", "Project ID", "OBS Name"],
        [(f"{pid}-OBS", pid, "Owner") for pid in projects])
    add("WBS", ["WBS ID", "Project ID", "Parent WBS ID", "EPS ID", "WBS Code", "WBS Name"],
        [(f"{pid}-WBS", pid, None, f"{pid}-EPS", "1", "Root") for pid in projects])
    add("Activities",
        ["Activity ID", "Project ID", "WBS ID", "Activity Name", "Original Duration Days",
         "Calendar ID", "Status", "Responsible OBS ID"],
        [
            (f"{pid}-A1", pid, activity_wbs if activity_wbs and pid == "REF-1" else f"{pid}-WBS",
             "First", 5, f"{pid}-CAL", "Not Started", f"{pid}-OBS")
            for pid in projects
        ] + [
            (f"{pid}-A2", pid, f"{pid}-WBS", "Second", 3, f"{pid}-CAL", "Not Started", f"{pid}-OBS")
            for pid in projects
        ])
    pairs = relationships or [(f"{pid}-A1", f"{pid}-A2") for pid in PROJECTS]
    add("Activity Relationships",
        ["Relationship ID", "Project ID", "Predecessor ID", "Successor ID",
         "Relationship Type", "Lag", "Lag Unit"],
        [(f"REL-{index}", predecessor.rsplit("-", 1)[0],
          predecessor, successor, "FS", 0, "Day")
         for index, (predecessor, successor) in enumerate(pairs)])
    add("Calendars", ["Calendar ID", "Project ID", "Calendar Name", "Work Hours per Day"],
        [(f"{pid}-CAL", pid, "Site", 8) for pid in PROJECTS])
    add("Calendar Workweeks",
        ["Calendar ID", "Weekday", "Is Working Day", "Start Time", "Finish Time", "Hours"],
        [(f"{pid}-CAL", "Monday", True, "08:00", "16:00", 8) for pid in PROJECTS])
    add("Resource Master",
        ["Resource ID", "Project ID", "Resource Name", "Resource Type", "Maximum Units",
         "Calendar ID", "Standard Rate USD per h"],
        resources or [(f"{pid}-H1", pid, "Engineer", "Labor", 1, f"{pid}-CAL", 50.0) for pid in PROJECTS])
    add("Equipment Register",
        ["Equipment ID", "Project ID", "Equipment Name", "Calendar ID", "Hourly Rate USD"],
        equipment if equipment is not None
        else [(f"{pid}-EQ1", pid, "Crane", f"{pid}-CAL", 60.0) for pid in PROJECTS])
    add("Resource Assignments",
        ["Assignment ID", "Project ID", "Activity ID", "Resource ID", "Assignment Type",
         "Budgeted Units h", "Actual Units h", "Remaining Units h"],
        [
            (f"ASG-{pid}-L", pid, f"{pid}-A1", f"{pid}-H1", "Labor", 80, 40, 40)
            for pid in PROJECTS
        ] + [
            (f"ASG-{pid}-E", pid, f"{pid}-A1", f"{pid}-EQ1", "Equipment", 24, 12, 12)
            for pid in PROJECTS
        ])
    add("Baselines",
        ["Baseline ID", "Project ID", "Baseline Name", "Immutable Snapshot"],
        [(f"{pid}-BL", pid, "Baseline", "YES") for pid in PROJECTS])
    add("Baseline Activities",
        ["Baseline ID", "Project ID", "Activity ID", "Baseline Start", "Baseline Finish"],
        [(f"{pid}-BL", pid, f"{pid}-A1", date(2025, 1, 6), date(2025, 1, 11)) for pid in PROJECTS])
    add("Activity Progress",
        ["Project ID", "Activity ID", "Status Date", "Physical %", "Duration %", "Units %"],
        [(pid, f"{pid}-A1", date(2026, 11, 22), 50, 50, 50) for pid in PROJECTS])
    add("Earned Value",
        ["Project ID", "Status Date", "BAC USD", "PV USD", "EV USD", "AC USD"],
        [(pid, date(2026, 11, 22), 1_000, 500, 400, 450) for pid in PROJECTS])

    if drop:
        del workbook[drop]

    path = tmp_path / "reference.xlsx"
    workbook.save(path)
    return path


def test_consistent_workbook_passes_with_per_project_counts(tmp_path):
    report = build_report(_write(tmp_path))
    assert report.ok, [issue.as_dict() for issue in report.errors]
    counts = report.dataset.counts()
    assert counts["Activities"]["projects"] == {project: 2 for project in PROJECTS}
    assert counts["Resource Assignments"]["projects"] == {project: 2 for project in PROJECTS}
    assert report.dataset.project_ids == PROJECTS


def test_missing_required_sheet_is_an_error(tmp_path):
    report = build_report(_write(tmp_path, drop="Calendars"))
    assert not report.ok
    assert "SHEET_MISSING" in {issue.code for issue in report.errors}


def test_activity_with_unknown_wbs_is_reported(tmp_path):
    report = build_report(_write(tmp_path, activity_wbs="REF-1-WBS-MISSING"))
    unknown = [issue for issue in report.errors if issue.code == "WBS_ID_UNKNOWN"]
    assert unknown and unknown[0].record == "REF-1-A1"


def test_relationship_cycle_is_rejected(tmp_path):
    pairs = [(f"{pid}-A1", f"{pid}-A2") for pid in PROJECTS]
    pairs[0] = ("REF-1-A1", "REF-1-A2")
    pairs.append(("REF-1-A2", "REF-1-A1"))
    report = build_report(_write(tmp_path, relationships=pairs))
    assert "RELATIONSHIP_CYCLE" in {issue.code for issue in report.errors}


def test_equipment_assignment_resolves_through_the_equipment_register(tmp_path):
    report = build_report(_write(tmp_path))
    assert not [issue for issue in report.errors if issue.code == "RESOURCE_ID_UNKNOWN"]

    without_equipment = build_report(_write(tmp_path, equipment=[]))
    unknown = [issue for issue in without_equipment.errors if issue.code == "RESOURCE_ID_UNKNOWN"]
    assert {issue.record for issue in unknown} == {"ASG-REF-1-E", "ASG-REF-2-E", "ASG-REF-3-E"}


def test_project_count_must_be_three(tmp_path):
    report = build_report(_write(tmp_path, projects=PROJECTS[:2]))
    assert "PROJECT_COUNT" in {issue.code for issue in report.errors}
