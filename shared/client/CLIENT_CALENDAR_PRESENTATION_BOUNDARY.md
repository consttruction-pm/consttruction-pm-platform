# Client Calendar Presentation Boundary

## Purpose

Define the framework-neutral calendar reference consumed by Web, Desktop, and Mobile without moving calendar arithmetic into presentation code.

## Contract

`ClientCalendarReference` carries `calendar_id`, `calendar_version`, and `kind` (`working-day` or `working-time`). `ClientCalendarContext` carries project, optional activity, and optional relationship-lag references.

## Effective reference rules

1. Activity calendar, otherwise project calendar.
2. Relationship-lag calendar, otherwise activity calendar, otherwise project calendar.

Clients may display and select references, but must not calculate working days, working hours, duration, lag, finish/start dates, or float.

## Version integrity

A calendar reference identifies both ID and version. Clients must not silently replace a missing requested version with another version. Resolution to an executable Shared Core calendar remains authoritative.

## Localization and parity

Calendar IDs and versions are stable identifiers. Localized labels, weekday names, and Jalali/Gregorian presentation belong to the presentation layer and must not alter the reference or calculation semantics. Web, Desktop, and Mobile should serialize the same reference/context payloads while remaining free to render them differently.
