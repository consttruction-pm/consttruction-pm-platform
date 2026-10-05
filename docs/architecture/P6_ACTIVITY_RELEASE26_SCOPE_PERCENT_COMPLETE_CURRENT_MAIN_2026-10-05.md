# P6 Activity Release 26 — ScopePercentComplete Current-Main Correction

Date: 2026-10-05  
Owner: Jalal  
Baseline: `main@1a2b89760a3b4d0cd18e6f966ac407ac346077ba`  
Related: #1186

## Verified mismatch

Current main's canonical Activity registry recorded `ScopePercentComplete` as DOUBLE, non-writable and computed.

Oracle Release 26/26.4 evidence records `ScopePercentComplete` as a Percent field with Read Only blank and describes it as imported from Prime via integration. Release 26 Activity GET/PUT also expose the numeric field.

## Corrected metadata

The canonical registry now records:

- DOUBLE
- writable=true
- computed=false
- unit=percent

## Boundary

Registry metadata and deterministic regression only. No Activity identity or dataclass expansion, no CPM/scheduling/calendar/formula/progress/EVM calculations, no persistence/API/client calculation behavior.

## Oracle sources

- Oracle P6 Pro Integration API Field Summary (Release 26.4)
- Oracle P6 EPPM Release 26 Activity GET
- Oracle P6 EPPM Release 26 Activity PUT
