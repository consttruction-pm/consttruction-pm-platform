# CUBI V1 Platform Execution Principles

Status: Binding architecture and delivery rule
Date recorded: 2026-11-03
Applies to: Web, Windows Desktop, Flutter Mobile (Android and iOS)

## 1. V1 client platforms

CUBI V1 has three first-class client surfaces:

1. **Web application** — browser-based, online-only.
2. **Windows Desktop application** — independently installed and fully usable offline for approved project workflows.
3. **Flutter Mobile application** — independently installed Android and iOS applications, fully usable offline for approved project workflows.

Flutter Mobile is part of V1. It is not a later phase, optional companion, Web wrapper, or deferred port. Every architecture plan, screen-design task, interaction specification, implementation plan, test plan, and release checklist must name Android and iOS explicitly.

## 2. One canonical application and calculation core

- Python owns the canonical domain behavior, validation, calculations, and application services.
- Web, Windows and Flutter invoke the same versioned application contracts and Shared Python Core.
- Windows embeds the approved Python runtime in its installed application.
- Flutter Android/iOS embeds the approved Python runtime and invokes it through a narrow, versioned native bridge (FFI or a justified platform channel).
- TypeScript, Dart, Swift, Kotlin and UI components may implement presentation, navigation, device integration and transport adapters only. They must not implement duplicate scheduling, calendar arithmetic, resource leveling, cost, progress, EVM or other domain rules.
- The versioned runtime ABI must not depend on WSGI, HTTP, browser state, Web UI packages or Internet access.

## 3. Platform execution model

### Web

- Web remains online-only.
- Authenticated Web APIs invoke the canonical server-side Python application/core.
- Browser storage and client caches are not authoritative project databases.
- No offline Web/PWA engine, Pyodide runtime or browser-authoritative SQLite database is part of this architecture.

### Windows Desktop and Flutter Mobile

- Both installed clients use local SQLite project persistence and durable attachment/file storage.
- Approved project work and canonical calculations continue without a Web server or Internet connection.
- Local project writes and outbox records commit atomically in the same database transaction.
- Pending operations survive process termination, restart and device restart.
- Reconnection enables authenticated delivery, acknowledgements and explicit conflict handling; it must never silently overwrite newer server state.
- Offline entitlement, trusted actor identity and secure storage are host responsibilities. Expired or unverifiable access fails closed for protected writes without deleting or stranding the user's local project data.

## 4. Flutter design is an initial V1 workstream

Flutter must receive its own mobile-first information architecture and interaction design before or alongside Web workspace implementation. A desktop screen compressed into a phone viewport is not an acceptable mobile design.

The Flutter design and implementation backlog must explicitly cover:

- Sign-in, offline unlock, session/entitlement state and recovery.
- Project list, create/open, project workspace and project settings.
- WBS tree, activity list, activity detail/edit, IDs/codes and bulk operations.
- Relationship and lag/lead editing, constraints and validation.
- Calendar selection, calendar definitions, work patterns, exceptions and inherited calendars.
- Resource/role views, assignments, periods, spreads, capacity and leveling inputs.
- Schedule/recalculate, timeline/Gantt navigation, critical/float views and baseline comparison.
- Cost accounts, expenses, progress/actuals and project-control reports.
- Import/export, file attachments, forms, report builder/reader and document workflows.
- Permissions, audit/revisions, pending sync queue, conflict resolution, backup/restore and undo/redo.

Touch layouts may reorganize dense workspace panels into mobile navigation, tabs, sheets and contextual editors. They must preserve the meaning and validation of domain fields, the same project model, role permissions, revisions, calendar semantics and canonical calculation results.

## 5. Shared project data and localization

- Windows and Flutter use the same logical local database schema, migration/version contract and outbox semantics; only platform file-system and secure-storage adapters may differ.
- Every project record is tenant/project scoped and protected by the same permission model and optimistic revision rules.
- Store canonical date/time values with explicit timezone semantics; Jalali/Gregorian and RTL/LTR are presentation and input-boundary concerns governed by explicit project/user settings.
- Platform-specific formatting must never change the underlying calculation facts or stored project dates.

## 6. Security and host boundary

- The trusted server/native host supplies authenticated identity, roles, entitlements, current revision, repositories and platform capabilities out-of-band.
- A JSON request from the UI cannot grant itself a user identity, role, permission, tenant, project or authoritative revision.
- All operations are allow-listed, versioned, scoped and permission-checked.
- Protected local writes must go through one transaction boundary that commits the domain mutation and outbox event together.

## 7. V1 completion and release gates

V1 is not complete when Web alone is complete. Delivery requires independent evidence for:

- Web online application using the shared Python services.
- Windows installation/runtime and offline operation with no system Python.
- Flutter Android and iOS installation/runtime, embedded Python bridge and offline operation with no Web login.
- Shared golden fixtures proving canonical calculation/result parity across server Python, Windows Python, Android Python and iOS Python.
- Device/OS tests for restart recovery, local storage integrity, migration/upgrade, interrupted writes, attachments, backup/restore, entitlement changes, and sync conflicts.

Typechecks, mocked bridges, screenshots and architecture-only issues do not replace real native runtime and device acceptance.
