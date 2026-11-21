from construction_pm.application.authorization import AuthorizationContext
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_access import resource_is_accessible, require_resource_access
from construction_pm.p6_resource_master_repository import P6Resource
from construction_pm.application.authorization import AuthorizationError


class ResourceRepository:
    def __init__(self, items):
        self.items = tuple(items)

    def list(self, tenant_id, project_id, project_revision):
        return tuple(
            item for item in self.items
            if (item.tenant_id, item.project_id, item.project_revision)
            == (tenant_id, project_id, project_revision)
        )


class Policy:
    def __init__(self, roots):
        self.roots = set(roots)

    def can_access_resource(self, context, resource_id, ancestor_resource_ids):
        return bool(self.roots.intersection(ancestor_resource_ids))


def _context():
    return AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"}))


def _scope():
    return BackendScope("tenant-1", "project-1", 4)


def _resource(resource_id, parent=None, *, tenant="tenant-1"):
    return P6Resource(tenant, "project-1", 4, resource_id, resource_id, parent_resource_id=parent)


def test_resource_access_resolves_ancestry_from_scoped_repository():
    repo = ResourceRepository((_resource("root"), _resource("child", "root"), _resource("sibling")))
    policy = Policy({"root"})
    assert resource_is_accessible(policy, repo, _scope(), "child", _context())
    assert not resource_is_accessible(policy, repo, _scope(), "sibling", _context())


def test_resource_access_fails_closed_for_missing_resource_repository_or_record():
    policy = Policy({"root"})
    assert not resource_is_accessible(policy, None, _scope(), "root", _context())
    assert not resource_is_accessible(policy, ResourceRepository(()), _scope(), "root", _context())


def test_resource_access_rejects_cross_scope_and_malformed_hierarchy():
    repo = ResourceRepository((
        _resource("root"), _resource("child", "root"),
        _resource("foreign", tenant="tenant-2"),
    ))
    policy = Policy({"root"})
    assert not resource_is_accessible(policy, repo, _scope(), "foreign", _context())
    cyclic = ResourceRepository((_resource("a", "b"), _resource("b", "a")))
    assert not resource_is_accessible(policy, cyclic, _scope(), "a", _context())


def test_require_resource_access_raises_stable_authorization_error():
    policy = Policy(set())
    repo = ResourceRepository((_resource("root"),))
    try:
        require_resource_access(policy, repo, _scope(), "root", _context())
    except AuthorizationError as exc:
        assert "RESOURCE_ACCESS_DENIED" in str(exc)
    else:
        raise AssertionError("out-of-scope resource access must be denied")
