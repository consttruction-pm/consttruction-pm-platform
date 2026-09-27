# Stage 34.3 — Conformance Gate

This gate proves Shared Control Intelligence and API/client projection layers do not become authoritative calculation engines.

Static checks verify that control-intelligence/backend modules do not import the authoritative scheduling or resource calculators, and the web Control Intelligence projection does not introduce scheduling, duration, EVM, critical-path, or resource-cost calculation calls.

Existing dynamic evidence includes provider delegation in backend schedule query tests, deterministic typed dependency-graph projection tests, scenario revision/mutation tests, and cross-domain regression fixtures.

The gate does not move or duplicate P6 Scheduling, Calendar/Duration, Progress/EVM, Resource/Cost, or financial formulas into API/client layers.
