# CUBI V2 — Interactive Multilingual Academy

## Status

**Planned for Version 2.** This record is an approved product direction and must not be treated as V1 scope.

The V2 Academy is intended to be built **after the V1 product workflow is complete and usable**. It is a guided, hands-on learning experience that teaches users by executing one realistic multi-story construction project inside the actual CUBI application.

## Product concept

Working concept:

> **CUBI Academy — Build a Project from Zero to Reports**

The learner follows a sample multi-story building project from initial project setup through scheduling, a short period of simulated execution, control charts and daily/weekly reporting.

The tutorial should use the **real CUBI screens and real product workflows**, with annotated screenshots/images from the corresponding application page rather than a disconnected documentation-only experience.

## Core principles

- Multilingual/all-language support from the start.
- RTL/LTR support and language-aware presentation.
- One continuous construction-project scenario across the full course.
- Screenshots/visuals taken from the real CUBI application for each relevant lesson.
- Step-by-step explanations plus an actionable "do it yourself" point.
- Teach both manual workflows and CUBI AI-assisted workflows.
- Preserve the project's authoritative Shared Core and existing API/application boundaries.
- Do not duplicate scheduling, calculation, financial, or project-control semantics in the tutorial/client layer.
- Academy content should follow the actual V1 product behavior; it must not teach obsolete or mock workflows.

## Reference training scenario

Use a realistic multi-story building as the continuous example project. The exact project data set can be finalized when V1 workflows are stable.

The scenario should be large enough to demonstrate:

- WBS hierarchy and multiple floors/areas;
- activities and activity relationships;
- project calendars;
- labor, equipment and cost resources;
- planned schedule;
- several days of actual progress;
- progress/control charts;
- daily and weekly reporting;
- import/export.

## Course sequence

### 1. Project setup and building data

Teach:

- create/open a project;
- project identity and basic building information;
- project parties and basic settings;
- project dates and applicable project configuration.

### 2. WBS and project structure

Teach:

- create the project structure;
- build WBS;
- represent floors/areas/work packages;
- create activities under the appropriate WBS nodes.

### 3. Calendar configuration

Teach:

- select/create a project calendar;
- working days;
- non-working days/holidays;
- working hours;
- assign the appropriate calendar to project/activity context.

### 4. Data entry methods

Teach all supported entry paths:

- manual entry;
- AI-assisted entry;
- voice entry;
- OCR/document-assisted entry.

For AI/voice/OCR, explain what the system proposes/extracts, how the user reviews it, and how authoritative project data is committed.

### 5. Resources and cost

Teach:

- labor;
- equipment/machinery;
- materials where applicable;
- rates/costs;
- resource assignments;
- cost entry and review.

### 6. Activity relationships

Teach:

- Finish-to-Start (FS);
- Start-to-Start (SS);
- Finish-to-Finish (FF);
- Start-to-Finish (SF);
- lead/lag where supported.

The learner creates the relationships in the sample project rather than only reading definitions.

### 7. Schedule and baseline plan

Teach:

- durations;
- relationship-driven scheduling;
- schedule calculation;
- Gantt/schedule presentation;
- critical-path/control views available in CUBI;
- review of the resulting project plan.

Scheduling semantics remain authoritative in the Shared Domain/Calculation Core and must not be reimplemented by the Academy.

### 8. Short execution period

Simulate several days of project execution so the learner can enter:

- actual starts/finishes;
- progress;
- quantities/status where supported;
- labor usage;
- equipment usage;
- actual cost data where supported.

The tutorial should explain the difference between planned and actual information.

### 9. Control charts and reporting

Use the execution data to teach:

- progress charts;
- S-Curve;
- schedule/control views;
- daily report;
- weekly report;
- cost/resource reporting where available;
- interpretation of the resulting project information.

### 10. Import and export

Teach:

- importing supported project data;
- exporting project/report data;
- where to verify the resulting files;
- how project context, dates, durations and typed values are preserved according to the authoritative contracts.

## Lesson format

Each lesson should eventually contain:

1. lesson objective;
2. short explanation;
3. screenshot of the actual CUBI page;
4. numbered/annotated UI callouts;
5. exact user actions;
6. expected result;
7. optional AI/voice/OCR alternative where applicable;
8. common mistakes and recovery;
9. a small hands-on task;
10. completion state before moving to the next lesson.

## Multilingual architecture

The Academy must consume the existing multilingual/language-pack foundations rather than inventing a second translation system.

Target direction:

- all currently supported CUBI languages;
- language-aware lesson metadata;
- localized screenshots/callouts when text in the UI requires it;
- RTL/LTR presentation;
- future voice narration/localized narration where supported.

## V2 acceptance gates

V2 Academy should not be marked complete until:

- the continuous sample project can be completed end-to-end;
- every lesson corresponds to a real current CUBI workflow;
- screenshots are sourced from the actual product screens;
- all instructional paths have current UI/API contract alignment;
- multilingual content coverage is verified;
- RTL/LTR behavior is verified;
- AI, voice and OCR lessons distinguish suggestions/extraction from authoritative committed project data;
- scheduling/calculation behavior comes from the Shared Core;
- import/export lessons use the authoritative typed contracts;
- focused Academy tests and applicable client/runtime/regression gates pass;
- the Academy is verified against the V1 product state it teaches.

## Dependency and priority

This is a **V2 product capability**, not a reason to interrupt current V1/P0/P1 completion work.

Current project rules require completion of the Web product and release/integrity gates before expanding non-critical feature streams. When V2 implementation begins, it should be decomposed into bounded vertical slices and built against the then-current `main`.

## Initial implementation slices

1. Academy content model and lesson registry.
2. Continuous sample construction-project fixture/data set.
3. Lesson runner/navigation shell.
4. Screenshot/annotation asset contract.
5. Project-setup and building-data lessons.
6. WBS/activity/calendar lessons.
7. Manual/AI/voice/OCR entry lessons.
8. Resource/cost lessons.
9. Dependency/scheduling lessons.
10. Execution/progress lessons.
11. Charts/S-Curve/reporting lessons.
12. Import/export lessons.
13. Multilingual/localization coverage.
14. Completion/progress tracking and end-to-end acceptance.

## Non-goals

- Do not rebuild the core scheduling engine for Academy.
- Do not create a separate project-data model that competes with the product model.
- Do not teach from obsolete screenshots.
- Do not make the Academy a static PDF-only manual.
- Do not block V1 completion on V2 Academy work.

## Relationship to the approved V1 visual direction

The approved CUBI V1 homepage direction remains the stable V1 reference. V2 Academy should inherit the CUBI blue/cyan brand, bilingual RTL/LTR behavior, and product-specific visual language without changing the approved V1 homepage direction unless explicitly requested.

## Record

Approved by product direction discussion on **2026-10-06**.

This document is a roadmap/product record. It is intentionally not a claim that the V2 Academy has already been implemented.
