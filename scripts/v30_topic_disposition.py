"""Generate the V30 PDF topic disposition from the V29 inventory.

Only rows whose behaviour changed in V30 are rewritten; every other V29
disposition is carried forward verbatim so the 264-topic baseline stays stable.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V29 = ROOT / "docs/workspace/evidence/activity-workspace-v29/pdf-topic-disposition.md"
V30 = ROOT / "docs/workspace/evidence/activity-workspace-v30/pdf-topic-disposition.md"

CONFIRMED = "**confirmed**"
ATTACHMENT_TITLES = [
    "Add a curtain attachment in a Gantt Chart",
    "Hide a curtain attachment in a Gantt Chart",
    "Add a text attachment to a Gantt Chart",
    "Remove a text attachment from a Gantt Chart",
    "Attach notebook items to bars in a Gantt Chart",
    "Hide all curtain attachments in the Gantt Chart",
    "Delete a curtain attachment from a Gantt Chart",
    "Display all curtain attachments in the Gantt Chart",
]
EDIT_TITLES = {
    "Delete an activity": "Delete is implemented end to end: a confirmation, an Activity Master DELETE with a record revision, a refusal when logic/children/assignments/documents exist, and a grid refresh. Proven in `activity-edit-v30` and `test_p6_activity_edit_commands.py`.",
    "Dissolve an activity": "Dissolve is implemented: it requires a predecessor and a successor, combines the predecessor's first half with the successor's second half, deletes the old links and the activity, and is refused when child records exist. Proven in `activity-edit-v30`.",
    "Copy and paste activities in the Activity Table": "Copy stores authoritative source IDs; Paste creates a new Activity Master row with a collision-free ID, starts it planned, copies codes/notebook/steps, and refreshes the grid. Proven in `activity-edit-v30`.",
    "Cut and paste activities in the Activity Table": "Cut uses the same clipboard, creates the pasted row first and only then deletes the source with its record revision. Proven in `activity-edit-v30`.",
}
BULK_LIMITED = {
    "Hide all curtain attachments in the Gantt Chart",
    "Display all curtain attachments in the Gantt Chart",
}


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def render(cells_in: list[str]) -> str:
    return "| " + " | ".join(cells_in) + " |"


def main() -> None:
    lines = V29.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    for line in lines:
        if line.startswith("# "):
            output.append("# V30 — PDF topic disposition (all Activities topics)")
            continue
        if line.startswith("- Source:"):
            output.append("- Source: Primavera P6 Professional Help G57535-02 (October 2026), 815 pages; PDF re-read on 2026-11-19.")
            continue
        if line.startswith("- HTML Help:"):
            output.append("- HTML Help: `https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-help/index.html` returned **HTTP 403** on 2026-11-19 with both the default client and a desktop Chrome user agent. No content was taken from it; the PDF remains the readable reference of the same edition.")
            continue
        if line.startswith("- Status vocabulary:"):
            output.append("- Status vocabulary: confirmed / partial / absent / delegated / out-of-scope / verify. A row is a disposition, not a parity claim. V30 rewrote only rows whose behaviour changed; all other V29 decisions are carried forward unchanged.")
            continue
        if not line.startswith("| ") or line.startswith("| # ") or line.startswith("|---"):
            output.append(line)
            continue
        values = cells(line)
        if len(values) < 9 or not values[0].isdigit():
            output.append(line)
            continue
        title = values[3]
        if title in EDIT_TITLES:
            values[5] = "workspace-activity-edit.ts / workspace-activity-clipboard.ts / p6_activity_master_api.py"
            values[6] = CONFIRMED
            values[7] = "activity-edit-v30, test_p6_activity_edit_commands.py"
            values[8] = EDIT_TITLES[title]
        elif title in ATTACHMENT_TITLES:
            values[5] = "workspace-gantt-attachments.ts / workspace-view.ts / p6_gantt_attachment.py"
            values[6] = "**partial**" if title in BULK_LIMITED else CONFIRMED
            values[7] = "gantt-attachments-v30, test_p6_gantt_attachment.py, test_gantt_attachment_http_routes.py"
            values[8] = (
                "Curtain, text and notebook links are persisted per project (kind, range, colour, label, visibility, "
                "activity/topic link, record revision), drawn in the real Gantt body/bar layer, hidden and shown, "
                "survive reload, edit under a revision guard and reject stale writes with 409. Notebook bodies stay in "
                "the Notebook tab; this row only links a topic to a bar."
                if title not in BULK_LIMITED
                else
                "Each curtain has a persisted visible flag and a Hide/Show action in the Attachments dialog; "
                "all visible curtains draw from their stored ranges. A single toolbar command that toggles every "
                "curtain at once is not implemented, so the bulk form of this topic stays partial."
            )
        output.append(render(values))

    # Recompute the summary from the rewritten rows.
    counts = {"confirmed": 0, "partial": 0, "absent": 0, "delegated": 0, "out-of-scope": 0, "verify": 0}
    for line in output:
        if not line.startswith("| ") or line.startswith("| # ") or line.startswith("|---"):
            continue
        values = cells(line)
        if len(values) < 7 or not values[0].isdigit():
            continue
        status = values[6].strip("* ")
        if status in counts:
            counts[status] += 1

    summary_index = output.index("## Summary") if "## Summary" in output else len(output)
    tail = output[summary_index:]
    rewritten_tail: list[str] = []
    for line in tail:
        if re.match(r"^\| (confirmed|partial|absent|delegated|out-of-scope|verify) \| \d+ \|$", line):
            status = line.strip("| ").split("|")[0].strip()
            rewritten_tail.append(f"| {status} | {counts[status]} |")
        else:
            rewritten_tail.append(line)
    output = output[:summary_index] + rewritten_tail

    output.insert(
        summary_index,
        "## V30 changes\n\n"
        "V30 completed the four edit commands that were `partial` in V29 (Delete, Dissolve, Copy/Paste and "
        "Cut/Paste in the Activity Table) and all eight Gantt attachment topics that were `absent`. "
        "The new evidence is `activity-edit-v30.json`, `gantt-attachments-v30.json`, "
        "`test_p6_activity_edit_commands.py`, `test_p6_gantt_attachment.py` and "
        "`test_gantt_attachment_http_routes.py`. Everything else keeps its V29 status; the remaining "
        "counts are reported below and listed in `remaining-items.md`.\n",
    )
    V30.parent.mkdir(parents=True, exist_ok=True)
    V30.write_text("\n".join(output) + "\n", encoding="utf-8")
    print("wrote", V30)
    print(counts)


if __name__ == "__main__":
    main()
