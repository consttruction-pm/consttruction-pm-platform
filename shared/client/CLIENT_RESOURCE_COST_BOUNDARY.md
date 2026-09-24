# Resource and Cost Client Boundary

## Purpose

Define the typed client boundary for Resource API v1 consumed by Web, Desktop, and Mobile.

## Resource identity

`ClientResourceDTO` preserves resource ID, code, name, type, unit, calendar reference, active state, and authoritative revision.

## Assignment values

`ClientResourceAssignmentDTO` preserves planned/actual/remaining units and costs as canonical decimal strings. Clients must not convert these authoritative values into floating-point business calculations.

## Revision and errors

Successful resource responses carry an authoritative positive revision. Client adapters must route conflict, validation, context, authorization, not-found, and persistence errors through the existing stable ApplicationError boundary rather than branching on message text.

## Scope

This boundary only parses and presents authoritative Resource API data. Resource utilization, capacity, cost, variance, EVM, and financial calculations remain in the Shared/Application layers.
