import json
from pathlib import Path

from construction_pm.client_sync.api_endpoint import VersionedSyncEndpoint, VersionedSyncRevisionEndpoint
from construction_pm.client_sync.application_gateway import ApplicationSyncGateway
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.sync_outcome import SyncDisposition

class RevisionAwareHandler:
    def __init__(self, revisions): self.revisions, self.calls = revisions, 0
    def handle(self, mutation):
        self.calls += 1
        if mutation.expected_revision != self.revisions[(mutation.tenant_id, mutation.project_id)]: raise RuntimeError("stale revision")

def _mutation(revision, key="idem-1"):
    return {"contract_version":"sync-mutation.v1","mutation_id":"mutation-1","tenant_id":"tenant-1","project_id":"project-1","expected_revision":revision,"operation":"update_activity","payload":{"activity_id":"A-1"},"idempotency_key":key}

def _headers(revision,key):
    return {"Idempotency-Key":key,"X-Tenant-Id":"tenant-1","X-Project-Id":"project-1","X-Project-Revision":str(revision)}

def test_sync_project_revision_contract_is_versioned():
    root=Path(__file__).resolve().parents[2]
    contract=json.loads((root/"shared"/"contracts"/"sync-project-revision.schema.json").read_text(encoding="utf-8"))
    assert contract["$id"]=="constructionpm://contracts/sync-project-revision/v1"
    success,error=contract["oneOf"]
    assert success["properties"]["revision"]["maximum"]==9007199254740991
    assert error["properties"]["error_code"]["const"]=="INVALID_PROJECT_CONTEXT"

def test_sync_mutation_contract_caps_expected_revision_at_client_safe_integer():
    root=Path(__file__).resolve().parents[2]
    contract=json.loads((root/"shared"/"contracts"/"sync-mutation.schema.json").read_text(encoding="utf-8"))
    assert contract["properties"]["expected_revision"]["maximum"]==9007199254740991

def test_offline_mutation_rejects_unsafe_expected_revision_at_domain_boundary():
    try: OfflineMutation("mutation-unsafe","tenant-1","project-1",9007199254740992,"update_activity",{"activity_id":"A-1"},"idem-unsafe")
    except ValueError as exc: assert str(exc)=="INVALID_EXPECTED_REVISION"
    else: raise AssertionError("unsafe expected_revision must be rejected")

def test_mutation_endpoint_rejects_unsafe_expected_revision():
    endpoint=VersionedSyncEndpoint(ApplicationSyncGateway("tenant-1","project-1",RevisionAwareHandler({("tenant-1","project-1"):8})))
    result=endpoint.post(_mutation(9007199254740992),_headers(9007199254740992,"idem-unsafe"))
    assert result["error_code"]=="INVALID_EXPECTED_REVISION"

def test_revision_endpoint_returns_authoritative_server_revision():
    endpoint=VersionedSyncRevisionEndpoint("tenant-1","project-1",lambda tenant,project:8)
    assert endpoint.get({"X-Tenant-Id":"tenant-1","X-Project-Id":"project-1"})["revision"]==8

def test_revision_endpoint_rejects_unsafe_project_revision():
    endpoint=VersionedSyncRevisionEndpoint("tenant-1","project-1",lambda tenant,project:9007199254740992)
    try: endpoint.get({"X-Tenant-Id":"tenant-1","X-Project-Id":"project-1"})
    except ValueError as exc: assert str(exc)=="INVALID_PROJECT_REVISION"
    else: raise AssertionError("unsafe project revision must be rejected")

def test_revision_endpoint_rejects_wrong_project_context_without_reading_revision():
    calls=[]
    endpoint=VersionedSyncRevisionEndpoint("tenant-1","project-1",lambda tenant,project:calls.append((tenant,project)) or 8)
    assert endpoint.get({"X-Tenant-Id":"tenant-1","X-Project-Id":"other-project"})["error_code"]=="INVALID_PROJECT_CONTEXT"
    assert calls==[]

def test_real_conflict_refresh_and_explicit_retry_uses_authoritative_revision():
    revisions={("tenant-1","project-1"):8}; handler=RevisionAwareHandler(revisions)
    endpoint=VersionedSyncEndpoint(ApplicationSyncGateway("tenant-1","project-1",handler))
    revision_endpoint=VersionedSyncRevisionEndpoint("tenant-1","project-1",lambda tenant,project:revisions[(tenant,project)])
    first=endpoint.post(_mutation(7),_headers(7,"idem-1"))
    assert first["disposition"]==SyncDisposition.CONFLICT.value and first["error_code"]=="STALE_REVISION"
    assert revision_endpoint.get({"X-Tenant-Id":"tenant-1","X-Project-Id":"project-1"})["revision"]==8
    second=endpoint.post(_mutation(8,"idem-1:r8"),_headers(8,"idem-1:r8"))
    assert second["disposition"]=="acknowledged"
    assert handler.calls==2
