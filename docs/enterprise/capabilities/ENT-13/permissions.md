# ENT-13 — Contract & Commercial permission matrix

| Role | Read | Create / edit | Evaluate / certify | Approve | Execute / close |
|---|---|---|---|---|---|
| Requester | Own package and visible status | Draft need/request | No | No | No |
| Procurement officer | Assigned sourcing packages | Tender, bidder and procurement records | Compliance checks | Only within delegated limit | Issue solicitation when authorized |
| Bid evaluator | Assigned bids only | Evaluation notes and scoring | Evaluate assigned submissions | No self-approval | No |
| Commercial manager | Authorized contract/commercial scope | Contract administration, notices, change submissions | Review variations, claims and payment applications | Within delegated limit only | No unilateral execution unless separately delegated |
| Project manager | Linked project/contract summaries | Project-side evidence and impact request | Validate project delivery evidence | Only if delegated | No contract signature by role alone |
| Finance reviewer | Financial terms and authorized payment data | Reconciliation evidence | Review/certify financial calculations | Within delegated limit | Actual disbursement belongs to finance/ERP |
| Legal reviewer | Need-to-know contract, claim and dispute materials | Legal comments and controlled documents | Legal review | Legal concurrence where policy requires | No automatic signature authority |
| Authorized approver | Items within explicit delegation | No alteration of submitted evidence | Review | Approve/reject within threshold | Only with explicit execution authority |
| Vendor / external party | Own granted package and released documents | Own submissions, invoices and correspondence | Respond to clarifications | No internal approval | No internal state mutation |
| Auditor | Read-only authorized audit trail | No | Inspect | No | No |

## Mandatory controls

- Deny by default; tenant, project, contract and document scope are checked server-side.
- Segregate requester, evaluator, recommender, approver and payer; prevent self-approval where policy prohibits it.
- Bid pricing, claims, legal advice and privileged documents are need-to-know.
- Delegation is explicit, bounded by amount/currency/scope/time and revocable.
- Vendor grants are time-limited, least-privilege and re-authorized on every read/write.
- Contract execution and payment disbursement are separate privileged actions; neither follows merely from workflow approval.
- Every read of restricted tender/claim/legal content and every state-changing action is auditable.
