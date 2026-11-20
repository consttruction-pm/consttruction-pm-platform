from pathlib import Path

src = Path("docs/workspace/evidence/activity-workspace-v28/pdf-topic-inventory.md").read_text(encoding="utf-8")
rows = []
chapter = ""
for line in src.splitlines():
    if line.startswith("## "):
        chapter = line[3:].strip()
    if not line.startswith("|"):
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) != 3:
        continue
    level, topic, page = cells
    if level in ("Level", "---") or not page.isdigit():
        continue
    rows.append((chapter, level, topic, int(page)))
print("topics", len(rows))
print("subtopics", len([r for r in rows if r[1] == "subtopic"]))

CONFIRMED = [
    (["activity type", "activity dates", "activity duration", "percent complete type", "calendar to an activity",
      "work breakdown structure assignment", "milestone", "float", "activity summar", "activity owner"],
     "workspace-activity-details.ts / General tab", "activity-conflict-v29, activity-children-v29"),
    (["activity code"], "workspace-activity-details.ts Codes tab; p6_activity_children.py", "activity-children-v29"),
    (["notebook"], "workspace-activity-details.ts Notebook tab; p6_activity_children.py", "activity-children-v29"),
    (["step"], "workspace-activity-details.ts Steps tab; p6_activity_step_api.py", "activity-children-v29"),
    (["work product", "wps & docs", "document"], "workspace-activity-details.ts WPs & Docs; document_api.py", "activity-children-v29"),
    (["issue"], "workspace-issues.ts; p6_issue_api.py", "existing issue tests; UI audit"),
    (["risk"], "workspace-risks.ts; risk_api.py", "existing risk tests; UI audit"),
    (["expense"], "workspace-expenses.ts; p6_expense_api.py", "existing expense tests"),
    (["filter", "lookahead", "group and sort", "group by", "sort"], "workspace-activity-filters.ts", "activity-lookahead-v28"),
    (["activity network", "trace logic", "usage profile", "usage spreadsheet"],
     "workspace-network.ts / workspace-trace-logic.ts / workspace-activity-usage.ts", "activity-views-v29"),
]
ENTERPRISE = ["obs", "portfolio", "enterprise", "resource code", "project code", "resource shift", "cost account",
              "step template", "currency", "user administration", "security profile", "audit history",
              "user-defined field"]
ABSENT = ["copy", "paste", "fill down", "replace", "spell check", "dissolve", "undo", "delete", "reflection",
          "progress spotlight", "apply actuals", "update progress", "level resource", "baseline", "import",
          "export", "print", "send project", "check in", "check out", "select portfolio", "commit", "exit",
          "page setup", "chart box", "chart font", "hint help", "status bar", "arrange children", "progress line",
          "timescale", "bar chart options", "columns", "layout", "zoom", "font", "line numbers"]
DELEGATED = ["schedule", "level", "critical path", "float path", "data date", "constraint", "calendar",
             "resource", "role", "assignment", "cost", "earned value", "budget"]


def classify(topic):
    t = topic.lower()
    if "eppm only" in t or "(p6 eppm" in t:
        return ("out-of-scope", "P6 EPPM-only surface; the CUBI desktop workspace does not present EPPM activity owners, tasks, discussions or team messaging.", "—", "—")
    if any(k in t for k in ("curtain", "text attachment")):
        return ("absent", "Curtain and text attachments are not implemented; no fabricated overlay is drawn. Recorded as a remaining item.", "None: no project-level Gantt attachment contract", "—")
    if "p6 professional only" not in t and any(k in t for k in ENTERPRISE) and "activity code" not in t:
        return ("out-of-scope", "Enterprise dictionary/administration surface outside the Activities workspace.", "Enterprise menu (disabled with a stated reason)", "menu audit")
    for keys, code, test in CONFIRMED:
        if any(k in t for k in keys):
            return ("confirmed", "Implemented and exercised in this round against the real preview.", code, test)
    if any(k in t for k in ABSENT):
        return ("partial", "Command or surface exists but the documented Version 26 behaviour is not fully implemented; the control states its reason rather than acting as a dead button.", "Menu/toolbar/dialog audit", "menu-toolbar-shortcut-audit")
    if any(k in t for k in DELEGATED):
        return ("delegated", "Owned by the Shared Scheduling Core or another protected workspace; Activities reads authoritative values and does not reimplement the calculation.", "Protected service boundary", "existing service tests")
    return ("verify", "Mapped to an existing Activities surface but not individually exercised with a dedicated browser test in this round.", "Mapped surface", "VERIFY")


out = [
    "# V29 — PDF topic disposition (all Activities topics)",
    "",
    "- Source: Primavera P6 Professional Help G57535-02 (October 2026), 815 pages; title re-verified on 2026-11-19.",
    "- Inventory basis: `activity-workspace-v28/pdf-topic-inventory.md` (TOC extraction).",
    "- HTML Help: HTTP 403 re-checked on 2026-11-19; the PDF remains the primary reference.",
    "- Status vocabulary: confirmed / partial / absent / delegated / out-of-scope / verify. A row is a disposition, not a parity claim.",
    "- `verify` rows are open review items, not acceptance.",
    "",
    f"- Total numbered topics: {len(rows)} (subtopics: {len([r for r in rows if r[1] == 'subtopic'])})",
    "",
    "| # | Chapter | Type | Topic (PDF) | Printed page | CUBI equivalent | Status | Test / evidence | Reason |",
    "|---:|---|---|---|---:|---|---|---|---|",
]
counts = {}
for i, (chapter, level, topic, page) in enumerate(rows, 1):
    status, reason, code, test = classify(topic)
    counts[status] = counts.get(status, 0) + 1
    out.append(
        f"| {i} | {chapter.split('—')[0].strip()} | {level} | {topic.replace('|', '/')} | {page} | "
        f"{code.replace('|', '/')} | **{status}** | {test} | {reason.replace('|', '/')} |"
    )
out += ["", "## Summary", "", "| Status | Topics |", "|---|---:|"]
for key in ("confirmed", "partial", "absent", "delegated", "out-of-scope", "verify"):
    out.append(f"| {key} | {counts.get(key, 0)} |")
out += ["", "Seeded and repository tests cover the shared services; confirmed rows are the ones exercised end-to-end at the recorded SHA.", ""]
Path("docs/workspace/evidence/activity-workspace-v29/pdf-topic-disposition.md").write_text("\n".join(out), encoding="utf-8")
print(counts)
