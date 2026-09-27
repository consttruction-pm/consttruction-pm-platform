import assert from "node:assert/strict";
import test from "node:test";
import { projectProcurementRFQ, projectProcurementQuote, projectProcurementBidComparison, projectPurchaseOrder, projectProcurementCommitment, projectProcurementDelivery } from "./workspace-procurement.js";

const scope={tenant_id:"t1",project_id:"p1",project_revision:4};
const audit={created_by:"u1",created_at:"2026-01-01T00:00:00Z",updated_at:"2026-01-01T00:00:00Z"};
const evidence=[{source_id:"doc-1",source_type:"document",locator:"/1",revision:4}];

test("workspace procurement projections all workflow records",()=>{
    const rfq=projectProcurementRFQ({contract_version:"procurement-rfq.v1",rfq_id:"rfq-1",scope,status:"issued",title_key:"rfq.title",requested_by:"u1",due_at:null,items:[{item_id:"i1",description_key:"cement",quantity:"10",unit:"t",activity_ids:["A-1"]}],supplier_ids:["S-1"],audit},scope);
    const quote=projectProcurementQuote({contract_version:"procurement-quote.v1",quote_id:"q-1",scope,rfq_id:"rfq-1",supplier_id:"S-1",status:"submitted",currency:"USD",valid_until:"2026-02-01",items:[{item_id:"i1",description_key:"cement",quantity:"10",unit:"t",unit_price:"25",activity_ids:["A-1"]}],audit,evidence_refs:evidence},scope);
    const bid=projectProcurementBidComparison({contract_version:"procurement-bid-comparison.v1",comparison_id:"bc-1",scope,rfq_id:"rfq-1",status:"under_review",entries:[{quote_id:"q-1",supplier_id:"S-1",compliance_status:"compliant"}],audit,evidence_refs:evidence},scope);
    const po=projectPurchaseOrder({contract_version:"purchase-order.v1",po_id:"po-1",scope,supplier_id:"S-1",status:"approved",currency:"USD",rfq_id:"rfq-1",quote_id:"q-1",order_date:"2026-01-02",required_delivery_date:"2026-02-02",items:[{item_id:"i1",description_key:"cement",quantity:"10",unit:"t",unit_price:"25",activity_ids:["A-1"]}],audit,evidence_refs:evidence},scope);
    const commitment=projectProcurementCommitment({contract_version:"procurement-commitment.v1",commitment_id:"c-1",scope,supplier_id:"S-1",status:"committed",currency:"USD",committed_amount:"250",po_id:"po-1",activity_ids:["A-1"],audit,evidence_refs:evidence},scope);
    const delivery=projectProcurementDelivery({contract_version:"procurement-delivery.v1",delivery_id:"d-1",scope,po_id:"po-1",supplier_id:"S-1",status:"received",delivery_date:"2026-02-02",receipt_reference:"GRN-1",items:[{item_id:"i1",quantity_received:"10",unit:"t",acceptance_status:"accepted"}],audit,evidence_refs:evidence},scope);
    assert.deepEqual([rfq,quote,bid,po,commitment,delivery].map(x=>x.type), ["rfq","quote","bid_comparison","purchase_order","commitment","delivery"]);
    assert.deepEqual(po.activityIds, ["A-1"]);
    assert.equal(commitment.amount, "250");
test("procurement projection rejects stale project scope",()=>{
    assert.throws(() => projectProcurementRFQ({contract_version:"procurement-rfq.v1",rfq_id:"rfq-1",scope:{...scope,project_revision:3},status:"issued",title_key:"x",requested_by:"u1",items:[{item_id:"i1",description_key:"x",quantity:"1",unit:"ea"}],supplier_ids:[],audit},scope), /STALE_PROCUREMENT_SCOPE/);
  });
test("procurement projection requires evidence collection shape",()=>{
    assert.throws(() => projectProcurementQuote({contract_version:"procurement-quote.v1",quote_id:"q-1",scope,rfq_id:"rfq-1",supplier_id:"S-1",status:"submitted",currency:"USD",valid_until:"2026-02-01",items:[{item_id:"i1",description_key:"x",quantity:"1",unit:"ea",unit_price:"1"}],audit,evidence_refs:null as never},scope), /INVALID_PROCUREMENT_EVIDENCE/);
  });
});
