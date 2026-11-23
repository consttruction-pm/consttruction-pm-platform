"""Deterministic shared in-progress dam + hydropower project bundle.

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

def _build_enterprise_records(
    activity_rows: list[dict[str, object]],
    leaf_ids: list[str],
    resource_master: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    """Build project-scoped Enterprise facts linked to the same Engineering IDs."""
    activity_ids = [str(row["activity_id"]) for row in activity_rows]
    obs_ids = ("OBS-DAM-PMO", "OBS-DAM-ENG", "OBS-DAM-COM")
    roles = (
        "Project Director", "Project Controls Manager", "Engineering Manager",
        "Construction Manager", "HSE Manager", "Quality Manager",
        "Procurement Manager", "Commercial Manager", "Document Controller",
        "Commissioning Manager", "Planning Engineer", "Cost Engineer",
    )
    organization = [
        {"organization_id": "DAM-ORG-OWNER", "organization_name": "Project Owner", "parent_organization_id": None, "department_head_role": "Project Director"},
        {"organization_id": "DAM-ORG-PMO", "organization_name": "Project Management Office", "parent_organization_id": "DAM-ORG-OWNER", "department_head_role": "Project Controls Manager"},
        {"organization_id": "DAM-ORG-ENG", "organization_name": "Engineering Directorate", "parent_organization_id": "DAM-ORG-PMO", "department_head_role": "Engineering Manager"},
        {"organization_id": "DAM-ORG-CON", "organization_name": "Construction Directorate", "parent_organization_id": "DAM-ORG-PMO", "department_head_role": "Construction Manager"},
        {"organization_id": "DAM-ORG-COM", "organization_name": "Commercial and Procurement", "parent_organization_id": "DAM-ORG-PMO", "department_head_role": "Commercial Manager"},
        {"organization_id": "DAM-ORG-COMM", "organization_name": "Commissioning and Operations", "parent_organization_id": "DAM-ORG-OWNER", "department_head_role": "Commissioning Manager"},
    ]
    project_teams = [
        {"team_id": f"DAM-TEAM-{index:02d}", "team_name": name, "organization_id": org, "team_lead_role": lead}
        for index, (name, org, lead) in enumerate((
            ("Project Controls", "DAM-ORG-PMO", "Project Controls Manager"),
            ("Engineering Design", "DAM-ORG-ENG", "Engineering Manager"),
            ("Civil Construction", "DAM-ORG-CON", "Construction Manager"),
            ("HSE and Quality", "DAM-ORG-CON", "HSE Manager"),
            ("Procurement and Contracts", "DAM-ORG-COM", "Procurement Manager"),
            ("Commissioning", "DAM-ORG-COMM", "Commissioning Manager"),
        ), start=1)
    ]
    responsibility_assignments = [
        {
            "responsibility_id": f"DAM-RACI-{index:03d}",
            "obs_id": obs_ids[index % len(obs_ids)],
            "role": role,
            "raci": ("A", "R", "C", "I")[index % 4],
            "responsibility": f"{role} accountability for {PACKAGES[index % len(PACKAGES)][1]}",
        }
        for index, role in enumerate(roles, start=1)
    ]
    vendors = [
        {"vendor_id": f"DAM-VEN-{index:02d}", "vendor_name": name, "specialization": spec, "country": country, "qualification_status": "Qualified" if index % 4 else "Under Review", "status": "active"}
        for index, (name, spec, country) in enumerate((
            ("HydroDesign Consortium", "Hydraulic engineering", "Germany"),
            ("GeoFoundations Ltd", "Geotechnical investigation", "Türkiye"),
            ("Concrete Systems Group", "Concrete technology", "Italy"),
            ("HeavyLift International", "Lifting equipment", "Netherlands"),
            ("TurbineWorks AG", "Hydro turbine packages", "Austria"),
            ("PowerGrid Solutions", "Switchyard and protection", "France"),
            ("RiverControl Engineering", "Diversion and gates", "Switzerland"),
            ("SurveyTech Services", "Survey and instrumentation", "Azerbaijan"),
            ("Industrial Piping Co", "Penstock and piping", "Türkiye"),
            ("Commissioning Partners", "Testing and commissioning", "United Kingdom"),
            ("EarthMove Contractors", "Earthworks and haulage", "Georgia"),
            ("QualityLab International", "Materials testing", "Germany"),
        ), start=1)
    ]
    contracts = [{
        "contract_id": "DAM-CON-EPC-001",
        "contract_name": "Main Dam and Hydropower EPC Contract",
        "contract_type": "EPC",
        "contractor": "Dam Infrastructure EPC Consortium",
        "contract_value_usd": "845000000",
        "currency": "USD",
        "effective_date": PROJECT_START.isoformat(),
        "planned_completion": _working_date(780).isoformat(),
        "status": "Active",
        "commercial_basis": "Lump sum with measured provisional items",
    }]
    contract_packages = [
        {
            "package_id": f"DAM-CP-{index:02d}",
            "contract_id": "DAM-CON-EPC-001",
            "package_name": title,
            "scope": f"Engineering, procurement and construction scope for {title.lower()}",
            "budget_usd": str(Decimal(42000000 + index * 3750000)),
            "status": "In Progress" if index < 5 else "Planned",
        }
        for index, (_, title) in enumerate(PACKAGES, start=1)
    ]
    procurement_register = [
        {
            "procurement_id": f"DAM-PR-{index:03d}",
            "package_id": f"DAM-CP-{((index - 1) % len(PACKAGES)) + 1:02d}",
            "description": description,
            "category": category,
            "quantity": str(1 + (index % 12)),
            "unit": unit,
            "budget_usd": str(Decimal(850000 + (index % 9) * 225000)),
            "required_on_site": _working_date(150 + index * 7).isoformat(),
            "procurement_status": ("Delivered" if index <= 6 else "Under Evaluation" if index % 4 == 0 else "In Progress"),
            "vendor_id": f"DAM-VEN-{((index - 1) % len(vendors)) + 1:02d}",
            "related_activity_id": activity_ids[(index * 11) % len(activity_ids)],
        }
        for index, (description, category, unit) in enumerate((
            ("Hydraulic gates and hoists", "Mechanical", "set"),
            ("Embedded steel liners", "Steelwork", "tonne"),
            ("Penstock steel plates", "Piping", "tonne"),
            ("Turbine runner assemblies", "Hydromechanical", "set"),
            ("Generator stator and rotor", "Electrical", "set"),
            ("Protection and control panels", "Electrical", "set"),
            ("Concrete batching equipment", "Plant", "set"),
            ("Instrumentation and monitoring", "Instrumentation", "lot"),
            ("Rock bolts and anchors", "Civil", "lot"),
            ("Waterproofing membrane", "Civil", "m2"),
            ("Power transformers", "Electrical", "unit"),
            ("Cable trays and power cables", "Electrical", "lot"),
            ("Cranes and lifting accessories", "Plant", "set"),
            ("Grouting materials", "Civil", "tonne"),
            ("Laboratory testing equipment", "Quality", "lot"),
            ("Ventilation and drainage systems", "Mechanical", "lot"),
            ("Fire detection and protection", "Safety", "lot"),
            ("Switchyard disconnectors", "Electrical", "set"),
            ("Construction dewatering pumps", "Plant", "unit"),
            ("Survey and monitoring instruments", "Instrumentation", "lot"),
            ("Concrete admixtures", "Materials", "tonne"),
            ("Spillway gate seals", "Mechanical", "set"),
            ("Penstock expansion joints", "Piping", "set"),
            ("Commissioning test equipment", "Commissioning", "lot"),
        ), start=1)
    ]
    change_requests = [
        {
            "change_request_id": f"DAM-CR-{index:03d}",
            "title": title,
            "description": f"Project change assessment for {title.lower()} with linked schedule and commercial impact review.",
            "reason": reason,
            "status": ("Approved" if index in {1, 2, 5} else "Under Review" if index % 3 else "Submitted"),
            "cost_impact_usd": str(Decimal((index - 7) * 185000)),
            "schedule_impact_days": (index % 9) - 3,
            "raised_by": roles[index % len(roles)],
            "date_raised": _working_date(110 + index * 9).isoformat(),
        }
        for index, (title, reason) in enumerate((
            ("Additional foundation grouting scope", "Geotechnical verification"),
            ("Spillway access platform revision", "Construction sequence optimization"),
            ("Penstock support detail update", "Interface coordination"),
            ("Temporary river monitoring extension", "Environmental permit condition"),
            ("Powerhouse crane rail adjustment", "Equipment vendor clarification"),
            ("Switchyard protection panel change", "Grid operator requirement"),
            ("Reservoir instrumentation expansion", "Dam safety review"),
            ("Concrete mix trial extension", "Quality assurance findings"),
            ("Access road drainage modification", "Site condition"),
            ("Commissioning sequence update", "Integrated testing requirement"),
            ("Additional survey control points", "Construction tolerance"),
            ("Temporary works design revision", "Safety review"),
        ), start=1)
    ]
    communication_log = [
        {
            "communication_id": f"DAM-COMM-{index:03d}",
            "subject": subject,
            "communication_type": ("RFI" if index % 3 == 0 else "Technical Query" if index % 3 == 1 else "Coordination Meeting"),
            "from_role": roles[index % len(roles)],
            "to_role": roles[(index + 3) % len(roles)],
            "communication_date": _working_date(75 + index * 5).isoformat(),
            "status": ("Closed" if index % 4 == 0 else "Open" if index % 4 == 1 else "Responded"),
            "summary": f"Recorded project coordination item concerning {subject.lower()}.",
        }
        for index, subject in enumerate((
            "River diversion interface", "Foundation treatment acceptance", "Concrete temperature controls",
            "Spillway gate vendor data", "Penstock anchor block design", "Turbine hall embedded parts",
            "Switchyard protection interface", "Reservoir clearing boundary", "HSE lifting plan review",
            "Powerhouse crane commissioning", "Grid synchronization requirements", "Dam instrumentation layout",
            "Temporary access road handover", "Quality dossier closeout", "Hydraulic model review",
            "Procurement delivery sequence", "Environmental monitoring results", "Commissioning energization permit",
            "Concrete pour sequence", "Geological mapping update", "Electrical cable routing", "Penstock welding procedure",
            "Gate hoist factory test", "Site survey control network",
        ), start=1)
    ]
    approval_records = [
        {
            "approval_id": f"DAM-APR-{index:03d}",
            "object_type": object_type,
            "object_id": object_id,
            "decision": ("Approved" if index % 4 in {0, 1} else "Pending Review"),
            "decision_date": _working_date(90 + index * 6).isoformat(),
            "approver_role": roles[(index + 2) % len(roles)],
            "comment": "Reviewed against current project controls and interface requirements.",
        }
        for index, (object_type, object_id) in enumerate(
            [("document", f"DAM-DOC-{i:03d}") for i in range(1, 13)]
            + [("change_request", f"DAM-CR-{i:03d}") for i in range(1, 7)]
            + [("procurement", f"DAM-PR-{i:03d}") for i in range(1, 7)],
            start=1,
        )
    ]
    forms_register = [
        {"form_id": f"DAM-FRM-{index:02d}", "form_name": name, "form_type": kind, "version": "1.0", "status": "active"}
        for index, (name, kind) in enumerate((
            ("Request for Information", "RFI"), ("Technical Submittal", "Submittal"),
            ("Inspection Request", "Inspection"), ("Material Approval Request", "Material"),
            ("Method Statement Review", "Method Statement"), ("Permit to Work", "HSE"),
            ("Non-Conformance Report", "Quality"), ("Site Instruction", "Instruction"),
            ("Change Request", "Commercial"), ("Progress Measurement", "Progress"),
            ("Equipment Handover", "Handover"), ("Commissioning Test Sheet", "Commissioning"),
        ), start=1)
    ]
    project_milestones = [
        {
            "milestone_id": f"DAM-MS-{index:03d}",
            "milestone_name": title,
            "activity_id": activity_ids[(index * 17) % len(activity_ids)],
            "baseline_date": _working_date(120 + index * 14).isoformat(),
            "forecast_date": _working_date(125 + index * 14).isoformat(),
            "milestone_status": ("Achieved" if index <= 4 else "At Risk" if index % 6 == 0 else "Forecast"),
        }
        for index, title in enumerate((
            "Design basis approved", "River diversion readiness", "Cofferdam closure",
            "Foundation excavation complete", "Foundation treatment accepted", "First concrete placement",
            "Dam crest level reached", "Spillway gates installed", "Intake structure complete",
            "Penstock hydrotest complete", "Turbine runner installation", "Generator alignment complete",
            "Switchyard energized", "First unit wet commissioning", "Reservoir impoundment authorization",
            "Unit 1 synchronization", "Unit 2 synchronization", "Reliability run complete",
            "Environmental restoration complete", "Performance test accepted", "Provisional handover",
            "Final documentation submitted", "Operational training complete", "Taking-over certificate",
        ), start=1)
    ]
    workflow_templates = [
        {"workflow_template_id": f"DAM-WF-{index:02d}", "template_name": name, "version": "1.0", "active": True, "steps": steps}
        for index, (name, steps) in enumerate((
            ("Engineering Submittal Review", "Submitted > Discipline Review > Project Controls > Project Manager Approval > Closed"),
            ("Procurement Approval", "Request > Technical Evaluation > Commercial Review > Approval > Purchase Order"),
            ("Change Control", "Raised > Impact Assessment > Review Board > Decision > Implementation"),
            ("Risk Response Review", "Identified > Response Planning > Owner Review > Accepted > Monitoring"),
            ("Document Transmittal", "Prepared > Checked > Approved > Issued > Acknowledged"),
            ("Site Inspection and Release", "Requested > HSE Review > Quality Inspection > Accepted > Released"),
        ), start=1)
    ]
    workflow_instances = [
        {
            "workflow_template_id": f"DAM-WF-{((index - 1) % len(workflow_templates)) + 1:02d}",
            "instance_id": f"DAM-WFI-{index:03d}",
            "object_type": ("document" if index <= 12 else "procurement" if index <= 24 else "change_request"),
            "object_id": f"DAM-DOC-{index:03d}" if index <= 12 else f"DAM-PR-{index - 12:03d}" if index <= 24 else f"DAM-CR-{index - 24:03d}",
            "status": ("completed" if index % 4 == 0 else "in_progress" if index % 4 == 1 else "pending"),
            "current_step": ("Project Manager Approval" if index % 3 == 0 else "Technical Review"),
            "initiated_at": _working_date(80 + index * 4).isoformat(),
            "due_date": _working_date(95 + index * 4).isoformat(),
        }
        for index in range(1, 37)
    ]
    timesheets = [
        {
            "timesheet_id": f"DAM-TS-{index:04d}",
            "resource_id": str(resource["resource_id"]),
            "week_ending": _working_date(150 + week * 7).isoformat(),
            "regular_hours": str(40 + (index % 5) * 4),
            "overtime_hours": str(index % 3 * 2),
            "approval_status": ("approved" if index % 4 else "submitted"),
        }
        for index, resource in enumerate(resource_master, start=1)
        for week in range(2)
    ]
    risk_register = []
    risk_responses = []
    risk_categories = ("schedule", "geotechnical", "procurement", "environmental", "quality", "HSE", "interface", "cost")
    risk_titles = (
        "Unexpected weak rock at foundation level", "River diversion flood event",
        "Long-lead turbine delivery delay", "Concrete thermal control exceedance",
        "Spillway gate interface mismatch", "Penstock weld repair rate increase",
        "Reservoir sediment management constraint", "Grid interconnection approval delay",
        "Access road disruption during wet season", "Foundation grout take above allowance",
        "Critical crane availability constraint", "Environmental permit monitoring non-compliance",
        "Powerhouse embedded parts late release", "Switchyard protection coordination gap",
        "Dam instrumentation procurement delay", "Commissioning water availability constraint",
        "High groundwater inflow in excavation", "Concrete aggregate source variability",
        "HSE lifting operation exposure", "Vendor documentation approval backlog",
        "Uncharted utility at access corridor", "Contractor productivity below target",
        "Penstock support settlement risk", "Emergency spillway test readiness",
    )
    for index, title in enumerate(risk_titles, start=1):
        probability = 2 + (index % 4)
        impact = 2 + ((index * 3) % 4)
        category = risk_categories[(index - 1) % len(risk_categories)]
        risk_id = f"DAM-RSK-{index:03d}"
        risk_register.append({
            "risk_id": risk_id,
            "risk_title": title,
            "category": category,
            "risk_level": "High" if probability * impact >= 16 else "Medium" if probability * impact >= 9 else "Low",
            "risk_score": probability * impact,
            "probability_1_5": probability,
            "impact_1_5": impact,
            "owner_obs_id": obs_ids[index % len(obs_ids)],
            "wbs_id": leaf_ids[(index * 2) % len(leaf_ids)],
        })
        risk_responses.append({
            "risk_id": risk_id,
            "response_id": f"DAM-RSP-{index:03d}",
            "response_strategy": ("mitigate" if index % 3 else "transfer"),
            "response_action": f"Implement and track mitigation actions for {title.lower()}.",
            "action_owner": roles[index % len(roles)],
            "due_date": _working_date(180 + index * 8).isoformat(),
            "status": ("in_progress" if index % 4 else "planned"),
        })
    issue_register = [
        {
            "issue_id": f"DAM-ISS-{index:03d}",
            "issue_title": title,
            "status": ("Open" if index % 4 == 0 else "In Progress" if index % 4 == 1 else "Resolved" if index % 4 == 2 else "Closed"),
            "priority": ("Critical" if index % 8 == 0 else "High" if index % 3 == 0 else "Medium" if index % 3 == 1 else "Low"),
            "owner_obs_id": obs_ids[index % len(obs_ids)],
            "date_raised": _working_date(90 + index * 5).isoformat(),
            "related_activity_id": activity_ids[(index * 13) % len(activity_ids)],
        }
        for index, title in enumerate((
            "Foundation survey benchmark discrepancy", "Spillway embedded plate tolerance query",
            "River diversion pump redundancy review", "Concrete pour temperature sensor fault",
            "Penstock support bolt material certificate gap", "Turbine vendor drawing interface conflict",
            "Switchyard relay coordination revision", "Access tunnel ventilation commissioning issue",
            "Reservoir clearing boundary clarification", "Cofferdam seepage monitoring alarm",
            "Powerhouse crane runway alignment correction", "Cable trench drainage detail conflict",
            "Gate hoist brake test witness requirement", "Grout mix trial report resubmission",
            "Dam gallery lighting classification review", "Generator stator shipment preservation",
            "Environmental turbidity threshold exceedance", "Quality dossier traceability gap",
            "Construction water supply interruption", "Grid operator protection settings comment",
            "Penstock weld NDT acceptance backlog", "Concrete aggregate moisture correction",
            "Temporary access road erosion repair", "Commissioning procedure hold point clarification",
            "Survey control point protection", "HSE lifting zone segregation finding",
            "Fire water pump test record discrepancy", "Vendor spare parts schedule alignment",
            "Reservoir instrumentation cable route conflict", "Final handover document index update",
        ), start=1)
    ]
    document_register = []
    document_revisions = []
    activity_documents = []
    document_titles = (
        "General arrangement drawing", "Hydraulic calculation report", "Geotechnical investigation report",
        "Concrete mix design submission", "Spillway gate fabrication drawing", "Penstock welding procedure",
        "Turbine technical data sheet", "Generator protection philosophy", "Environmental management plan",
        "HSE lifting plan", "Inspection and test plan", "Commissioning procedure",
        "Foundation treatment method statement", "Cofferdam stability calculation", "Switchyard single line diagram",
        "Reservoir instrumentation schedule", "Powerhouse embedded parts drawing", "Quality control dossier",
        "River diversion operation plan", "Electrical cable routing drawing", "Penstock hydrotest procedure",
        "Concrete thermal control report", "Vendor document register", "Mechanical completion checklist",
        "Dam safety monitoring plan", "Access road drainage drawing", "Gate hoist operation manual",
        "Grid synchronization procedure", "As-built survey control report", "Operations training plan",
        "Spillway hydraulic model report", "Turbine installation method statement",
        "Fire protection design report", "Emergency response procedure",
        "Environmental restoration plan", "Taking-over documentation index",
    )
    for index, title in enumerate(document_titles, start=1):
        document_id = f"DAM-DOC-{index:03d}"
        status = ("Approved" if index % 6 == 0 else "IFC" if index % 6 == 1 else "IFA" if index % 3 == 0 else "In Progress")
        current_revision = "B" if index % 3 == 0 else "A"
        document_register.append({
            "document_id": document_id,
            "document_title": title,
            "document_status": status,
            "current_revision": current_revision,
            "discipline": ("Civil" if index % 4 == 0 else "Mechanical" if index % 4 == 1 else "Electrical" if index % 4 == 2 else "Project Controls"),
            "originator": roles[index % len(roles)],
            "package_id": f"DAM-CP-{((index - 1) % len(PACKAGES)) + 1:02d}",
            "due_date": _working_date(140 + index * 6).isoformat(),
        })
        document_revisions.append({
            "document_id": document_id,
            "revision": "A",
            "revision_date": _working_date(95 + index * 4).isoformat(),
            "status": "Submitted",
            "submitted_by": roles[index % len(roles)],
        })
        if current_revision == "B":
            document_revisions.append({
                "document_id": document_id,
                "revision": "B",
                "revision_date": _working_date(115 + index * 4).isoformat(),
                "status": "Current",
                "submitted_by": roles[(index + 2) % len(roles)],
            })
        activity_documents.append({
            "document_id": document_id,
            "activity_id": activity_ids[(index * 19) % len(activity_ids)],
        })
    team_tasks = [
        {
            "team_task_id": f"DAM-TASK-{index:03d}",
            "task_title": title,
            "assigned_role": roles[index % len(roles)],
            "status": ("Completed" if index % 8 == 0 else "Blocked" if index % 7 == 0 else "In Progress" if index % 3 == 0 else "Open"),
            "related_activity_id": activity_ids[(index * 9) % len(activity_ids)],
            "due_date": _working_date(125 + index * 5).isoformat(),
        }
        for index, title in enumerate((
            "Close foundation geological model comments", "Review diversion gate vendor drawings",
            "Issue concrete thermal control method statement", "Verify powerhouse embedded plate survey",
            "Complete penstock support stress review", "Resolve turbine auxiliary interface register",
            "Prepare switchyard relay coordination study", "Close environmental permit action items",
            "Approve spillway gate factory inspection plan", "Review dam gallery drainage details",
            "Coordinate generator delivery and preservation", "Update integrated commissioning sequence",
            "Verify cofferdam instrumentation readings", "Complete access road handover inspection",
            "Issue procurement expediting report", "Review contractor monthly schedule narrative",
            "Close non-conformance report on concrete finish", "Confirm reservoir monitoring data interface",
            "Prepare grid synchronization readiness checklist", "Review lifting plan for powerhouse crane",
            "Update risk response owners and due dates", "Verify document transmittal register",
            "Complete quality dossier index reconciliation", "Coordinate temporary works removal plan",
            "Close penstock weld NDT documentation", "Prepare first impoundment readiness review",
            "Review vendor spare parts and maintenance list", "Update project cost forecast narrative",
            "Verify operations training attendance", "Prepare provisional handover punch list",
            "Close outstanding RFI responses", "Review updated foundation treatment quantities",
            "Coordinate switchyard energization permit", "Confirm turbine installation hold points",
            "Reconcile weekly progress measurement records", "Update procurement delivery constraints",
            "Review change request cost and schedule impact", "Complete emergency response drill record",
            "Issue commissioning procedure for Unit 1", "Verify dam safety instrumentation calibration",
            "Close environmental restoration work package", "Prepare monthly project controls dashboard",
            "Review contract package payment milestone", "Update interface action log",
            "Confirm quality surveillance coverage", "Prepare final documentation turnover matrix",
            "Close site access and traffic management actions", "Review resource forecast for next period",
        ), start=1)
    ]
    return {
        "organization": organization,
        "project_teams": project_teams,
        "responsibility_assignments": responsibility_assignments,
        "vendors": vendors,
        "vendor_register": vendors,
        "contracts": contracts,
        "contract_packages": contract_packages,
        "procurement_register": procurement_register,
        "change_requests": change_requests,
        "communication_log": communication_log,
        "approval_records": approval_records,
        "forms_register": forms_register,
        "project_milestones": project_milestones,
        "workflow_templates": workflow_templates,
        "workflow_instances": workflow_instances,
        "timesheets": timesheets,
        "risk_register": risk_register,
        "risk_responses": risk_responses,
        "issue_register": issue_register,
        "document_register": document_register,
        "document_revisions": document_revisions,
        "activity_documents": activity_documents,
        "team_tasks": team_tasks,
    }


def build_dam_reference_bundle() -> dict[str, object]:
    """Build a deterministic one-project import bundle with 720 activities."""
    project = {
        "project_id": PROJECT_ID,
        "project_name": PROJECT_NAME,
        "sector": "infrastructure",
        "contract_type": "EPC",
        "planned_start": PROJECT_START.isoformat(),
        "status_date": STATUS_DATE.isoformat(),
        "description": "Shared in-progress project workspace for CUBI Engineering and Enterprise build-out.",
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
        "budget_type": "Working project control budget — under development",
        "budget_amount_usd": str(sum(Decimal(row["baseline_budget_usd"]) for row in baseline_rows)),
        "cost_account_id": "DAM-CA-01",
    }]

    enterprise_records = _build_enterprise_records(activity_rows, leaf_ids, resource_master)

    entry = {
        **enterprise_records,
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
            "baseline_name": "Working Baseline — Initial Control Version",
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
            "classification": "SHARED_BUILD_PROJECT",
            "data_origin": "generated_structured_seed",
            "synthetic_source_data": True,
            "project_ids": [PROJECT_ID],
        },
        "projects": {PROJECT_ID: entry},
        "excluded": {"workbook": "not used; source records are generated in memory"},
    }
    return bundle

__all__ = ["PROJECT_ID", "PROJECT_NAME", "build_dam_reference_bundle"]
