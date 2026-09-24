# Mobile Client Foundation

## Role
The Mobile Client is a first-class product client alongside Web and Desktop. It is optimized for field operations and rapid data capture rather than being a reduced copy of the desktop UI.

## Mandatory architecture
- Mobile consumes the same versioned API/Application contracts as Web and Desktop.
- Shared Domain/Calculation Core remains the single source of Scheduling/P6, Progress/EVM, Resource/Cost, duration, calendar and financial calculation semantics.
- Mobile must not implement an independent scheduling, progress, EVM, resource, cost, duration or calendar-calculation engine.
- ProjectContext, authorization, optimistic locking, idempotency, stable errors and audit/revision semantics apply equally to Mobile.
- Offline behavior is limited to explicitly supported workflows; synchronization and conflict handling are governed by shared application/API contracts.
- Persian/English and Jalali/Gregorian presentation are supported; calendar arithmetic remains in the Shared Core.

## Basic offline planning capability
Mobile must be capable of simple planning without depending on the Web client or Internet for approved offline workflows:
- Create/open a local project.
- Create and edit a simple WBS hierarchy.
- Create and edit activities.
- Define FS/SS/FF/SF relationships and lag/lead.
- Run Schedule/Recalculate using the portable Shared Scheduling Core semantics.
- View Start, Finish, Duration and applicable Float/Criticality results.
- Persist locally and queue changes for synchronization when connectivity returns.
- Apply the same ProjectContext, revision, idempotency and conflict rules during synchronization.

This is not an independent Mobile scheduling engine; it is the same authoritative scheduling implementation/semantics made portable for offline execution.

## Desktop standalone capability
Desktop is a standalone installed product. Core project operations and Shared Domain/Calculation Core execution must work without Web or Internet. Online connectivity is used for synchronization, remote collaboration, updates and other services that explicitly require connectivity.

## Initial field capabilities
- Authentication and permission-aware project selection.
- Mobile dashboard and assigned-work views.
- Activity/WBS lookup and progress entry.
- Daily site reports.
- Personnel attendance entry.
- Machinery status and breakdown reporting.
- Linking field reports to WBS/activities.
- Photo/document capture and upload where supported.
- RFI/Submittal and other field-document workflows where applicable.
- Notifications.
- Offline queue and synchronization for approved workflows.
- Voice input and AI Smart Guide integration through shared services/contracts.

## UX principle
Mobile workflows prioritize fast, low-friction field entry, readable status information, limited typing, camera/voice-assisted capture, and clear synchronization state. Mobile UI may differ from Web/Desktop while preserving identical business semantics.

## Completion gate
Mobile foundation is complete only when the Mobile client consumes the authoritative shared contracts, respects security/context/revision/idempotency rules, supports the approved field workflows, and passes applicable cross-client contract and parity regression tests.
