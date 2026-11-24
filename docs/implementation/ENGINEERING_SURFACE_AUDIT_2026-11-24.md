# CUBI Engineering — surface audit and next bounded work (2026-11-24)

Scope: audit the **existing** Engineering workspace before adding anything. This
is not a rebuild plan and it does not repeat Stage 0. No schema, migration,
account, session, owner identity or reference project was touched.

Base: `main` at `6220af27` (after Stage 1 dam merge `e938c619`).
Reference: P6 Professional V26 HTML Help
(`https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm`) and the V26
Professional user guide.

## What already exists (verified in source, not inferred)

| Surface | Implementation | Evidence |
|---|---|---|
| Desktop shell, menu bar, command menus, Alt access keys | `apps/web/src/workspace-desktop-shell.ts` | menu definitions + popup rendering at `workspace-desktop-shell.ts:760-800`; shell tests `workspace-desktop-shell.test.ts` |
| Two dockable tool rails + floating toolbars, per-user/per-project config, hide/show families, add/remove/move/reorder buttons, lock, custom toolbars, icon/text style | `workspace-toolbar-config.ts`, `workspace-toolbar-view.ts`, `workspace-toolbar-registry.ts` | `setFamilyRail`, `setFamilyVisible`, `moveButton`, `createCustomFamily`, `toolbarConfigStorageKey`; tests `workspace-toolbars.test.ts`, `workspace-toolbar-rails.test.ts` |
| Menubar commands that open real dialogs/windows | `workspace-desktop-shell.ts` command table | `dialog.bars`, `view.line-numbers`, layout/filter dialogs |
| Presentation model (table font/row/colours/icons/line numbers, bar styles, timescale, WBS bands, Gantt options, saved filters) | `workspace-presentation.ts` | `WorkspacePresentation`, `normalizePresentation`, `DEFAULT_PRESENTATION` |
| Activity grid, WBS register/chart, relationships, calendars, resources, assignments, roles, baselines, progress, cost, reports, tracking, issues, risks, thresholds, control, import/export, backup | `apps/web/src/workspace-*.ts` (~60 modules with matching `*.test.ts`) | module inventory; `workspace-navigation.ts` 21 groups |
| Schedule/CPM core, leveling, EVM, baseline immutability, Data Date, float paths | `src/construction_pm/scheduling/*`, `p6_baseline_*`, `p6_earned_value_*` | `docs/engineering/CORE_COMPLETION_EXECUTION_LEDGER.md` |
| RTL/LTR, nine-locale catalogs, Jalali/Gregorian input | `workspace-localization.ts`, locale catalogs, `parseJalaliDateInput` | main.ts create form and workspace labels |

Conclusion: Engineering is **not** an empty shell. Menus, toolbars (including
hide/show, customize and rail docking), WBS, activities, Gantt, calendars,
resources, baselines, reports and the calculation core already exist with tests.
The mission must continue from the real gaps below, not from a rebuild.

## Real gaps found in this audit

1. **Chrome visibility is missing.** `WorkspacePresentation` covers the table,
   bars, timescale, WBS, Gantt and filters, but not the title bar, menu bar,
   status bar or tool rails. P6 V26 lets the user hide/show these; CUBI currently
   cannot. This is the next bounded implementation.
2. **Menu/toolbar personalization is split.** Toolbars have a versioned,
   per-user/per-project configuration; menus have no equivalent customization
   (no hide/show of individual menus, no reset). P6 exposes a customizable menu
   bar; CUBI exposes a fixed one.
3. **No PDF visual comparison evidence.** The owner's 815-page V26 PDF is not
   present in `/mnt` or the workspace, so page count, images, colours, forms and
   control states could not be compared in this environment. The HTML Help
   baseline remains the only verified reference; this is a blocker for
   pixel-level parity claims, not for implementation.
4. **Several navigation groups are still labelled `preview`/`partial`**
   (`reports`, `tracking`, `risks`, `thresholds`, `administration`, `exchange`,
   `backup`). Each needs a page-by-page completion check against the V26 topic,
   not a new module.
5. **No live Preview target.** The canonical official URL still returns 404, so
   browser evidence for any change is produced locally (headless) only.

## Next bounded work (ordered)

1. Add `chrome` visibility to `WorkspacePresentation` (title bar, menu bar,
   status bar, left rail, right rail), with View-menu checkboxes, persistence in
   the saved layout, CSS, keyboard reachability and tests — including RTL.
2. Add menu-bar customization (hide/show a menu, reset) on the same persisted
   configuration pattern as toolbars.
3. Page-by-page completion of the `preview`/`partial` groups against the V26
   Help topics, one page per PR-sized increment with real data and tests.
4. Re-run the visual comparison when the owner's PDF is available in the
   workspace.

## Non-regression contract

- No change to passwords/hashes, accounts, roles, permissions, sessions, tenant
  membership, Personal Workbench, Global Administration, login/environment
  routes, or `CUBI-REF-001/002/003` and `CUBI-DAM-001`.
- No production database access or migration.
- No parallel project store, calculation engine or UI-side persisted math.
