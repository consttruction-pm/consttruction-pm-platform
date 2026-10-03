from __future__ import annotations
import os, threading, uuid
import pytest
psycopg = pytest.importorskip("psycopg")
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_financial_period_repository import P6FinancialPeriod, P6FinancialPeriodPersistenceError, PostgresP6FinancialPeriodRepository
from construction_pm.p6_baseline_repository import P6Baseline, P6BaselinePersistenceError, PostgresP6BaselineRepository
from construction_pm.p6_formula_definition_repository import P6FormulaDefinitionPersistenceError, PersistedP6FormulaDefinition, PostgresP6FormulaDefinitionRepository
from construction_pm.p6_formula_engine import FormulaDefinition, FormulaType

@pytest.fixture(scope="module")
def postgres_dsn():
    dsn=os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn: pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    return dsn

@pytest.fixture()
def connection(postgres_dsn):
    conn=psycopg.connect(postgres_dsn)
    try: yield conn
    finally: conn.rollback(); conn.close()

def scope(rev=7):
    s=uuid.uuid4().hex
    return BackendScope("tenant-"+s,"project-"+s,rev)

def period(s,name="October 2026"):
    return P6FinancialPeriod(s,"period-1",name,"2026-10-01","2026-10-31","OPEN")

def baseline(s,name="Primary"):
    return P6Baseline(s,"baseline-1",name,"PRIMARY",6,"2026-10-03T00:00:00Z","baseline")

def formula(s,expr="1 + 1"):
    return PersistedP6FormulaDefinition(s,"1.0.0","p6:test",FormulaDefinition("formula-1","1.0",expr,FormulaType.NUMBER),"hours",("field-1",),{"source":"test"})

def item_key(item):
    if hasattr(item, "period_id"):
        return item.period_id
    if hasattr(item, "baseline_id"):
        return item.baseline_id
    return item.formula_id

def run(repo_cls, factory, error_cls, immutable, connection):
    repo=repo_cls(connection); repo.initialize(); s=scope(); item=factory(s)
    with connection.transaction():
        assert repo.upsert(item)==item; assert repo.upsert(item)==item
    key=item_key(item)
    got=repo.get(s,key,item.version) if hasattr(item,"version") else repo.get(s,key)
    assert got==item
    listed=repo.list_versions(s,key) if hasattr(repo,"list_versions") else repo.list(s)
    assert listed==(item,)
    other=BackendScope("other-tenant",s.project_id,s.project_revision)
    got=repo.get(other,key,item.version) if hasattr(item,"version") else repo.get(other,key)
    assert got is None
    with pytest.raises(error_cls,match="REVISION_CONFLICT"):
        bad=BackendScope(s.tenant_id,s.project_id,s.project_revision+1)
        if hasattr(item,"version"): repo.get(bad,key,item.version)
        else: repo.get(bad,key)
    changed=factory(s, "Changed" if not hasattr(item,"version") else "2 + 2")
    with pytest.raises(error_cls,match=immutable): repo.upsert(changed)

def test_postgres_financial_period_scoped_immutable(connection):
    run(PostgresP6FinancialPeriodRepository,period,P6FinancialPeriodPersistenceError,"IMMUTABLE_FINANCIAL_PERIOD",connection)

def test_postgres_baseline_scoped_immutable(connection):
    run(PostgresP6BaselineRepository,baseline,P6BaselinePersistenceError,"IMMUTABLE_BASELINE",connection)

def test_postgres_formula_definition_scoped_immutable(connection):
    run(PostgresP6FormulaDefinitionRepository,formula,P6FormulaDefinitionPersistenceError,"IMMUTABLE_FORMULA_DEFINITION",connection)

@pytest.mark.parametrize("repo_cls,factory,error_cls,immutable",[
    (PostgresP6FinancialPeriodRepository,period,P6FinancialPeriodPersistenceError,"IMMUTABLE_FINANCIAL_PERIOD"),
    (PostgresP6BaselineRepository,baseline,P6BaselinePersistenceError,"IMMUTABLE_BASELINE"),
    (PostgresP6FormulaDefinitionRepository,formula,P6FormulaDefinitionPersistenceError,"IMMUTABLE_FORMULA_DEFINITION"),
])
def test_postgres_core_repository_rollback(connection,repo_cls,factory,error_cls,immutable):
    repo=repo_cls(connection); repo.initialize(); s=scope(); item=factory(s)
    with pytest.raises(RuntimeError):
        with connection.transaction(): repo.upsert(item); raise RuntimeError("force rollback")
    key=getattr(item,"period_id",getattr(item,"baseline_id",item.formula_id))
    got=repo.get(s,key,item.version) if hasattr(item,"version") else repo.get(s,key)
    assert got is None

@pytest.mark.parametrize("repo_cls,factory,error_cls,immutable",[
    (PostgresP6FinancialPeriodRepository,period,P6FinancialPeriodPersistenceError,"IMMUTABLE_FINANCIAL_PERIOD"),
    (PostgresP6BaselineRepository,baseline,P6BaselinePersistenceError,"IMMUTABLE_BASELINE"),
    (PostgresP6FormulaDefinitionRepository,formula,P6FormulaDefinitionPersistenceError,"IMMUTABLE_FORMULA_DEFINITION"),
])
def test_postgres_core_repository_concurrent_writers(postgres_dsn,repo_cls,factory,error_cls,immutable):
    s=scope(); first=factory(s,"First" if repo_cls is not PostgresP6FormulaDefinitionRepository else "1 + 1"); second=factory(s,"Second" if repo_cls is not PostgresP6FormulaDefinitionRepository else "2 + 2")
    setup,conn1,conn2=[psycopg.connect(postgres_dsn) for _ in range(3)]
    try:
        repo_cls(setup).initialize(); setup.commit(); start=threading.Barrier(2); outcomes=[]; errors=[]; lock=threading.Lock()
        def writer(conn,item):
            try:
                with conn.transaction():
                    start.wait(timeout=5); repo_cls(conn).upsert(item)
                with lock: outcomes.append("committed")
            except BaseException as exc:
                with lock: errors.append(exc)
        t1=threading.Thread(target=writer,args=(conn1,first)); t2=threading.Thread(target=writer,args=(conn2,second)); t1.start(); t2.start(); t1.join(10); t2.join(10)
        assert not t1.is_alive() and not t2.is_alive(); assert outcomes.count("committed")==1; assert len(errors)==1
        assert isinstance(errors[0],error_cls); assert str(errors[0])==immutable
    finally:
        for c in (conn1,conn2,setup): c.rollback(); c.close()
