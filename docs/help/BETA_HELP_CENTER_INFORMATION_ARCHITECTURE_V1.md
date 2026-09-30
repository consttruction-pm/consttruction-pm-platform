# Beta Help Center — Information Architecture v1

**Product release target:** Beta  
**Documentation contract:** beta-help.v1  
**Languages:** Persian (fa) and English (en) at launch; locale-neutral structure for future languages  
**Reference baseline:** Oracle Primavera P6 Professional and Microsoft Project task-oriented help patterns  
**Authority rule:** Documentation describes implemented product behavior only. P6/MS Project materials are structural/reference models; copyrighted manual text is not copied.

## 1. Purpose
The Help Center is a first-class product surface for Web, Desktop and Mobile. It provides task-oriented procedures, field/option explanations, validation guidance, examples, troubleshooting, terminology and contextual links.

Documentation is versioned with the product so a Beta user never receives instructions silently describing a different product contract.

## 2. Information architecture
### Getting Started
Welcome and product concepts; sign-in/workspace/first project; navigation; language and locale; Persian/English and RTL/LTR; keyboard shortcuts; accessibility.

### Projects
Create/open/close/archive; project identity/settings; EPS/project hierarchy; Data Date; project calendar; versions/revisions; import/export.

### WBS and Activities
WBS; activities; statuses/types; typed fields; calendars; constraints; codes/UDF; custom columns; field chooser; sorting/grouping/filtering.

### Relationships and Scheduling
FS/SS/FF/SF; lag/lead; forward/backward scheduling; float; criticality; multiple float paths; out-of-sequence scheduling; relationship lag calendars; start-to-start lag; expected finish; Calculate Float Based on Finish Date; resource leveling; scheduling validation.

### Calendars and Time
Gregorian/Jalali; working days; exceptions; working-time calculations; activity/project/resource calendar assignment; inheritance/resolution; duration and lag units.

### Resources and Costs
Resources; assignments; units/costs; resource calendars; availability/over-allocation; resource leveling; level within float; minimum float; over-allocation percentage; resource/priority selection.

### Progress and Control
Actual/remaining dates; progress states; remaining work; progress overrides; earned/progress control; variance/float interpretation; audit/provenance.

### Gantt, Reports and Printing
Activity/WBS grid; Gantt; column selection; width/alignment/pinning/freezing where supported; formula columns; report/print field selection.

### Formula and Calculated Columns
Formula editor; validation lifecycle; field types; dependency results; stale validation protection; Shared Core/API calculation authority; no client-side formula semantics.

### Data Exchange
Excel/XLSX; Microsoft Project interchange; Primavera interchange; typed dates/numbers/durations/percentages; unsupported-field policy; round-trip verification.

### Documents and Construction Controls
Documents; drawings/revisions; correspondence; RFI; submittals; delay/claim evidence; approval workflow; OCR/search; links to schedule/cost/progress.

### Users, Security and Audit
Users/roles; permissions; project access; audit trail; revision/concurrency; remote access controls.

### AI Assistant and Smart Guide
AI overview; online/offline capability; voice; contextual guidance; error explanation/correction; next actions; provenance/approval; no silent mutation of authoritative project truth.

### Administration and Settings
Organization/project settings; language/locale; calendars; units/currency; integrations; release/version.

### Troubleshooting and Reference
Validation/error catalog; scheduling/import/export/sync diagnostics; FAQ; glossary; P6-to-product terminology; release/change notes.

## 3. Topic contract
Every topic uses: topic_id, product_area, localized title, locale, product/documentation version, status, prerequisites, roles, related_topics, deep_link, last_verified, and source_contracts.

## 4. Topic body contract
Each procedural topic contains: Purpose; When to use; Prerequisites; Procedure; Field/option reference; Validation/errors; Example; Related topics; Version/behavior notes; Accessibility notes where relevant.

## 5. Contextual help contract
Screens expose a stable, locale-neutral help topic identifier. Example: help://beta/activity-grid/field-chooser

Rules: locale changes do not change topic identity; missing locale content follows the fallback chain; unavailable topics produce a deterministic unavailable state; deep links never grant permissions; retired topics remain traceable.

## 6. Current-main evidence boundary
Current-main contracts that may be documented after verification include the P6 field/layout foundation, Activity/WBS grid contracts, layout persistence/migration, field chooser, formula editor/grid binding, report/print selection, OOS Shared Core, and resource-leveling Shared Core.

A contract is not automatically a complete user feature. Topic status must distinguish Contract, Implemented, Integrated, and Beta-verified.

## 7. Status vocabulary
Contract; Implemented; Integrated; Beta-verified; Planned; Retired.

## 8. P6/MS Project alignment
Use task-oriented organization, option explanations, field references, procedures, troubleshooting and cross-links as structural models. Do not copy source-manual wording. Current product contracts and verified implementation determine behavior.

## 9. Localization
Persian and English use the same topic IDs and metadata schema. Additional languages reuse the same topic graph. Completeness is measured per published Beta topic.

## 10. Offline/Desktop
Desktop/local deployments can package a versioned static Help snapshot. Web Help may update independently only when its declared product-version compatibility includes the client version. Offline Help remains readable without Internet.

## 11. QA gates
Publish only when metadata validates, required Beta locales exist, deep links resolve or are explicitly unavailable, claims are supported by current contracts, version compatibility is declared, internal links resolve, and terminology matches shared product vocabulary.
