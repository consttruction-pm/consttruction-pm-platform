# Stage 33.2.5 — Project Portability Contract

The backend portability boundary carries the versioned context required to reload a project without silently changing its calculation inputs.

## Preserved context

A project-portability.v1 snapshot carries:
- tenant and project identity;
- project revision;
- calendar identity/version and calendar context;
- scheduling settings;
- calculation settings;
- Resource/Cost configuration;
- opaque revisions/references for authoritative modules.

Export/import is deterministic and uses canonical JSON ordering. Import requires every context section and validates the project revision.

## Boundary rules

This layer is a transport/context boundary only. It does not calculate dates, durations, critical paths, Progress/EVM, resource cost, or financial values. Authoritative calculation engines remain responsible for interpreting the preserved context.

The opaque module_refs section allows future authoritative modules to bind their own revisions without coupling the portability service to their domain semantics.

## Regression coverage

Tests verify:
1. export → import preserves the complete context;
2. mapping order does not change exported bytes/fingerprint;
3. missing required context is rejected;
4. invalid project revision is rejected.
