/**
 * CUBI visual command surface.
 *
 * This is presentation-only: commands are deliberately marked as shell
 * affordances until their owning workspace command/service is connected.
 * The menu catalogue is kept independent from API and calculation code.
 */
type MenuEntry = { label: string; description?: string; shortcut?: string; children?: MenuEntry[]; divider?: boolean; disabled?: boolean };
type MenuDefinition = { key: string; en: string; fa: string; entries: MenuEntry[] };

const menus: MenuDefinition[] = [
  { key: "file", en: "File", fa: "فایل", entries: [
    { label: "New Project", shortcut: "Ctrl+N" }, { label: "Open Project", shortcut: "Ctrl+O" }, { label: "Close Project" }, { label: "Close All Projects" },
    { divider: true, label: "" }, { label: "Save", shortcut: "Ctrl+S" }, { label: "Save All" }, { label: "Recent Projects", children: [{ label: "Recent project list" }, { label: "Clear recent list" }] },
    { divider: true, label: "" }, { label: "Import", children: [{ label: "Microsoft Project" }, { label: "Spreadsheet (XLSX)" }, { label: "Delimited text (CSV)" }, { label: "Project exchange package" }, { label: "Import layout" }] },
    { label: "Export", children: [{ label: "Spreadsheet (XLSX)" }, { label: "Delimited text (CSV)" }, { label: "PDF" }, { label: "Project exchange package" }, { label: "Export layout" }] },
    { divider: true, label: "" }, { label: "Print Preview", shortcut: "Ctrl+Shift+P" }, { label: "Page Setup" }, { label: "Print", shortcut: "Ctrl+P" },
    { label: "Backup Project" }, { label: "Restore Project" }, { label: "Workspace Backup / Restore" }, { divider: true, label: "" }, { label: "Sign Out" }, { label: "Exit Workspace" },
  ]},
  { key: "edit", en: "Edit", fa: "ویرایش", entries: [
    { label: "Undo", shortcut: "Ctrl+Z" }, { label: "Redo", shortcut: "Ctrl+Y" }, { divider: true, label: "" },
    { label: "Cut", shortcut: "Ctrl+X" }, { label: "Copy", shortcut: "Ctrl+C" }, { label: "Paste", shortcut: "Ctrl+V" }, { label: "Paste Special" }, { label: "Fill Down", shortcut: "Ctrl+D" },
    { label: "Add", shortcut: "Insert", children: [{ label: "Add Project" }, { label: "Add WBS" }, { label: "Add Activity" }, { label: "Add Relationship" }, { label: "Add Resource Assignment" }, { label: "Add Expense" }, { label: "Add Document" }, { label: "Add Issue" }, { label: "Add Risk" }] },
    { label: "Delete", shortcut: "Delete" }, { label: "Dissolve Activity" }, { label: "Link Activities", shortcut: "Ctrl+L" }, { label: "Unlink Activities" }, { label: "Renumber Activity IDs" },
    { label: "Assign", children: [{ label: "Resources" }, { label: "Roles" }, { label: "Activity Codes" }, { label: "Predecessors" }, { label: "Successors" }, { label: "Documents" }] },
    { divider: true, label: "" }, { label: "Find", shortcut: "Ctrl+F" }, { label: "Find Next", shortcut: "F3" }, { label: "Select All", shortcut: "Ctrl+A" }, { label: "User Preferences" },
  ]},
  { key: "view", en: "View", fa: "نمایش", entries: [
    { label: "Layout", children: [{ label: "New" }, { label: "Open" }, { label: "Save" }, { label: "Save As" }, { label: "Import Layout" }, { label: "Export Layout" }, { label: "Restore Default Layout" }] },
    { label: "Show on Top", children: [{ label: "Table" }, { label: "Gantt Chart" }, { label: "Activity Network" }, { label: "Resource Usage Spreadsheet" }, { label: "Activity Usage Spreadsheet" }, { label: "Profile" }, { label: "Chart" }] },
    { label: "Show on Bottom", children: [{ label: "Details" }, { label: "Activity Usage Profile" }, { label: "Resource Usage Profile" }, { label: "Trace Logic" }, { label: "None" }] },
    { label: "Bottom Layout Options" }, { label: "Columns" }, { label: "Filter By" }, { label: "Group and Sort By" }, { label: "Timescale" }, { label: "Bars" }, { label: "Bar Chart Options" },
    { label: "Progress Line" }, { label: "Progress Spotlight" }, { label: "Activity Critical Path" }, { label: "Check Schedule" }, { label: "Line Numbers" }, { label: "Attachments" },
    { label: "Table Font and Row" }, { label: "Chart Font and Colors" }, { label: "Chart Box Template" }, { label: "Arrange Children" }, { label: "Align Children" },
    { label: "Zoom", children: [{ label: "Zoom In" }, { label: "Zoom Out" }, { label: "Best Fit" }] }, { label: "Expand All" }, { label: "Collapse All" }, { label: "Collapse To" },
    { label: "Toolbars" }, { label: "Tab Groups" }, { label: "Full Screen" }, { label: "Theme / Appearance" },
  ]},
  { key: "project", en: "Project", fa: "پروژه", entries: [
    { label: "Activities" }, { label: "Additional Activities View" }, { label: "WBS" }, { label: "Resource Assignments" },
    { label: "Assign Baselines" }, { label: "Maintain Baselines" }, { label: "Expenses" }, { label: "Work Products and Documents" }, { label: "Thresholds" }, { label: "Issues" }, { label: "Risks" }, { label: "Set Default Project" },
    { divider: true, label: "" }, { label: "Project Details" }, { label: "Project Codes" }, { label: "Project Defaults" }, { label: "Project Calendars" }, { label: "Project Notebook" },
  ]},
  { key: "organization", en: "Organization", fa: "سازمان", entries: [
    { label: "Projects / Business Domains" }, { label: "Portfolios" }, { label: "Responsibility Structure" }, { label: "Resources" }, { label: "Roles" },
    { label: "Calendars", children: [{ label: "Global Calendars" }, { label: "Project Calendars" }, { label: "Resource Calendars" }, { label: "Working Hours and Shifts" }, { label: "Exceptions and Holidays" }] },
    { label: "Codes", children: [{ label: "Project Codes" }, { label: "Activity Codes" }, { label: "Resource Codes" }, { label: "Role Codes" }] },
    { label: "User Defined Fields" }, { label: "Resource Curves" }, { label: "Resource Shifts" }, { label: "Cost Accounts" }, { label: "Funding Sources" }, { label: "Currencies" }, { label: "Financial Period Calendars" },
  ]},
  { key: "tools", en: "Tools", fa: "ابزارها", entries: [
    { label: "Schedule", shortcut: "F9" }, { label: "Level Resources", shortcut: "Shift+F9" }, { label: "Apply Actuals" }, { label: "Update Progress" }, { label: "Recalculate Assignment Costs" },
    { label: "Summarize Projects" }, { label: "Store Period Performance" }, { label: "Global Change" }, { label: "Monitor Thresholds" }, { label: "Issue Navigator" },
    { label: "Reports", children: [{ label: "Reports" }, { label: "Report Groups" }, { label: "Report Batches" }, { label: "Run Report" }, { label: "Report Designer" }] },
    { label: "Form Builder", children: [{ label: "Open Form Builder" }, { label: "Organization Form Library" }, { label: "Project Form Library" }, { label: "Form Templates" }, { label: "Form Versions" }, { label: "Form Preview" }] },
    { label: "Smart Guide" }, { label: "Assistant" }, { label: "Global Search" },
  ]},
  { key: "administration", en: "Administration", fa: "مدیریت", entries: [
    { label: "Users" }, { label: "Teams and Membership" }, { label: "Access Profiles" }, { label: "Security Profiles" }, { label: "User Permissions" }, { label: "Admin Preferences" },
    { label: "Categories" }, { label: "Currencies" }, { label: "Financial Periods" }, { label: "Audit Log" }, { label: "System Defaults" },
  ]},
  { key: "help", en: "Help", fa: "راهنما", entries: [
    { label: "Workspace Guide" }, { label: "Context Help" }, { label: "Keyboard Shortcuts" }, { label: "What's New" }, { label: "Documentation Library" }, { label: "About CUBI" },
  ]},
];

const toolbarGroups = [
  { en: "Standard", fa: "عمومی", items: ["New", "Open", "Save", "Undo", "Redo", "Print", "Find"] },
  { en: "Project", fa: "پروژه", items: ["Add", "Delete", "WBS", "Activities", "Resources", "Assignments", "Baselines"] },
  { en: "Layout", fa: "چیدمان", items: ["Open Layout", "Save Layout", "Columns", "Filter", "Group / Sort", "Timescale", "Bars"] },
  { en: "Schedule", fa: "زمان‌بندی", items: ["Schedule", "Level Resources", "Progress Line", "Critical Path", "Trace Logic"] },
  { en: "CUBI Tools", fa: "ابزارهای کوبی", items: ["Form Builder", "Smart Guide", "Assistant", "Reports", "Theme"] },
];

function esc(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);
}

function renderEntry(entry: MenuEntry, locale: string): string {
  if (entry.divider) return '<li class="cubi-command-divider" role="separator"></li>';
  const label = locale === "fa" ? (entry.label) : entry.label;
  const shortcut = entry.shortcut ? `<kbd>${esc(entry.shortcut)}</kbd>` : "";
  if (entry.children?.length) return `<li class="cubi-command-parent"><details><summary>${esc(label)}<span class="cubi-submenu-caret">›</span></summary><ul role="group">${entry.children.map((child) => renderEntry(child, locale)).join("")}</ul></details></li>`;
  return `<li><button type="button" data-shell-command="${esc(entry.label)}" aria-disabled="true" title="Visual shell item; command wiring is a later phase">${esc(label)}${shortcut}</button></li>`;
}

export function renderWorkspaceCommandShell(locale: string): string {
  const isFa = locale === "fa";
  const menuMarkup = menus.map((menu) => `<li class="cubi-menu-root"><details><summary>${isFa ? menu.fa : menu.en}</summary><ul class="cubi-menu-popup" role="menu" aria-label="${isFa ? menu.fa : menu.en}">${menu.entries.map((entry) => renderEntry(entry, locale)).join("")}</ul></details></li>`).join("");
  const toolbar = toolbarGroups.map((group) => `<section class="cubi-toolbar-group"><strong>${isFa ? group.fa : group.en}</strong><div>${group.items.map((item) => `<button type="button" data-shell-command="${esc(item)}" aria-disabled="true" title="Visual shell item; command wiring is a later phase">${esc(item)}</button>`).join("")}</div></section>`).join("");
  return `<style>
  .cubi-command-shell{position:relative;z-index:12;background:#f7f9fc;border-bottom:1px solid #aebdce;color:#172b43;font:12px Inter,Vazirmatn, sans-serif}
  .cubi-command-menubar{display:flex;align-items:center;gap:2px;min-height:30px;padding:2px 8px;border-bottom:1px solid #d7dee8;background:#edf2f8;list-style:none;margin:0}
  .cubi-menu-root{position:relative}.cubi-menu-root>details>summary{list-style:none;cursor:pointer;padding:6px 10px;border:1px solid transparent;border-radius:3px;font-weight:600}.cubi-menu-root>details>summary::-webkit-details-marker{display:none}
  .cubi-menu-root>details[open]>summary,.cubi-menu-root>details>summary:hover{background:#fff;border-color:#b8c6d8;color:#123a6b}
  .cubi-menu-popup,.cubi-command-parent ul{list-style:none;margin:0;padding:4px;min-width:230px;background:#fff;border:1px solid #b8c6d8;box-shadow:0 8px 22px #14253b2b}
  .cubi-menu-popup{position:absolute;top:100%;inset-inline-start:0;max-height:min(70vh,560px);overflow:auto}
  .cubi-menu-popup li button,.cubi-command-parent summary{display:flex;align-items:center;justify-content:space-between;gap:22px;width:100%;border:0;background:transparent;color:#24384f;text-align:start;padding:6px 9px;border-radius:2px;font:inherit;cursor:pointer}
  .cubi-menu-popup li button[aria-disabled=true]{opacity:.82}.cubi-menu-popup li button:hover,.cubi-command-parent summary:hover{background:#e8eff8}
  .cubi-menu-popup kbd{font:10px Inter, sans-serif;color:#69798c}.cubi-command-divider{height:1px;background:#e1e6ed;margin:4px 3px}
  .cubi-command-parent{position:relative}.cubi-command-parent ul{display:none;position:absolute;top:0;inset-inline-start:100%;max-height:60vh;overflow:auto}.cubi-command-parent details[open]>ul{display:block}
  .cubi-submenu-caret{margin-inline-start:auto;color:#73849a}
  .cubi-toolbar{display:flex;align-items:stretch;gap:0;overflow-x:auto;padding:3px 6px;background:#f8fafc}
  .cubi-toolbar-group{display:flex;flex-direction:column;gap:3px;padding:2px 9px;border-inline-end:1px solid #d8e0e9;white-space:nowrap}
  .cubi-toolbar-group>strong{font-size:9px;color:#69798c;font-weight:600;text-align:center}.cubi-toolbar-group>div{display:flex;gap:3px}
  .cubi-toolbar-group button{border:1px solid #d5dde7;border-radius:3px;background:#fff;padding:5px 7px;color:#23405e;font:11px Inter,Vazirmatn,sans-serif}
  .cubi-toolbar-group button[aria-disabled=true]{opacity:.78}
  [dir=rtl] .cubi-command-menubar{flex-direction:row-reverse}
  @media(max-width:720px){.cubi-command-menubar{overflow-x:auto}.cubi-menu-popup{position:fixed;top:auto;inset-inline-start:8px;max-width:calc(100vw - 24px)}.cubi-toolbar-group{padding-inline:6px}}
  </style>
  <div class="cubi-command-shell" dir="${isFa ? "rtl" : "ltr"}" aria-label="${isFa ? "نوار فرمان محیط کار" : "Workspace command surface"}">
    <ul class="cubi-command-menubar" role="menubar">${menuMarkup}</ul>
    <div class="cubi-toolbar" role="toolbar" aria-label="${isFa ? "نوار ابزار اصلی" : "Main toolbar"}">${toolbar}</div>
  </div>`;
}
