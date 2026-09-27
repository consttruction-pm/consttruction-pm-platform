import type { ProjectScope } from "./workspace-field-ops.js";

export const PROCUREMENT_WEB_VERSION = "procurement-web.v1" as const;

type EvidenceRef = {
  source_id: string;
  source_type: string;
  locator: string;
  revision: number;
};

type Audit = {
  created_by: string;
  created_at: string;
  updated_at: string;
};

type BaseSnapshot = Readonly<{
  contract_version: string;
  scope: ProjectScope;
  audit: Audit;
  evidence_refs?: readonly EvidenceRef[];
}>;

type ProcurementItem = {
  item_id: string;
  quantity: string;
  unit: string;
  activity_ids?: readonly string[];
};

export type ProcurementRFQSnapshot = BaseSnapshot & Readonly<{
  contract_version: "procurement-rfq.v1";
  rfq_id: string;
  status: "draft" | "issued" | "clarification" | "closed" | "cancelled" | "awarded";
  title_key: string;
  requested_by: string;
  due_at?: string | null;
  items: readonly (ProcurementItem & { description_key: string })[];
  supplier_ids: readonly string[];
}>;

export type ProcurementQuoteSnapshot = BaseSnapshot & Readonly<{
  contract_version: "procurement-quote.v1";
  quote_id: string;
  rfq_id: string;
  supplier_id: string;
  status: "draft" | "submitted" | "under_review" | "withdrawn" | "accepted" | "rejected" | "expired";
  currency: string;
  valid_until: string;
  items: readonly (ProcurementItem & { description_key: string; unit_price: string })[];
}>;

export type ProcurementBidComparisonSnapshot = BaseSnapshot & Readonly<{
  contract_version: "procurement-bid-comparison.v1";
  comparison_id: string;
  rfq_id: string;
  status: "draft" | "under_review" | "approved" | "rejected" | "closed";
  entries: readonly {
    quote_id: string;
    supplier_id: string;
    compliance_status: "compliant" | "partial" | "non_compliant" | "not_evaluated";
  }[];
  selected_quote_id?: string | null;
  selected_supplier_id?: string | null;
  decision_reference?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
}>;

export type PurchaseOrderSnapshot = BaseSnapshot & Readonly<{
  contract_version: "purchase-order.v1";
  po_id: string;
  supplier_id: string;
  status: "draft" | "approved" | "issued" | "partially_received" | "closed" | "cancelled";
  currency: string;
  rfq_id?: string | null;
  quote_id?: string | null;
  order_date?: string | null;
  required_delivery_date?: string | null;
  items: readonly (ProcurementItem & { description_key: string; unit_price: string })[];
  commitment_id?: string | null;
  approval_reference?: string | null;
}>;

export type ProcurementCommitmentSnapshot = BaseSnapshot & Readonly<{
  contract_version: "procurement-commitment.v1";
  commitment_id: string;
  supplier_id: string;
  status: "planned" | "committed" | "partially_released" | "released" | "closed" | "cancelled";
  currency: string;
  committed_amount: string;
  po_id?: string | null;
  cost_refs?: readonly string[];
  activity_ids?: readonly string[];
}>;

export type ProcurementDeliverySnapshot = BaseSnapshot & Readonly<{
  contract_version: "procurement-delivery.v1";
  delivery_id: string;
  po_id: string;
  supplier_id: string;
  status: "scheduled" | "partial" | "received" | "rejected" | "cancelled";
  delivery_date: string;
  location_key?: string | null;
  receipt_reference?: string | null;
  items: readonly {
    item_id: string;
    quantity_received: string;
    unit: string;
    inspection_id?: string | null;
    punch_id?: string | null;
    acceptance_status?: "pending" | "accepted" | "rejected" | "partial";
  }[];
}>;

export type ProcurementRecordType =
  | "rfq"
  | "quote"
  | "bid_comparison"
  | "purchase_order"
  | "commitment"
  | "delivery";

export type WorkspaceProcurementRecord = Readonly<{
  id: string;
  type: ProcurementRecordType;
  status: string;
  supplierId: string | null;
  referenceId: string | null;
  currency: string | null;
  amount: string | null;
  itemCount: number;
  activityIds: readonly string[];
  revision: number;
  evidenceCount: number;
  approvalRef: string | null;
  date: string | null;
}>;

const EVIDENCE_REQUIRED = new Set<ProcurementRecordType>([
  "quote",
  "bid_comparison",
  "purchase_order",
  "commitment",
  "delivery",
]);

function validateBase(
  snapshot: BaseSnapshot,
  scope: ProjectScope,
  expectedContract: string,
  type: ProcurementRecordType,
): void {
  if (snapshot.contract_version !== expectedContract) {
    throw new Error(`UNSUPPORTED_${type.toUpperCase()}_CONTRACT`);
  }
  if (
    snapshot.scope.tenant_id !== scope.tenant_id ||
    snapshot.scope.project_id !== scope.project_id ||
    snapshot.scope.project_revision !== scope.project_revision
  ) {
    throw new Error("STALE_PROCUREMENT_SCOPE");
  }
  if (
    !snapshot.audit.created_by ||
    !snapshot.audit.created_at ||
    !snapshot.audit.updated_at
  ) {
    throw new Error("INVALID_PROCUREMENT_AUDIT");
  }
  if (EVIDENCE_REQUIRED.has(type)) {
    validateEvidence(snapshot.evidence_refs);
  } else if (
    snapshot.evidence_refs !== undefined &&
    !Array.isArray(snapshot.evidence_refs)
  ) {
    throw new Error("INVALID_PROCUREMENT_EVIDENCE");
  }
}

function validateEvidence(refs: readonly EvidenceRef[] | undefined): void {
  if (!Array.isArray(refs) || refs.length < 1) {
    throw new Error("INVALID_PROCUREMENT_EVIDENCE");
  }
  for (const ref of refs) {
    if (
      !ref.source_id ||
      !ref.source_type ||
      !ref.locator ||
      !Number.isInteger(ref.revision) ||
      ref.revision < 0 ||
      ref.revision > 9_007_199_254_740_991
    ) {
      throw new Error("INVALID_PROCUREMENT_EVIDENCE");
    }
  }
}

function validateDate(value: string | null | undefined, errorCode: string): void {
  if (
    value !== undefined &&
    value !== null &&
    (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(Date.parse(value)))
  ) {
    throw new Error(errorCode);
  }
}

function validateDateTime(value: string | null | undefined, errorCode: string): void {
  if (
    value !== undefined &&
    value !== null &&
    (Number.isNaN(Date.parse(value)) || !/(?:Z|[+-]\d{2}:\d{2})$/.test(value))
  ) {
    throw new Error(errorCode);
  }
}

function validateActivityIds(values: readonly string[] | undefined): readonly string[] {
  const ids = values ?? [];
  if (!Array.isArray(ids) || ids.some((value) => !value || typeof value !== "string")) {
    throw new Error("INVALID_PROCUREMENT_ACTIVITY_LINK");
  }
  return ids;
}

// Quantities are decimal strings; zero and leading-zero forms are rejected.\nfunction validateQuantity(value: string, errorCode: string): void {
  if (!/^(?!0+(?:\.0+)?$)(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value)) {
    throw new Error(errorCode);
  }
}

function validateStringAmount(value: string | null, errorCode: string): void {
  if (
    value !== null &&
    !/^-?(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value)
  ) {
    throw new Error(errorCode);
  }
}

function record(
  base: BaseSnapshot,
  id: string,
  type: ProcurementRecordType,
  status: string,
  supplierId: string | null,
  referenceId: string | null,
  currency: string | null,
  amount: string | null,
  itemCount: number,
  activityIds: readonly string[],
  approvalRef: string | null,
  date: string | null,
): WorkspaceProcurementRecord {
  if (
    typeof id !== "string" ||
    !id.trim() ||
    typeof status !== "string" ||
    !status.trim() ||
    !Number.isInteger(base.scope.project_revision) ||
    base.scope.project_revision < 0 ||
    itemCount < 0 ||
    !Number.isInteger(itemCount)
  ) {
    throw new Error("INVALID_PROCUREMENT_RECORD");
  }
  if (currency !== null && (currency.length !== 3 || !/^[A-Z]{3}$/.test(currency))) {
    throw new Error("INVALID_PROCUREMENT_CURRENCY");
  }
  validateStringAmount(amount, "INVALID_PROCUREMENT_AMOUNT");
  validateActivityIds(activityIds);
  return Object.freeze({
    id,
    type,
    status,
    supplierId,
    referenceId,
    currency,
    amount,
    itemCount,
    activityIds: Object.freeze([...activityIds]),
    revision: base.scope.project_revision,
    evidenceCount: base.evidence_refs?.length ?? 0,
    approvalRef,
    date,
  });
}

export function projectProcurementRFQ(
  snapshot: ProcurementRFQSnapshot,
  scope: ProjectScope,
): WorkspaceProcurementRecord {
  validateBase(snapshot, scope, "procurement-rfq.v1", "rfq");
  validateDateTime(snapshot.due_at, "INVALID_PROCUREMENT_DUE_AT");
  for (const item of snapshot.items) validateQuantity(item.quantity, "INVALID_PROCUREMENT_QUANTITY");
  const activityIds = snapshot.items.flatMap((item) => validateActivityIds(item.activity_ids));
  return record(snapshot, snapshot.rfq_id, "rfq", snapshot.status, null, null, null, null, snapshot.items.length, activityIds, null, snapshot.due_at ?? null);
}

export function projectProcurementQuote(
  snapshot: ProcurementQuoteSnapshot,
  scope: ProjectScope,
): WorkspaceProcurementRecord {
  validateBase(snapshot, scope, "procurement-quote.v1", "quote");
  validateDate(snapshot.valid_until, "INVALID_PROCUREMENT_VALID_UNTIL");
  for (const item of snapshot.items) {
    validateQuantity(item.quantity, "INVALID_PROCUREMENT_QUANTITY");
    validateStringAmount(item.unit_price, "INVALID_PROCUREMENT_UNIT_PRICE");
  }
  const activityIds = snapshot.items.flatMap((item) => validateActivityIds(item.activity_ids));
  return record(snapshot, snapshot.quote_id, "quote", snapshot.status, snapshot.supplier_id, snapshot.rfq_id, snapshot.currency, null, snapshot.items.length, activityIds, null, snapshot.valid_until);
}

export function projectProcurementBidComparison(
  snapshot: ProcurementBidComparisonSnapshot,
  scope: ProjectScope,
): WorkspaceProcurementRecord {
  validateBase(snapshot, scope, "procurement-bid-comparison.v1", "bid_comparison");
  validateDateTime(snapshot.approved_at, "INVALID_PROCUREMENT_APPROVED_AT");
  const approvalRef = snapshot.decision_reference ?? null;
  return record(snapshot, snapshot.comparison_id, "bid_comparison", snapshot.status, snapshot.selected_supplier_id ?? null, snapshot.rfq_id, null, null, snapshot.entries.length, [], approvalRef, snapshot.approved_at ?? null);
}

export function projectPurchaseOrder(
  snapshot: PurchaseOrderSnapshot,
  scope: ProjectScope,
): WorkspaceProcurementRecord {
  validateBase(snapshot, scope, "purchase-order.v1", "purchase_order");
  validateDate(snapshot.order_date, "INVALID_PROCUREMENT_ORDER_DATE");
  validateDate(snapshot.required_delivery_date, "INVALID_PROCUREMENT_REQUIRED_DELIVERY_DATE");
  for (const item of snapshot.items) {
    validateQuantity(item.quantity, "INVALID_PROCUREMENT_QUANTITY");
    validateStringAmount(item.unit_price, "INVALID_PROCUREMENT_UNIT_PRICE");
  }
  const activityIds = snapshot.items.flatMap((item) => validateActivityIds(item.activity_ids));
  return record(snapshot, snapshot.po_id, "purchase_order", snapshot.status, snapshot.supplier_id, snapshot.rfq_id ?? snapshot.quote_id ?? null, snapshot.currency, null, snapshot.items.length, activityIds, snapshot.approval_reference ?? null, snapshot.required_delivery_date ?? snapshot.order_date ?? null);
}

export function projectProcurementCommitment(
  snapshot: ProcurementCommitmentSnapshot,
  scope: ProjectScope,
): WorkspaceProcurementRecord {
  validateBase(snapshot, scope, "procurement-commitment.v1", "commitment");
  validateStringAmount(snapshot.committed_amount, "INVALID_PROCUREMENT_AMOUNT");
  return record(snapshot, snapshot.commitment_id, "commitment", snapshot.status, snapshot.supplier_id, snapshot.po_id ?? null, snapshot.currency, snapshot.committed_amount, 0, validateActivityIds(snapshot.activity_ids), null, null);
}

export function projectProcurementDelivery(
  snapshot: ProcurementDeliverySnapshot,
  scope: ProjectScope,
): WorkspaceProcurementRecord {
  validateBase(snapshot, scope, "procurement-delivery.v1", "delivery");
  validateDate(snapshot.delivery_date, "INVALID_PROCUREMENT_DELIVERY_DATE");
  for (const item of snapshot.items) validateQuantity(item.quantity_received, "INVALID_PROCUREMENT_QUANTITY");
  return record(snapshot, snapshot.delivery_id, "delivery", snapshot.status, snapshot.supplier_id, snapshot.po_id, null, null, snapshot.items.length, [], snapshot.receipt_reference ?? null, snapshot.delivery_date);
}
