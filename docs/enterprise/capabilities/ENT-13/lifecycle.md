# ENT-13 — Contract & Commercial lifecycle model

**Status:** source-mapped architecture; not a claim of complete Unifier parity or production implementation.

1. **Need and sourcing strategy** — define scope/package, procurement route, budget authority, funding source, delivery strategy and approval thresholds.
2. **Solicitation and tender** — issue RFQ/RFP, addenda, bidder list, clarifications, submissions and compliance evidence.
3. **Evaluation** — apply approved criteria, record scoring and conflicts, preserve evaluator segregation and recommendation evidence.
4. **Award authorization** — verify due diligence, funding and delegated authority; record approved award decision.
5. **Contract formation and execution** — versioned contract, parties, scope, price model, currency, dates, milestones, bonds/insurance, tax, retention, payment terms, notices, governing law, executed documents and effective date.
6. **Administration and obligations** — obligations, deliverables, submittals, notices, correspondence, securities expiry, vendor performance and linked project controls.
7. **Progress and payment** — measured work, supporting evidence, invoice/payment application, review/certification, deductions, retention, tax, advance recovery, approved amount and payment status. Certification is distinct from actual disbursement.
8. **Variations and change orders** — initiate, classify, substantiate, evaluate entitlement, assess scope/time/cost/term impact, approve under thresholds and issue authorized instruction. Pending and approved changes remain distinct.
9. **Claims, disputes and notices** — deadlines, event chronology, clauses, correspondence, evidence, time/quantum submissions, assessment, negotiation and disposition.
10. **Forecast and cash flow** — show original value, approved changes, approved commitments, pending exposure, certified/paid amounts, retention, forecast final value and dated cash flow with explicit currency/rate provenance.
11. **Suspension, termination and closeout** — suspension/resumption, termination grounds/approval, final account/payment, security release, warranty/defects period, handover, claims disposition, archive and controlled closure/reopening.

## State invariants

- Approval, execution, certification and payment are distinct states/events.
- Pending changes and claims are not silently included in approved commitments or liabilities.
- Executed contract versions and approved commercial events are immutable; changes create controlled revisions/events.
- Every state transition records actor, delegated authority, timestamp, evidence, source revision and audit event.
- A downstream schedule/cost effect is only a request to the Engineering owner; Engineering validates and records its own authoritative change.
- External payment execution remains with the designated finance/ERP system.
