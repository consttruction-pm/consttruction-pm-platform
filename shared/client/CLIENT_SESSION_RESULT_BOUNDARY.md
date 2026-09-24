# Client Session Result Boundary

## Purpose

Define the only presentation-to-session handoff for normalized online mutation results.

## Rules

1. Normalize the transport payload before giving it to the session.
2. Only applied and replayed results can advance the session revision.
3. The revision must come from the authoritative result; clients cannot supply a replacement revision.
4. conflict, rejected, and error results leave the session revision unchanged.
5. A backward authoritative revision is rejected.
6. The session does not calculate schedule, calendar, cost, Progress, or other business values.

## Cross-client parity

Web, Desktop, and Mobile can render different controls, but their session revision semantics must remain identical.

## Scope

This boundary coordinates existing contracts. It does not introduce a second revision system or change server-side mutation semantics.
