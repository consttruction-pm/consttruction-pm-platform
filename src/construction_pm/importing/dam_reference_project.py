"""Deterministic synthetic dam + hydropower project bundle.

This creates structured in-memory import records; it does not retain an Excel
workbook or write to PostgreSQL. Persistence is delegated to the canonical
reference importer and shared scheduling engine.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal

from .reference_persistence import BUNDLE_CONTRACT

PROJECT_ID = "CUBI-DAM-001"
PROJECT_NAME = "Large Reservoir Dam and Hydropower Development"
STATUS_DATE = date(2026, 11, 22)
PROJECT_START = date(2026, 1, 5)

PACKAGES = (
    ("ENG", "Engineering, Surveys and Permits"),
    ("SITE", "Site Preparation and Access"),
    ("DIV", "River Diversion and Cofferdams"),
    ("ENV", "Reservoir Clearing and Environmental Mitigation"),
    ("FND", "Foundation Excavation and Treatment"),
    ("DAM", "Concrete Dam Body and Galleries"),
    ("SPW", "Spillway, Gates and Outlet Works"),
    ("INT", "Intake and Penstock Systems"),
    ("PWR", "Powerhouse Civil Works"),
    ("TUR", "Turbine Generator and Auxiliaries"),
    ("GRID", "Switchyard and Grid Interconnection"),
    ("COM", "Testing, Commissioning and Impoundment"),
)

def _working_date(offset: int) -> date:
    """Return a weekday date offset from the planned project start."""
    value = PROJECT_START
    remaining = max(0, offset)
    while remaining:
        value += timedelta(days=1)
        if value.weekday() < 5:
            remaining -= 1
    return value

def build_dam_reference_bundle() -> dict[str, object]:
    """Build a deterministic one-project import bundle with 720 activities."""
    project = {
        "project_id": PROJECT_ID,
        "project_name": PROJECT_NAME,
        "sector": "infrastructure",
        "contract_type": "EPC",
        "planned_start": PROJECT_START.isoformat(),
        "status_date": STATUS_DATE.isoformat(),
        "description": "Synthetic QA reference project; not an actual historical dam.",
    }
    settings = {
        "default_calendar_id": "DAM-CAL-5D",
        "time_zone": "Asia/Tehran",
        "default_rate_type": "Standard",
    }
    calendars = [
        {"calendar_id": "DAM-CAL-5D", "calendar_name": "Project 5-day calendar"},
        {"calendar_id": "DAM-CAL-6D", "calendar_name": "Civil works 6-day calendar"},
        {"calendar_id": "DAM-CAL-7D", "calendar_name": "Continuous operations 7-day calendar"},
    ]
    workweeks = []
    for calendar_id, working_days in (("DAM-CAL-5D", 5), ("DAM-CAL-6D", 6), ("DAM-CAL-7D", 7)):
        for weekday_index, weekday in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")):
            workweeks.append({
                "calendar_id": calendar_id,
                "weekday": weekday,
                "is_working_day": weekday_index < working_days,
            })

    eps = [{"eps_id": "EPS-DAM-INFRA", "eps_name": "Dam and Hydropower Capital Program"}]
    obs = [
        {"obs_id": "OBS-DAM-PMO", "obs_name": "Dam Project Management Office", "parent_obs_id": None},
        {"obs_id": "OBS-DAM-ENG", "obs_name": "Engineering and Construction Directorate", "parent_obs_id": "OBS-DAM-PMO"},
        {"obs_id": "OBS-DAM-COM", "obs_name": "Commissioning and Operations Directorate", "parent_obs_id": "OBS-DAM-PMO"},
    ]

    wbs = []
    leaf_ids = []
    leaf_package = {}
    for package_index, (code, title) in enumerate(PACKAGES, start=1):
        level1 = f"DAM-WBS-{code}"
        wbs.append({"wbs_id": level1, "parent_wbs_id": None, "eps_id": "EPS-DAM-INFRA", "wbs_code": f"{package_index:02d}", "wbs_name": title, "level": 1})
        for control_index in range(1, 4):
            level2 = f"{level1}-CA{control_index:02d}"
            wbs.append({"wbs_id": level2, "parent_wbs_id": level1, "eps_id": None, "wbs_code": f"{package_index:02d}.{control_index:02d}", "wbs_name": f"{title} — Control Account {control_index}", "level": 2})
            for work_index in range(1, 3):
                level3 = f"{level2}-WP{work_index:02d}"
                wbs.append({"wbs_id": level3, "parent_wbs_id": level2, "eps_id": None, "wbs_code": f"{package_index:02d}.{control_index:02d}.{work_index:02d}", "wbs_name": f"{title} — Work Package {work_index}", "level": 3})
                level4 = f"{level3}-SUB"
                wbs.append({"wbs_id": level4, "parent_wbs_id": level3, "eps_id": None, "wbs_code": f"{package_index:02d}.{control_index:02d}.{work_index:02d}.01", "wbs_name": f"{title} — Detailed Construction Scope", "level": 4})
                leaf_ids.append(level4)
                leaf_package[level4] = package_index - 1

    # 720 activities: ten detailed activities in each of 72 level-4 WBS leaves.
    activity_rows = []
    progress_rows = []
    baseline_rows = []
    activity_ids = []
    for leaf_index, leaf_id in enumerate(leaf_ids):
        package_index = leaf_package[leaf_id]
        package_code, package_title = PACKAGES[package_index]
        calendar_id = ("DAM-CAL-6D" if package_index in {1, 2, 4, 5, 6, 7, 8} else
                       "DAM-CAL-7D" if package_index in {9, 10, 11} else "DAM-CAL-5D")
        for local_index in range(10):
            global_index = len(activity_rows)
            activity_id = f"DAM-{global_index + 1:04d}"
            duration = 2 + ((global_index * 7 + package_index) % 14)
            if global_index < 36:
                status, physical = "Completed", 100.0
                actual_start = _working_date(global_index * 2)
                actual_finish = _working_date(global_index * 2 + duration)
                remaining = 0
            elif global_index < 90:
                status, physical = "In Progress", float(20 + (global_index % 7) * 10)
                actual_start = _working_date(210 + (global_index % 12))
                actual_finish = None
                remaining = max(1, int(duration * (100 - physical) / 100))
            else:
                status, physical = "Not Started", 0.0
                actual_start = None
                actual_finish = None
                remaining = duration
            activity_rows.append({
                "activity_id": activity_id,
                "activity_name": f"{package_title}: {('Engineering' if local_index < 3 else 'Procurement' if local_index < 5 else 'Construction' if local_index < 8 else 'Inspection and handover')} — Task {local_index + 1:02d}",
                "wbs_id": leaf_id,
                "original_duration_days": duration,
                "remaining_duration_days": remaining,
                "status": status,
                "physical": physical,
                "actual_start": None if actual_start is None else actual_start.isoformat(),
                "actual_finish": None if actual_finish is None else actual_finish.isoformat(),
                "calendar_id": calendar_id,
            })
            activity_ids.append(activity_id)
            budget = Decimal(25000 + (global_index % 19) * 7250)
            progress_rows.append({
                "activity_id": activity_id,
                "physical": physical,
                "duration": physical,
                "units": physical,
                "actual_units_h": str((Decimal(duration * 8) * Decimal(str(physical)) / Decimal(100)).quantize(Decimal("0.01"))),
                "actual_cost_usd": str((budget * Decimal(str(physical)) / Decimal(100)).quantize(Decimal("0.01"))),
            })
            baseline_start = _working_date(global_index * 2)
            baseline_finish = _working_date(global_index * 2 + duration)
            baseline_rows.append({
                "baseline_id": "DAM-BL-PRIMARY",
                "activity_id": activity_id,
                "baseline_start": baseline_start.isoformat(),
                "baseline_finish": baseline_finish.isoformat(),
                "baseline_budget_usd": str(budget),
            })

    relationships = []
    relationship_types = ("FS", "SS", "FF", "SF")
    # Intra-leaf chains. Every edge points forward, so the graph is acyclic.
    for leaf_id in leaf_ids:
        members = [row["activity_id"] for row in activity_rows if row["wbs_id"] == leaf_id]
        for position in range(1, len(members)):
            predecessor, successor = members[position - 1], members[position]
            relationships.append({
                "relationship_id": f"DAM-REL-{len(relationships) + 1:05d}",
                "predecessor_id": predecessor,
                "successor_id": successor,
                "relationship_type": relationship_types[(position - 1) % 4],
                "lag": 0 if position % 3 else 1,
            })
    # Link the detailed WBS leaves and package handoffs to create an integrated
    # project network while preserving a forward-only dependency graph.
    leaf_last = []
    leaf_first = []
    for leaf_id in leaf_ids:
        members = [row["activity_id"] for row in activity_rows if row["wbs_id"] == leaf_id]
        leaf_first.append(members[0])
        leaf_last.append(members[-1])
    for index in range(1, len(leaf_ids)):
        relationships.append({
            "relationship_id": f"DAM-REL-{len(relationships) + 1:05d}",
            "predecessor_id": leaf_last[index - 1],
            "successor_id": leaf_first[index],
            "relationship_type": "FS",
            "lag": 0,
        })
    for index in range(1, len(PACKAGES)):
        previous_leaf = (index * 6) - 2
        next_leaf = index * 6
        relationships.append({
            "relationship_id": f"DAM-REL-{len(relationships) + 1:05d}",
            "predecessor_id": leaf_last[previous_leaf],
            "successor_id": leaf_first[next_leaf],
            "relationship_type": "FS",
            "lag": 2,
        })

    labor_roles = (
        "Project Manager", "Planning Engineer", "Cost Engineer", "Civil Engineer",
        "Geotechnical Engineer", "Structural Engineer", "Hydraulic Engineer",
        "Electrical Engineer", "Mechanical Engineer", "Surveyor", "Geologist",
        "HSE Officer", "Quality Inspector", "Quantity Surveyor", "Procurement Engineer",
        "Document Controller", "Concrete Specialist", "Welding Inspector",
    )
    resource_master = []
    resource_rates = []
    resource_availability = []
    for index in range(72):
        resource_id = f"DAM-LAB-{index + 1:03d}"
        role = labor_roles[index % len(labor_roles)]
        calendar_id = "DAM-CAL-6D" if index % 3 else "DAM-CAL-5D"
        resource_master.append({
            "resource_id": resource_id,
            "resource_name": f"{role} — Crew {index + 1:02d}",
            "calendar_id": calendar_id,
            "maximum_units": "1",
            "unit": "h",
        })
        resource_rates.append({
            "resource_id": resource_id,
            "rate": str(18 + (index % 17) * 4),
            "currency": "USD",
            "effective_date": PROJECT_START.isoformat(),
        })
        resource_availability.append({
            "resource_id": resource_id,
            "available_units": "1",
            "period_start": PROJECT_START.isoformat(),
        })

    equipment_types = (
        ("Excavator", 145), ("Dump Truck", 95), ("Crawler Crane", 220),
        ("Concrete Batching Plant", 310), ("Transit Mixer", 110),
        ("Tunnel Boring Machine", 1850), ("Drilling Rig", 260),
        ("Grouting Plant", 175), ("Bulldozer", 135), ("Wheel Loader", 105),
        ("Mobile Crane", 190), ("Generator Set", 85),
    )
    equipment_register = []
    for index in range(48):
        kind, rate = equipment_types[index % len(equipment_types)]
        equipment_register.append({
            "equipment_id": f"DAM-EQP-{index + 1:03d}",
            "equipment_name": f"{kind} — Unit {index + 1:02d}",
            "calendar_id": "DAM-CAL-7D" if index % 4 == 0 else "DAM-CAL-6D",
            "hourly_rate_usd": str(rate + (index % 5) * 7),
        })
        resource_availability.append({
            "resource_id": f"DAM-EQP-{index + 1:03d}",
            "available_units": "1",
            "period_start": PROJECT_START.isoformat(),
        })

    assignments = []
    for index, activity_id in enumerate(activity_ids):
        row = activity_rows[index]
        duration_hours = Decimal(int(row["original_duration_days"]) * 8)
        progress = Decimal(str(row["physical"]))
        for kind, resource_id in (
            ("LAB", f"DAM-LAB-{index % 72 + 1:03d}"),
            ("EQP", f"DAM-EQP-{index % 48 + 1:03d}"),
        ):
            budgeted = duration_hours
            actual = (budgeted * progress / Decimal(100)).quantize(Decimal("0.01"))
            rate = Decimal(18 + (index % 17) * 4) if kind == "LAB" else Decimal(equipment_types[index % len(equipment_types)][1] + (index % 5) * 7)
            assignments.append({
                "assignment_id": f"DAM-ASG-{len(assignments) + 1:05d}",
                "activity_id": activity_id,
                "resource_id": resource_id,
                "budgeted_units_h": str(budgeted),
                "actual_units_h": str(actual),
                "remaining_units_h": str(max(Decimal(0), budgeted - actual)),
                "budgeted_cost_usd": str((budgeted * rate).quantize(Decimal("0.01"))),
                "actual_cost_usd": str((actual * rate).quantize(Decimal("0.01"))),
                "remaining_cost_usd": str(((budgeted - actual) * rate).quantize(Decimal("0.01"))),
            })

    cost_periods = []
    for month in range(1, 13):
        start = date(2026, month, 1)
        finish = date(2026, month, 28) if month == 2 else (
            date(2026, month, 30) if month in {4, 6, 9, 11} else date(2026, month, 31)
        )
        cost_periods.append({
            "period_id": f"2026-{month:02d}",
            "period_start": start.isoformat(),
            "period_finish": finish.isoformat(),
        })

    cost_accounts = [
        {"cost_account_id": f"DAM-CA-{index + 1:02d}", "cost_code": f"CAPEX-{index + 1:02d}", "cost_category": label}
        for index, (_, label) in enumerate(PACKAGES)
    ]
    project_budgets = [{
        "budget_id": "DAM-BUDGET-BASE",
        "budget_type": "Approved synthetic reference budget",
        "budget_amount_usd": str(sum(Decimal(row["baseline_budget_usd"]) for row in baseline_rows)),
        "cost_account_id": "DAM-CA-01",
    }]

    entry = {
        "revision": 1,
        "project": project,
        "settings": settings,
        "eps": eps,
        "obs": obs,
        "wbs": wbs,
        "activities": activity_rows,
        "activity_relationships": relationships,
        "calendars": calendars,
        "calendar_workweeks": workweeks,
        "activity_calendar_assignments": [
            {"activity_id": row["activity_id"], "calendar_id": row["calendar_id"]}
            for row in activity_rows
        ],
        "resource_master": resource_master,
        "equipment_register": equipment_register,
        "resource_rates": resource_rates,
        "resource_availability": resource_availability,
        "resource_assignments": assignments,
        "baselines": [{
            "baseline_id": "DAM-BL-PRIMARY",
            "baseline_name": "Approved Project Baseline — Synthetic",
            "snapshot_date": PROJECT_START.isoformat(),
        }],
        "baseline_activities": baseline_rows,
        "activity_progress": progress_rows,
        "cost_periods": cost_periods,
        "cost_accounts": cost_accounts,
        "project_budgets": project_budgets,
        "resource_roles": [
            {"role_id": f"DAM-ROLE-{i + 1:02d}", "role_name": name, "role_category": "Engineering and Construction"}
            for i, name in enumerate(labor_roles)
        ],
        "schedule_options": [{
            "data_date": STATUS_DATE.isoformat(),
            "critical_activity_definition": "Longest Path",
            "calculate_multiple_float_paths": True,
            "float_path_count": 10,
            "calendar_for_relationship_lag": "Predecessor",
            "use_expected_finish_dates": False,
        }],
        "activity_constraints": [],
        "calendar_exceptions": [],
        "resource_assignment_spreads": [],
        "activity_expenses": [],
        "expenses": [],
    }
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    bundle = {
        "contract": BUNDLE_CONTRACT,
        "source": {
            "file": "generated-in-memory-cubi-dam-reference",
            "sha256": hashlib.sha256(canonical).hexdigest(),
            "status_date": STATUS_DATE.isoformat(),
            "classification": "DEMO/SYNTHETIC",
            "project_ids": [PROJECT_ID],
        },
        "projects": {PROJECT_ID: entry},
        "excluded": {"workbook": "not used; source records are generated in memory"},
    }
    return bundle

__all__ = ["PROJECT_ID", "PROJECT_NAME", "build_dam_reference_bundle"]
