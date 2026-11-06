# Activity Window — Version 26 Column, Filter and Formula Parity Audit

Status: implementation acceptance contract; **not a completion certificate**.
Scope: Activity Table column selection, Activity filters, Activity user-defined fields/formula columns, and the Activity context menu. This is an internal engineering reference and must not be surfaced as product UI/help/branding.

## 1. Product-surface distinction that must be preserved

The Version 26 material describes two related but not identical surfaces:

- The P6 Professional Version 26 User Guide (January 2026) defines the desktop Activity Table's column and filter workflows, and its Activity UDF workflow.
- The P6 EPPM Version 26 Help and Release 26 REST reference explicitly say that Project **and Activity** UDFs support calculated formulas. However, the detailed Version 26 click-by-click formula-definition topic routes the user through **Project UDFs**, not Activity UDFs. The Professional guide's Activity UDF topic documents creating an Activity UDF by title and data type; it does not document an Activity formula editor.

Therefore CUBI must not conflate:
1. adding an existing field to the Activity layout;
2. creating a new Activity UDF with a typed, manually entered value;
3. defining a calculated Activity UDF/formula column.

The third capability is required for CUBI's accepted Activity formula-column scope, but its exact interaction must be validated against the EPPM Activity UDF behavior. The current Professional Activity UDF guide alone is not evidence that the desktop client exposes the Project UDF formula editor for Activity UDFs.

## 2. Activity Table columns — required behavior

### Version 26 interaction model

Entry points are **View > Columns** and **Layout Options > Columns**.

The Columns dialog contains two distinct collections:
- **Available Columns**: registered fields not currently selected for this Activity Table layout.
- **Selected Options**: fields currently displayed by the Activity Table.

Required operations:
- Select one Available Column and move it to Selected Options.
- Move all Available Columns at once.
- Select one Selected Option and remove it from the displayed table.
- Remove all currently displayed columns at once, while refusing to leave the table with zero columns.
- Reorder selected columns in both directions.
- Copy a column-display configuration from another Activity layout.
- **Apply** previews changes while keeping the dialog open; **OK** applies and closes; **Default** restores the default column configuration for this layout.
- Edit a column title, width, and alignment; restore its default title when needed.

### Semantics CUBI must preserve

- Hiding a column is presentation-only: retain its field and values so it can be shown again.
- Removing a column from Selected Options removes it from this layout and returns the existing field to Available Columns. It does not delete the UDF definition or its values.
- Deleting an actual UDF is a separate, privileged, destructive enterprise-data action; it must never be the meaning of a grid's Hide or Remove command.
- Custom display title is a layout override, not a rename of the underlying field definition.
- The active layout must persist selection, order, title, width and alignment through the existing revisioned layout contract.
- The field list is scope-aware: only Activity-subject fields belong in the Activity grid.
- Context-menu **Hide This Column** must call the same visibility/layout action as the in-window column manager.

### Current CUBI evidence / gaps

- Existing `renderP6FieldChooser` in `apps/web/src/workspace-view.ts` already renders Available/visible/hidden fields and supports Add, Show, Hide, Remove-from-layout, reorder, title override, width, alignment, pin/freeze, Undo/Redo and history restore.
- It is currently mounted inside the secondary Tools drawer and the Settings layout administration surface, not as the primary Activity-window Columns dialog/command.
- The context menu's Activity header/cell Hide This Column action is connected to the existing saved-layout visibility callback.
- The current layout model has a single `scope/view_id` current layout with revision history. A complete named-layout manager (multiple named layouts, New/Open/Save As/Rename/Delete/Import/Export, ownership/scopes, dirty state, copy-from) remains a separate acceptance item; do not simulate it with an unsaved select box.

## 3. Activity UDF creation — required behavior

### Version 26 Professional workflow

Create a field through **Enterprise > User Defined Fields**:
1. Select the **Activities** subject area.
2. Add a new field.
3. Enter its title/name and choose a data type.
4. Save the definition.
5. Add that Activity UDF to the Activity Table through the Available Columns list.
6. Populate its values in the Activity UDF column (subject to field edit and security permissions).

The Professional Version 26 data types documented for UDFs are Text, Start Date, Finish Date, Cost, Indicator, Number and Integer. UDFs are scoped to the subject area in which they were created. The documentation also supports grouping, sorting, filtering and reporting on UDFs. Indicator UDFs are not free-text/formula fields: their Activity values use the supported red/yellow/green/blue indicator set. Cost UDF visibility is governed by project-cost permissions. UDF creation/modification/deletion requires the relevant global UDF security privilege.

## 4. Formula columns — exact Version 26 boundary and CUBI requirement

### Verified Version 26 facts

- EPPM Version 26 Help says Activity and Project UDFs support custom formulas and graphical indicators based on calculations.
- The Release 26 REST UDFType contract exposes `SubjectArea` values including Activity, `Formula` (maximum 4000 characters), and `IsCalculated`.
- The detailed Version 26 formula-definition help page says to select a Formula-type UDF, open Formula details, pick fields from the Fields list, use Insert Field and operator controls to construct the expression, then Save. It explicitly describes the **Project UDFs** page; it also states that numeric offsets combined with a date are hours, and a value that cannot be calculated is represented as unavailable/locked on the Project page.
- The Professional Version 26 User Guide's Activity UDF creation section documents name/title plus data type and manual value entry. It does not document the same Activity formula-editor steps. This surface difference is intentional in this audit, not an assumption to paper over.

### CUBI Activity formula-column acceptance

CUBI's approved formula-column flow is a first-class Activity-window workflow, not the validation panel hidden in Tools:

1. **New Formula Column** action from Activity Columns/field manager.
2. Enter a unique field/column ID, visible title, optional description, Activity scope, and declared result data type; select unit where applicable.
3. Select Formula as the value source (distinct from a manual UDF and an Indicator UDF).
4. Build an expression using a searchable, typed Activity-field catalogue. Insert fields and supported operators/functions into the expression; show field IDs, data types and units. No fabricated fields.
5. Validate using the Shared/Core formula authority; return dependency list, inferred/declared result type, unit compatibility and precise diagnostics. Reject unknown fields, unsupported types, self-reference and cycles.
6. Preview calculated values against a representative set of permitted Activity rows before saving. Null/missing data, divide-by-zero and unavailable inputs must have explicit, consistent outcomes. A formula is never allowed to alter Activity source facts or silently recalculate CPM dates.
7. Save an immutable formula definition/version in the authenticated tenant/project scope, with audit actor/time/hash and semantic-engine version; the field metadata and layout reference must be persisted separately but transactionally linked.
8. Reload the project and show the exact same column definition/version and authoritative display values.
9. Support the field in Activity column selection, hide/show, title override, reorder, width/alignment, supported sorting/filtering, reports/export and formula dependency/version history.
10. Any formula edit creates a new immutable version. Existing saved layouts must resolve the intended version deterministically; failed validation or save must not create a half-defined column.

Formula semantics remain Shared/Core-owned. The browser may display authoritative cell values but must never call JavaScript `eval`, infer data types, calculate formula results locally, or write formula results into source Activity fields.

### Current CUBI evidence / gaps

- `p6-formula-panel.ts` is explicitly **validation-only**: its copy says validation does not save, recalculate or change activity dates. UI contains context field, expression and Validate only.
- `p6-formula-api.ts` calls the authoritative formula validation route; it does not persist a definition.
- `p6-formula-grid-binding.ts` requires an existing registry field and a field already present in the layout; it exposes setExpression/validate/applyAuthoritativeResult but does not create a field, persist a definition, calculate a row projection or restore a saved formula column.
- `workspace-model.ts:setP6Presentation` maps registry fields and sets every WorkspaceColumn's `formula` to `null`. The grid displays only values already projected into `activity.cells`.
- `addFormulaColumn` currently adds only a local WorkspaceColumn object after checking a non-empty expression and duplicate ID; it does not provide the accepted authoritative persistence/value lifecycle.
- Server-side `P6FormulaDefinitionAPI` and SQLite/Postgres repositories already persist immutable, scoped, versioned formula definitions and audit records. However, this API is not yet injected into `ProjectLifecycleHttpRoutes` / production composition, and the Activity grid does not consume persisted formula result projections.
- Thus a validated formula is **not yet** a working Activity formula column.

## 5. Activity filters — required Version 26 behavior

### Version 26 interaction model

The Activity filter workflow is not a single free-text search. It must provide a Filters/Customize dialog with:
- a named filter register (default, global, layout and user-defined categories where supported);
- New, edit, duplicate/copy, Delete (with privilege check), Apply/OK/Cancel;
- condition rows with **Parameter** (field), **Is** (operator/criteria) and **Value**;
- Add/Delete row and reorder criteria;
- multiple conditions in a filter and **All / Any** match mode;
- Apply to preview results without losing an edit in progress;
- selection checkboxes to apply/remove one or several saved filters;
- All Activities / clear-selection to remove the active filter restriction;
- Optimize action to identify/reduce redundant criteria;
- user-defined filters may be shared/global only by users with the required privilege.

Operators must be typed by field kind. At minimum include equality/inequality, text contains/prefix/suffix where semantically valid, empty/not-empty, comparisons and inclusive/exclusive ranges. Date/numeric range criteria must be distinct from ordinary equality. Duration and unit values preserve their specified units and use the applicable activity/resource calendar or configured hours-per-period rule. Do not compare duration fields as bare strings or convert a user-entered `2d` into an unqualified number.

Applying/removing a filter changes only the displayed row set. It never mutates activities, relationships, WBS, schedule dates or calculation facts.

### Current CUBI evidence / gaps

- The Activity toolbar currently has a token-based free-text search, WBS/None grouping and a single sort field/direction. It does not expose a named filter register or condition editor.
- `workspace-filter-sort.ts` performs a text contains-all-tokens search and sort/group projection.
- `p6-activity-wbs-grid.ts` has an early `P6GridFilter` shape, but only a limited operator set (equals/not-equals/contains/starts/ends/comparisons/empty); no criteria match mode, field-type-specific range semantics, named/persisted filter lifecycle, or demonstrated integration with the Activity window.
- P6 EPPM Release 26 REST reference also defines ActivityFilter create/read/update/delete endpoints and a filter object with name, criteria, criteria config, group/type and owner fields. CUBI currently has no equivalent connected Activity-filter persistence workflow.

## 6. Acceptance tests required before declaring parity

### ACT-COLUMNS
- Open Columns from the Activity window and from the context menu; same state and same saved layout.
- Add one field / add all; remove one / remove all; prevent zero visible columns.
- Hide then show; prove field definition and cell data remain intact.
- Rename title; restore original title; resize; align; reorder; Copy From layout; Apply preview; OK commit; Default reset.
- Reload and prove the same saved column set/order/presentation; stale revision conflict handled.
- Confirm deleting a UDF is a separate privileged destructive flow and never exposed as grid Remove.

### ACT-FILTERS
- Create named criteria filter; add/remove/reorder multiple conditions; All/Any behavior.
- Preview vs Apply; Apply several filters; clear one filter / All Activities; Delete user filter; deny Delete/Make Global without privilege.
- Verify date/numeric ranges, nulls, text operators, indicator values, units/durations and calendar-aware values.
- Prove filter affects visible rows only and does not modify schedule/project source data.
- Persist/reload filters in the correct scope with optimistic concurrency/audit.

### ACT-FORMULA-COLUMNS
- Create unique named Activity formula column with typed result/unit; reject invalid/duplicate field.
- Field insertion, allowed operator/function catalog, authoritative type/unit checks, dependency and cycle detection.
- Preview values; null/missing/divide-by-zero and unsupported-input behavior.
- Persist immutable version + audit; reload exact expression/version/dependencies; authoritative row values display.
- Formula columns support visibility, remove-from-layout, re-add, rename, order, width, alignment and permitted filtering/sorting/report use.
- Prove no browser formula evaluation and no mutation of source Activity facts or CPM calculation facts.

### ACT-CONTEXT
- Mouse right-click and ContextMenu/Shift+F10 for table header/cell/row, WBS, Gantt row/link and blank areas.
- Hide This Column routes through ACT-COLUMNS manager semantics; filter commands open ACT-FILTERS rather than only focusing a text box.
- Permission-aware actions, keyboard/focus restoration, Escape, outside-click dismissal, RTL and viewport-edge positioning.

## 7. Reference material reviewed

- P6 Professional User Guide Version 26 (January 2026), *Define Activity Table columns* and *Customize activity column titles*: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf
- P6 Professional Version 26, *Create a filter*: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/create_a_filter.htm
- P6 Professional Version 26, *Combine filters*: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/combine_filters.htm
- P6 Professional Version 26, *User-defined fields*: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/user_defined_fields.htm
- P6 Professional Version 26, *Define custom user fields*: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/define_custom_user_fields.htm
- P6 EPPM Help Version 26, *Working with User Defined Fields*: https://docs.oracle.com/cd/G48897_01/p6help/en/6656.htm
- P6 EPPM Help Version 26, *Defining Formulas for User Defined Fields*: https://docs.oracle.com/cd/G48897_01/p6help/en/7805.htm
- P6 EPPM REST API Release 26, *UDFType Fields*: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-ws-ref/udftypefields-42370a.html
- P6 EPPM REST API Release 26, *ActivityFilter*: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activityfilter-post.html



## 8. Mandatory visual specification — Activity Filters (Version 26)

This section is a **visual acceptance contract**, not optional styling guidance. The Activity filter must not ship as a generic web form, a floating list of chips, a side-panel with unrelated cards, or a single search box. The target is the compact, data-dense desktop interaction documented for P6 Professional Version 26. Use the official Version 26 PDF screenshot on printed page **288** (PDF zero-based page index 287) as the primary visual reference for the **Filter definition** dialog. Use the Version 26 Help page "Filters dialog box" (published July 16, 2026) for the selection/management dialog commands and semantics.

### 8.1 There are two distinct visual surfaces — do not merge them

**A. Filters / selection and management dialog**

This is the dialog opened through Activity > View > Filter By > Customize. It is where a user selects one or more saved filters, combines them, previews the result, returns to all activities, and manages saved filter definitions.

Required visible structure:
1. A top-level **All Activities** selection at the top of the filter list. Selecting it clears the filter restriction and restores all Activity rows.
2. A **Show activities that match** group with two mutually exclusive radio choices:
   - **All selected filters**
   - **Any selected filter**
3. A filter register grouped by filter category, not one undifferentiated chip cloud:
   - **Default**
   - **Global**
   - **Layout**
   - **User-Defined**
4. A proper list/table with filter name and a **Select** checkbox column. A filter can be selected without opening its definition. The Filter and Select column headings retain their sort affordance.
5. A lower **When applying the selected filter(s)** group with two mutually exclusive radio choices:
   - **Replace activities shown in current layout**
   - **Highlight activities in current layout which match criteria**
6. A command area with the actions that apply to the selected row/category and are enabled only when valid:
   - **OK**, **Cancel**, **Apply**, **New**, **Delete**, **Copy**, **Paste**, **Modify**, **Make Global**, **Copy as Layout**, **Help**.
   - **Apply** previews the chosen filter set and leaves this dialog open.
   - **Copy as Layout** creates a layout-scoped copy of a Default or Global definition; it is not the same as changing the current filter selection.
   - **Make Global** promotes an eligible layout/user definition to shared/global availability and requires the appropriate permission.
7. The filter name register must show the category/group relationship visually (tree/group header or equivalent compact grouped list). Do not represent Default/Global/Layout/User filters as independent large cards.
8. The dialog must keep a clear distinction between **Select/apply** and **Modify/edit**. Clicking a name to inspect it must not accidentally activate/deactivate it.

**B. Filter definition dialog**

This is the separate editor opened by New or Modify. Its baseline arrangement must follow the Version 26 screenshot:
1. A compact title bar and a **Filter Name** label with a single-line name input near the top.
2. A collapsible **Display: Filter** row immediately below the name line.
3. The main body is a grid/table occupying approximately four-fifths of the dialog width. A compact vertical command strip occupies approximately one-fifth at the right. Keep these relative proportions from the official screenshot; do not replace the grid with one form card per criterion.
4. The definition grid has the following column order and meaning:
   - **Display all rows** — logical connector for the criterion row: Where / And / Or.
   - **Parameter** — field/activity data item.
   - **Is** — operator / matching condition.
   - **Value** — primary comparison operand.
   - **High Value** — second operand for a between/range criterion.
5. The first group/header row displays **[All of the following]** or the corresponding any-match group mode. Criterion rows appear underneath with the connector in the first column; the first row begins with **Where** and subsequent rows use **And** or **Or** as selected. Preserve the indentation/tree-like grouping shown in the screenshot.
6. Keep the editor grid spacious enough to add rows without collapsing columns to tiny controls. Use aligned table headers, visible row boundaries, compact row heights, a selected-row highlight, and both vertical and horizontal scrolling when required. Do not truncate Parameter, Is, Value, or High Value so severely that users cannot inspect their criteria.
7. Double-clicking the **Is** cell opens the operator choices; selecting a Parameter opens the available Activity fields and supports type-ahead search. The Value/High Value cells are editable in-place and display values in the field's declared type/units.
8. The right-side command strip is vertically ordered as in the reference:
   - **OK** and **Cancel** at the top;
   - **Add** and **Delete**;
   - **Cut**, **Copy**, **Paste**;
   - criterion-order/group movement arrow controls (up/down and the available left/right hierarchy controls);
   - **Help** at the bottom.
   Use icon + readable label treatment like the reference, preserve disabled-state appearance, and do not hide the commands in an ellipsis menu.
9. The **Optimize** command is accessed from the Activity Display Options bar as documented. It is not an invented, permanently visible button inside every row. It reviews criteria to identify/reduce redundancy; it must not silently alter criteria without user confirmation.
10. OK commits the filter definition and closes the editor. Cancel closes without saving the unsaved draft. Add creates a new criterion row and places focus in its Parameter cell. Delete removes the selected criterion row, not the saved filter definition unless the user is in the manager dialog and explicitly chooses Delete.

### 8.2 Exact visual states that must be implemented and tested

The browser implementation must provide screenshot evidence for each of these states at the same Activity-window scale:
- Filters manager with the Default, Global, Layout and User-Defined groups expanded/collapsed as appropriate, including All Activities.
- Manager with one filter selected and with multiple filters selected.
- **All selected filters** and **Any selected filter** radio states.
- Replace vs Highlight application mode.
- New/Modify definition with one simple criterion (Where).
- Definition with multiple criteria and mixed Where / And / Or connectors.
- Definition with the **[All of the following]** group row and the corresponding any-match state.
- Range criterion showing both Value and High Value columns/cells.
- Empty/new filter before any criterion is added.
- Add-row and delete-selected-row states.
- Parameter type-ahead list open and the Is operator list open.
- Long text, date, numeric, duration and unit criterion values without clipping.
- Disabled Cut/Copy/Paste/move controls when no applicable selection exists; enabled state after a row is selected.
- Apply preview while the dialog remains open; Cancel discards the uncommitted filter-definition draft; OK saves and closes.
- All Activities restores the full set; unchecking a single Select checkbox removes only that filter.
- User without Global privilege cannot Make Global or delete/modify protected global definitions; a user without permitted ownership cannot edit/delete another user's definition.
- RTL Persian localization with the same column order, alignment, keyboard navigation and command hierarchy; RTL must not reverse the logical sequence of the columns or connector semantics.
- Narrow viewport behavior that preserves the dialog's action strip and permits grid horizontal scrolling; commands must not be pushed off-screen or overlap the grid.

### 8.3 Exact behavior that affects the appearance

- **Replace** mode removes nonmatching rows from the Activity Table display. **Highlight** mode retains all rows and visually marks only matches. These modes must look visibly different in the Activity grid and must be labeled as separate radio options in the manager dialog.
- Multiple saved filters are combined using All/Any at the **manager** level. Multiple criteria inside one filter use the row connectors and the criterion-group selector inside the **definition** dialog. These are separate controls and separate logic levels.
- The range operator exposes and uses both **Value** and **High Value**. For non-range operators, High Value is inactive/empty as appropriate; do not hide or repurpose the column only for a custom design.
- Relative date/time values such as **CD**, **CD+6w**, and **CF+6w** must remain recognizable strings/expressions in the Value/High Value cells and be resolved by the domain filter evaluator. They must not be parsed as ordinary date strings in the browser.
- Duration/unit criteria preserve entered units. For example, 2d remains two days rather than being converted to 16 hours. Calendar-aware filtering follows task-dependent global/project calendar or resource calendar semantics, and the configured hours-per-period rule when assigned-calendar conversion is disabled.
- A filter is a temporary view restriction/highlight. It does not modify Activity records, schedule dates, WBS, relationships, resource assignments, calculation facts or the source dataset.
- The UI must not show fake success or pretend that a filter has been saved if its persistence request fails. Keep a recoverable draft and show a specific validation/conflict message.
- Default filters are read-only templates. Copy a Default filter before editing its definition. Scope promotion, deletion and modification follow the authenticated permission model; protected built-in definitions must not expose active destructive commands.

### 8.4 Visual rejection criteria

Reject the implementation if any of the following appears:
- A generic search input is presented as the complete filter feature.
- One card per condition replaces the compact tabular definition grid.
- No dedicated Filter Name row or no Display: Filter section exists.
- The definition grid omits the Display all rows, Parameter, Is, Value or High Value columns.
- And/Or connectors are represented only as textual prose outside the rows.
- Add/Delete/Cut/Copy/Paste/movement commands are hidden in a three-dot menu or scattered elsewhere.
- Manager-level All/Any is incorrectly merged with criterion-level Where/And/Or logic.
- Replace and Highlight are collapsed into one behavior.
- No visual distinction exists between filter categories or between selected and unselected checkboxes.
- Dialog controls overlap, wrap unpredictably, clip values, lose focus on each criterion update, or cause the Activity window to jump/rescale.
- The filter editor is rendered only in the generic Tools drawer rather than as a first-class Activity-window dialog.

### 8.5 Official visual evidence reviewed

- **P6 Professional User Guide Version 26 (January 2026), printed page 288 / PDF page index 287:** screenshot of the Filter definition dialog. This is the primary visual baseline for the editor's title/name row, Display: Filter row, criterion grid, [All of the following] group, Where/And rows, Value/High Value columns, right-side command stack and Help.
  https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf
- **P6 Professional User Guide Version 26, printed pages 285–287:** filtering semantics, criteria connectors, creation, ranges, Optimize, applying/combining and duration/calendar notes.
  https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf
- **P6 Professional Help Version 26, Filters dialog box, last published July 16, 2026:** four filter categories, All Activities, All/Any saved-filter matching, Replace/Highlight modes, Apply, New/Delete/Copy/Paste/Modify/Make Global/Copy as Layout/Help semantics.
  https://docs.oracle.com/cd/G48902_01/client_help/en_US/filters_dialog_box.htm
- **P6 Professional Help Version 26, Create a lookahead filter:** type-ahead Parameter selection, High Value, relative date expressions and Replace/Highlight behavior.
  https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/create_a_lookahead_filter.htm

