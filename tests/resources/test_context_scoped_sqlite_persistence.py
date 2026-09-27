import sqlite3
from decimal import Decimal
import pytest
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.models import Resource,ResourceAssignment,ResourceType
from construction_pm.resources.persistence import ContextScopedSQLiteResourceRepository,OptimisticLockError
A=ProjectContext("tenant-1","company-1","project-a"); B=ProjectContext("tenant-1","company-1","project-b")
def resource(): return Resource(id="R-1",code="LAB-01",name="Labor",resource_type=ResourceType.LABOR,unit="hour",rates=(),calendar_id=None,active=True)
def test_context_isolation_and_revision():
 r=ContextScopedSQLiteResourceRepository(sqlite3.connect(":memory:")); r.save_resource(A,resource()); r.save_resource(B,resource()); assert r.get_resource(A,"R-1")==resource(); assert r.get_resource(B,"R-1")==resource(); assert r.get_resource_revision(A,"R-1")==1
 with pytest.raises(OptimisticLockError): r.save_resource(A,resource(),expected_revision=0)
def test_assignment_isolation_and_revision():
 r=ContextScopedSQLiteResourceRepository(sqlite3.connect(":memory:")); r.save_resource(A,resource()); a=ResourceAssignment(activity_id="A-1",resource_id="R-1",planned_units=Decimal("10.2500"),actual_units=Decimal("4.2500")); r.save_assignment(A,a); assert r.list_assignments(A)==[a]; assert r.list_assignments(B)==[]; assert r.get_assignment_revision(A,"A-1","R-1")==1
 with pytest.raises(OptimisticLockError): r.save_assignment(A,a,expected_revision=0)
def test_invalid_context_rejected():
 r=ContextScopedSQLiteResourceRepository(sqlite3.connect(":memory:"));
 with pytest.raises(ValueError,match="project_id"): r.list_resources(ProjectContext("tenant-1","company-1",""))
