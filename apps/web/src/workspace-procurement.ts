import type { ProjectScope } from "./workspace-field-ops.js";

export const PROCUREMENT_WEB_VERSION = "procurement-web.v1" as const;

type BaseSnapshot = Readonly<{
  contract_version: string;
  scope: { tenant_id: string; project_id: string; project_revision: number };
  audit: { created_by: string; created_at: string; updated_at: string };
  evidence_refs?: readonly unknown[];
}>;

export type ProcurementRFQSnapshot = BaseSnapshot & Readonly<{
  contract_version: "procurement-rfq.v1"; rfq_id: string; status: string; title_key: string;
  requested_by: string; due_at?: string | null;
  items: readonly { item_id: string; description_key: string; quantity: string; unit: string; activity_ids?: readonly string[] }[];
  supplier_ids: readonly string[];
}>;

export type ProcurementQuoteSnapshot = BaseSnapshot & Readonly<{
  contract_version: "procurement-quote.v1"; quote_id: string; rfq_id: string; supplier_id: string;
  status: string; currency: string; valid_until: string;
  items: readonly { item_id: string; description_key: string; quantity: string; unit: string; unit_price: string; activity_ids?: readonly string[] }[];
}>;

export type ProcurementBidComparisonSnapshot = BaseSnapshot & Readonly<{
  contract_version: "procurement-bid-comparison.v1"; comparison_id: string; rfq_id: string; status: string;
  entries: readonly { quote_id: string; supplier_id: string; compliance_status: string }[];
  selected_quote_id?: string | null; selected_supplier_id?: string | null;
}>;

export type PurchaseOrderSnapshot = BaseSnapshot & Readonly<{
  contract_version: "purchase-order.v1"; po_id: string; supplier_id: string; status: string; currency: string;
  rfq_id?: string | null; quote_id?: string | null; order_date?: string | null; required_delivery_date?: string | null;
  items: readonly { item_id: string; description_key: string; quantity: string; unit: string; unit_price: string; activity_ids?: readonly string[] }[];
  commitment_id?: string | null; approval_reference?: string | null;
}>;

export type ProcurementCommitmentSnapshot = BaseSnapshot & Readonly<{
  contract_version: "procurement-commitment.v1"; commitment_id: string; supplier_id: string; status: string;
  currency: string; committed_amount: string; po_id?: string | null; cost_refs?: readonly string[]; activity_ids?: readonly string[];
}>;

export type ProcurementDeliverySnapshot = BaseSnapshot & Readonly<{
  contract_version: "procurement-delivery.v1"; delivery_id: string; po_id: string; supplier_id: string;
  status: string; delivery_date: string; location_key?: string | null; receipt_reference?: string | null;
  items: readonly { item_id: string; quantity_received: string; unit: string; inspection_id?: string | null; punch_id?: string | null; acceptance_status?: string }[];
}>;

export type ProcurementRecordType = "rfq" | "quote" | "bid_comparison" | "purchase_order" | "commitment" | "delivery";

export type WorkspaceProcurementRecord = Readonly<{
  id: string; type: ProcurementRecordType; status: string; supplierId: string | null; referenceId: string | null;
  currency: string | null; amount: string | null; itemCount: number; activityIds: readonly string[];
  revision: number; evidenceCount: number; approvalRef: string | null; date: string | null;
}>;

function validateBase(snapshot: BaseSnapshot, scope: ProjectScope): void {
  if (snapshot.scope.tenant_id !== scope.tenant_id || snapshot.scope.project_id !== scope.project_id || snapshot.scope.project_revision !== scope.project_revision) {
    throw new Error("STALE_PROCUREMENT_SCOPE");
  }
  if (!snapshot.audit.created_by || !snapshot.audit.created_at || !snapshot.audit.updated_at) throw new Error("INVALID_PROCUREMENT_AUDIT");
  if (!Array.isArray(snapshot.evidence_refs)) throw new Error("INVALID_PROCUREMENT_EVIDENCE");
}

function record(base: BaseSnapshot, id: string, type: ProcurementRecordType, status: string, supplierId: string | null, referenceId: string | null, currency: string | null, amount: string | null, itemCount: number, activityIds: readonly string[], approvalRef: string | null, date: string | null): WorkspaceProcurementRecord {
  if (!id.trim() || !status.trim() || !Number.isInteger(base.scope.project_revision) || itemCount < 0) throw new Error("INVALID_PROCUREMENT_RECORD");
  return Object.freeze({ id, type, status, supplierId, referenceId, currency, amount, itemCount, activityIds: Object.freeze([...activityIds]), revision: base.scope.project_revision, evidenceCount: base.evidence_refs?.length ?? 0, approvalRef, date });
}

export function projectProcurementRFQ(s: ProcurementRFQSnapshot, scope: ProjectScope): WorkspaceProcurementRecord {
  validateBase(s, scope); return record(s, s.rfq_id, "rfq", s.status, null, null, null, null, s.items.length, s.items.flatMap(i => i.activity_ids ?? []), null, s.due_at ?? null);
}
export function projectProcurementQuote(s: ProcurementQuoteSnapshot, scope: ProjectScope): WorkspaceProcurementRecord {
  validateBase(s, scope); return record(s, s.quote_id, "quote", s.status, s.supplier_id, s.rfq_id, s.currency, null, s.items.length, s.items.flatMap(i => i.activity_ids ?? []), null, s.valid_until);
}
export function projectProcurementBidComparison(s: ProcurementBidComparisonSnapshot, scope: ProjectScope): WorkspaceProcurementRecord {
  validateBase(s, scope); return record(s, s.comparison_id, "bid_comparison", s.status, s.selected_supplier_id ?? null, s.rfq_id, null, null, s.entries.length, [], null, null);
}
export function projectPurchaseOrder(s: PurchaseOrderSnapshot, scope: ProjectScope): WorkspaceProcurementRecord {
  validateBase(s, scope); return record(s, s.po_id, "purchase_order", s.status, s.supplier_id, s.rfq_id ?? s.quote_id ?? null, s.currency, null, s.items.length, s.items.flatMap(i => i.activity_ids ?? []), s.approval_reference ?? null, s.required_delivery_date ?? s.order_date ?? null);
}
export function projectProcurementCommitment(s: ProcurementCommitmentSnapshot, scope: ProjectScope): WorkspaceProcurementRecord {
  validateBase(s, scope); return record(s, s.commitment_id, "commitment", s.status, s.supplier_id, s.po_id ?? null, s.currency, s.committed_amount, 0, s.activity_ids ?? [], null, null);
}
export function projectProcurementDelivery(s: ProcurementDeliverySnapshot, scope: ProjectScope): WorkspaceProcurementRecord {
  validateBase(s, scope); return record(s, s.delivery_id, "delivery", s.status, s.supplier_id, s.po_id, null, null, s.items.length, [], s.receipt_reference ?? null, s.delivery_date);
}
