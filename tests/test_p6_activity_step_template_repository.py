import sqlite3
import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_step_template_repository import P6ActivityStepTemplate, P6ActivityStepTemplatePersistenceError, SQLiteP6ActivityStepTemplateRepository

def scope(revision=1): return BackendScope("tenant-a", "project-a", revision)

def template(s, template_id="T1"):
    return P6ActivityStepTemplate(s, template_id, "Formwork Inspection", "Standard inspection steps", (("discipline","STRUCT"),("zone","Z-1")))

def test_round_trip_and_deterministic_order():
    repo=SQLiteP6ActivityStepTemplateRepository(sqlite3.connect(":memory:"))
    repo.upsert(template(scope(),"T2")); repo.upsert(template(scope(),"T1"))
    assert repo.get(scope(),"T1")==template(scope(),"T1")
    assert [x.template_id for x in repo.list(scope())]==["T1","T2"]

def test_tenant_and_project_isolation():
    repo=SQLiteP6ActivityStepTemplateRepository(sqlite3.connect(":memory:")); repo.upsert(template(scope()))
    assert repo.get(BackendScope("tenant-b","project-a",1),"T1") is None
    assert repo.get(BackendScope("tenant-a","project-b",1),"T1") is None

def test_stale_revision_rejected():
    repo=SQLiteP6ActivityStepTemplateRepository(sqlite3.connect(":memory:")); repo.upsert(template(scope(2)))
    with pytest.raises(P6ActivityStepTemplatePersistenceError,match="REVISION_CONFLICT"): repo.get(scope(3),"T1")
    with pytest.raises(P6ActivityStepTemplatePersistenceError,match="REVISION_CONFLICT"): repo.upsert(template(scope(3),"T1"))

def test_identical_replay_is_idempotent_but_changed_definition_is_immutable():
    repo=SQLiteP6ActivityStepTemplateRepository(sqlite3.connect(":memory:")); original=template(scope())
    assert repo.upsert(original)==original and repo.upsert(original)==original
    changed=P6ActivityStepTemplate(scope(),"T1","Changed",original.description,original.udf_metadata)
    with pytest.raises(P6ActivityStepTemplatePersistenceError,match="IMMUTABLE_ACTIVITY_STEP_TEMPLATE"): repo.upsert(changed)

def test_invalid_definition_fails_closed():
    repo=SQLiteP6ActivityStepTemplateRepository(sqlite3.connect(":memory:"))
    with pytest.raises(P6ActivityStepTemplatePersistenceError,match="INVALID_NAME"): repo.upsert(P6ActivityStepTemplate(scope(),"T1",""))
    with pytest.raises(P6ActivityStepTemplatePersistenceError,match="INVALID_UDF_METADATA"): repo.upsert(P6ActivityStepTemplate(scope(),"T2","Template",udf_metadata=(("x",1),)))
