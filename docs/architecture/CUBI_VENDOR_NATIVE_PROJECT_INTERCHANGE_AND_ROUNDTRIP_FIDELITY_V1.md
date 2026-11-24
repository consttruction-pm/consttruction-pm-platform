# CUBI Vendor-Native Project Interchange and Round-Trip Fidelity Standard

**Status:** Owner-approved architecture and acceptance standard; implementation and vendor certification are not implied.  
**Decision date:** 2026-11-24  
**Tracking issue:** #2136  
**Related work:** #389, #393, #1227, #1799, #2131

## 1. Purpose and governing rule

CUBI shall support loss-aware, versioned interchange with Primavera P6 and Microsoft Project while preserving the project schedule, selected calendars, relationships, resources, assignments and baselines. This is a data-integrity requirement, not a file-extension feature.

There are two complementary layers:

1. **CUBI Native Project Package** — canonical, complete, versioned CUBI transfer container. It is the authoritative lossless format for CUBI-owned data, including objects that external products do not model.
2. **Vendor-native adapters** — genuine P6 and Microsoft Project formats, with explicit versioned mappings and compatibility reports. An external format can only preserve the subset its schema and target application support. Unsupported semantics must never be silently discarded or represented as fully lossless.

One canonical project domain model, one shared scheduling/calendar/calculation core and one typed interchange boundary are mandatory. Import/export adapters do not calculate schedules and do not introduce a parallel scheduler, calendar engine, resource engine or field registry.

## 2. Required file formats

| Product | Required format | Additional format | Important boundary |
|---|---|---|---|
| Primavera P6 | XER | Primavera P6 XML | Both must be real files accepted by the named P6 version. XER and XML are separately audited; success in one does not certify the other. |
| Microsoft Project | MSPDI / Microsoft Project XML | MPP | MPP requires a real, versioned and tested compatible conversion path. XML support does not imply MPP support. |
| CUBI | CUBI Native Project Package | — | The only format intended to preserve all CUBI-native semantics without external-model limitations. |

A file must not be given a vendor extension unless it conforms to that vendor's actual format. In particular, XML must not be renamed to .mpp, and a generic ZIP/CSV must not be presented as XER or P6 XML.

## 3. Primavera P6 export contract

Export real P6 XER and P6 XML using the target application's applicable format/schema version. Preserve all data supported by that exact version, including:

- project identity and metadata, EPS, WBS hierarchy, activity IDs/codes and ordering;
- activity types, durations, dates, actuals, remaining work, status, progress, constraints and deadlines;
- all supported relationship types (FS, SS, FF, SF), lag and external-project references;
- selected/default project calendar, plus all referenced activity and resource calendars;
- calendar workweek, daily work periods, nonworking time, exceptions, holidays, shifts, hours-per-day/week/month/year and calendar assignments;
- labor, nonlabor, material and cost resources, resource codes, rates, availability, resource calendars, assignments, units, curves, spreads and costs;
- all selected baselines and baseline identity/association and values to the extent the audited format/version supports them;
- scheduling options, date/time precision, timezone policy, codes, UDFs and supported custom fields.

The selected project calendar must remain selected after export and reopen. Saving only its name, or substituting a global default, is not sufficient.

Baselines must remain baseline objects/snapshots. They must not be flattened into current activity dates or regenerated from the current schedule. If a specific XER/XML version or export path cannot carry a baseline object or some baseline values, the compatibility report must identify the exact limitation before export. The export must not be labelled full-fidelity.

Vendor acceptance requires opening the generated file in the named P6 version, inspecting the relevant project/calendar/baseline/resource/link records, saving and reopening it, and comparing semantics.

## 4. Microsoft Project export contract

### 4.1 MSPDI XML

Export genuine Microsoft Project XML (MSPDI) conforming to the supported target version. Preserve, where representable:

- project options, project start and project calendar/working-time settings;
- task and summary hierarchy, stable IDs, task IDs, outline levels and WBS mapping;
- task types, durations, work, dates, constraints, deadlines, status and progress;
- dependency types and lag, including supported cross-project links;
- base, task and resource calendars, work weeks, exceptions, shifts and assignment-calendar semantics;
- work/resource/material/cost resources, rates, availability, assignments, units, work, costs and timephased values;
- all supported baseline slots (Baseline and numbered baselines), including task/resource/assignment baseline values where the schema/version supports them;
- supported custom fields, codes, notes and metadata.

### 4.2 MPP

MPP import/export is a separate capability. It may be offered only through a real, versioned, tested Microsoft Project-compatible conversion path. Do not implement a fake MPP writer, rename XML to MPP, or infer MPP compatibility from MSPDI XML parsing.

For each supported Microsoft Project version, reopen the MPP output in the actual application and verify calendars, baselines, task links, resource calendars and assignments.

## 5. Mandatory import audit into CUBI

Audit P6 XER, P6 XML, MSPDI XML and MPP independently, at both file-structure and application-semantic levels. Build a versioned crosswalk covering:

1. format/schema version, encoding and source application version;
2. typed fields, identifiers, codes, UDFs and extension fields;
3. project/EPS/WBS/task hierarchy and summary semantics;
4. FS/SS/FF/SF links, lag units, external/cross-project references and broken-link behavior;
5. project, activity/task, resource and assignment calendars;
6. working periods, nonworking periods, holidays, exceptions, shifts, hours-per-period, timezone and daylight-saving transitions;
7. duration/work units, date precision, constraints, deadlines and scheduling options;
8. resource types, rates, availability, assignment units, curves, spreads and timephased values;
9. baseline count, identity, type, associations and all available baseline values;
10. actuals, progress, costs, financial periods and supported custom fields;
11. vendor-specific, unknown and unsupported data.

### Import invariants

- Parse into a non-mutating staging model; show a deterministic preview and diff before apply.
- Preserve source identifiers, source application/version, source values and provenance. Use explicit stable source-to-CUBI identity mappings.
- Preserve the selected project calendar and every task/activity/resource calendar assignment. Never silently substitute a CUBI default calendar.
- Preserve original source dates, durations, relationships, resources, assignments, baseline snapshots and scheduling inputs. Import must not silently normalize, round, reinterpret, drop or recalculate them.
- If a source construct cannot be represented natively, retain its typed source representation in a versioned extension/provenance area where safe and useful, or stop/fail according to the selected strictness policy. Mark it as preserved-extension, not native-equivalent.
- Import must not trigger a schedule rewrite. The shared CUBI engine remains the sole authority for any later, explicit CUBI schedule calculation.
- If an explicit later calculation produces different dates or float, show a separate comparison against imported source schedule values and explain semantic differences. Do not overwrite imported facts silently.
- Apply must be permission-checked, revision-bound, idempotent and transactional. Validation or write failure must not leave a partial project.
- Provide machine-readable and human-readable compatibility reports with per-field dispositions: exact, equivalent-with-rule, preserved-extension, unsupported-blocking, or omitted-only-after-explicit-approval.

No cross-vendor engine equality may be promised merely because the same inputs were transferred. Differences in scheduling options, calendars, date precision, duration units and engine algorithms must be isolated and reported.

## 6. Round-trip certification

For every format and supported version, certification must include both directions:

- CUBI → native vendor file → open/save/reopen in the target application → import into CUBI.
- Vendor file → import into CUBI → export back to the same vendor format → open/reopen in the target application.

Use independent expected fixtures and semantic assertions; export-then-import self-consistency alone is insufficient.

Compare at minimum:
- project and task/activity identities and hierarchy;
- relationship type, endpoints and lag;
- selected project calendar, every calendar definition and every calendar assignment;
- working time, exceptions, holidays, shifts, timezone and date precision;
- resources, rates, availability, assignments, units, curves/spreads and costs;
- baseline identities, associations and values;
- dates, durations, actuals, progress and cost values.

Generate schedule and calendar fingerprints over normalized, typed source semantics. A parser test is not vendor certification. Each certification record must name the source/target application version, file format/schema, fixture identity, exact test steps, comparison results and limitations.

Test malformed and unknown-version files, duplicate IDs, broken references, unsupported fields, timezone/DST boundaries, decimal precision, security cases and large projects (including 100,000 activities where practical). No silent data loss, default-calendar substitution, baseline flattening, relationship rewriting, resource duplication or partial writes is acceptable.

If a licensed target application, reference file or converter is unavailable, mark that specific gate BLOCKED_EXTERNAL. Do not invent a pass or label parser success as application compatibility.

## 7. Multi-project transfers

A user may select multiple projects into one transfer package. Retain each project's boundary, identity and baselines. Preserve cross-project links only when all referenced projects are included and the target format supports them. Otherwise retain an explicit external-reference record and report the limitation; never silently delete a link.

Shared resources and calendars must remain shared identities when the target model supports shared objects. Do not accidentally duplicate them into unrelated project-local objects. The transfer must not change project ownership, tenant membership, user identities or security grants.

## 8. Required test layers

- **Unit/codec:** parser, serializer, schema/version handling, typed conversion, unknown-field retention and security.
- **Mapping contract:** independently expected values for every critical field family and semantic rule.
- **Application integration:** real target application opens, saves and reopens the file.
- **Round-trip:** both directions with semantic fingerprints and exact diffs.
- **Persistence:** transactional apply, idempotency, revision conflicts, rollback and tenant/project isolation.
- **Scale:** representative large and stress projects.
- **Regression:** no change to source schedule inputs or imported facts from unrelated UI filtering, sorting, layout or view operations.

## 9. Existing implementation ownership — no parallel systems

- Issue #389: parent P6 parity backlog, including calendar and interchange requirements.
- Issue #393: persistence/API/import-export and P6 mapping registry, including Microsoft Project XML/MPX scope.
- Issue #1227: typed interchange mappings and field-type certification.
- Issue #1799: Agent 3 backend exchange implementation and verification.
- Issue #2131: current Excel project-import recovery; this standard does not bypass it.

Issue #2136 records the explicit product-owner gate for genuine native files and round-trip preservation. Implement through the existing owners and contracts. Do not create another importer, field registry, scheduler, calendar engine or resource engine.

## 10. Definition of done

- Versioned compatibility matrices exist for P6 XER, P6 XML, MSPDI XML and the actual MPP conversion path.
- Native files open and round-trip in named target application versions.
- Selected calendars, all referenced calendars, baselines, relationships, resources and assignments survive import/export under exact/equivalent/preserved-extension rules without silent mutation.
- Independent semantic comparisons and schedule/calendar fingerprints pass.
- Unsupported mappings are visible and actionable.
- Code, tests, docs and exact-head CI are linked; statuses distinguish implemented, parser-tested, vendor-tested and production-verified.
- No claim of full interoperability is made before target-application certification.

## 11. Full-fidelity project replacement and controlled import workflow

Import from Primavera or Microsoft Project must support a defined **project replacement workflow**, not only create-new import. Replacement means replacing the selected target project's in-scope project data with the validated source snapshot while retaining unrelated projects and protecting references outside the replacement boundary. It must never mean deleting and recreating records blindly.

### 11.1 Explicit import intent

Before parsing can be applied, the user must choose one of these explicit operations:

1. **Create as new project:** create a new CUBI project identity; preserve all source IDs in source-identity mappings and retain source provenance.
2. **Replace selected project:** replace the selected existing CUBI project's in-scope schedule and project data with the source snapshot. The target CUBI project identity, tenant ownership, permissions and external references remain governed by CUBI; source vendor identifiers are mapped explicitly.
3. **Controlled merge/update:** merge only when a separately defined mapping and conflict policy is selected. This is not a default and must never be inferred from matching names or IDs.

No import may silently choose replace, merge, overwrite, or create-new based on project name.

### 11.2 Preflight and replacement plan

The importer must build a deterministic, immutable staging snapshot and a replacement plan before writing. The plan must identify:

- source application, source format/schema version, source project identity and export timestamp;
- target deployment, tenant, selected target project and current revision;
- all objects to be created, replaced, retained, remapped, detached or rejected;
- source-to-target mappings for project, WBS, activities/tasks, relationships, resources, assignments, calendars, codes/UDFs and baselines;
- incoming and existing object counts, typed field coverage and content/schedule/calendar fingerprints;
- source references to objects outside the package or replacement boundary;
- collisions, duplicate IDs, missing references, unsupported fields, precision conversions, timezone assumptions and every semantic mapping rule;
- effects on shared resources/calendars, other projects, portfolio/enterprise links, reports, documents, workflows and audit history;
- the exact rollback/recovery point and estimated operation scope.

The preview must show both a structured object-level diff and a human-readable summary. A project name match is never sufficient evidence of identity.

### 11.3 Identity, mapping and referential integrity

- Keep source identifiers and provenance immutable in a source identity namespace. CUBI internal IDs may be preserved when safe, or deterministically mapped where collisions exist; mappings must be explicit, stable and reversible.
- Resolve every relationship endpoint, WBS parent, resource assignment, calendar reference, baseline association and cross-project dependency before apply.
- A reference outside the import/replacement package must be classified as a preserved external reference, explicitly mapped to a verified target object, or treated as a blocking unresolved dependency. Never silently null it or bind by display name.
- Shared resource/calendar objects must not be duplicated or overwritten merely because names match. Reuse an existing target shared object only after a typed semantic fingerprint proves equivalence and the user has authorized linking; otherwise preserve an isolated project snapshot or request an explicit resolution.
- Preserve the selected project calendar and each activity/resource calendar assignment exactly. Calendar name equality is not calendar equivalence.
- Preserve all baseline identities and their association to the correct project, WBS, activity, resource and assignment objects. Never convert a baseline into live/current values.

### 11.4 Replacement boundary and protected CUBI data

Replacement applies only to the explicitly selected project data scope. It must not overwrite or delete:

- other projects or portfolio records outside the selected scope;
- tenant, organization, owner, user, role, membership, invitation, access grants or deployment identity;
- CUBI authentication/session secrets or vendor credentials;
- CUBI audit events, immutable revision history or legal/retention records;
- unrelated documents, attachments, workflows or custom data not included in the source package.

For included attachments and custom fields, preserve bytes/typed values and metadata where supported. If an incoming source cannot represent a CUBI-only field, the default is retain it as a CUBI extension with provenance during replacement, or require an explicit field-level discard decision. Never silently erase CUBI-only data.

### 11.5 Apply, verification and rollback

1. Freeze the source staging snapshot and bind the plan to the exact target project revision (optimistic concurrency).
2. Create a recoverable pre-replacement snapshot/backup of the target project and its in-scope dependent records.
3. Revalidate permissions, revision, referential closure, mapping rules, quotas and storage availability immediately before apply.
4. Apply the replacement in one transaction or a durable, resumable atomic-swap protocol with an all-or-nothing visible result. No partially replaced project may be exposed.
5. Do not invoke the scheduling engine as a side effect of import or replacement.
6. Re-read the persisted target and compare source and target semantic fingerprints, object counts, identity mappings, relationships, calendar definitions/assignments, resources/assignments and baseline values.
7. Verify that protected out-of-scope objects and references remain unchanged.
8. Commit the new project revision only after all required checks pass. If any blocking check fails, roll back completely to the pre-replacement state and preserve the failure report.
9. Record who initiated and approved the operation, source provenance, mapping decisions, before/after revision IDs, hashes, warnings and verification results in the audit trail.

If full transactional atomicity cannot be guaranteed for a large project, use a durable staging-and-swap design: stage all new records in isolation, validate them, then switch the active project revision atomically. The previous revision remains recoverable until the new revision is verified.

### 11.6 Conflict and fidelity policy

Every mapped field/object must be classified as one of:
- **EXACT:** same typed value and semantics;
- **EQUIVALENT_WITH_RULE:** explicit documented conversion with verified semantic equivalence;
- **PRESERVED_EXTENSION:** original typed source data retained, but not represented as a native CUBI field;
- **CONFLICT_REQUIRES_DECISION:** multiple plausible targets or incompatible existing data;
- **BLOCKING_UNSUPPORTED:** cannot be safely represented or preserved;
- **EXPLICITLY_OMITTED:** user-approved omission recorded in the audit trail.

Default strict mode blocks apply when a required scheduling, calendar, relationship, resource, assignment or baseline element is not exact/equivalent or safely preserved. A permissive mode may proceed only after showing each affected item and obtaining explicit approval; it must never be labelled lossless.

### 11.7 Replacement acceptance tests

Test at minimum:
- replace an existing project with identical source content and prove idempotency;
- replace with changed dates/logic and verify only intended in-scope values change;
- source/target ID collisions and stable reversible mapping;
- duplicate names with different IDs, and same IDs with different semantics;
- missing WBS parents, broken relationship endpoints, missing calendars/resources and unresolved external links;
- shared resource/calendar references used by other projects;
- CUBI-only fields, attachments, audit history, portfolio links and workflows;
- all baseline slots and baseline-to-object associations;
- calendar work periods, holidays, exceptions, shifts, timezone/DST and hours-per-period;
- optimistic revision conflict, permission revocation, quota failure, mid-apply failure, retry and rollback;
- post-apply fingerprints proving no out-of-scope project or organization data changed;
- large-project staging and atomic activation.

The acceptance criterion is not merely that the replacement finishes. It is that the resulting project is semantically identical to the intended source snapshot for every supported field, all exceptions are explicit and approved, and the prior target state remains recoverable until verification completes.
