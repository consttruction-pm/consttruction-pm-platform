from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, Permission, default_project_policy

def test_default_project_policy_grants_viewer_read_only():
    p=default_project_policy(); c=AuthorizationContext("tenant-1","project-1","user-1",frozenset({"viewer"}))
    assert p.is_allowed(c,Permission.PROJECT_READ); assert not p.is_allowed(c,Permission.PROJECT_WRITE)

def test_default_project_policy_grants_planner_schedule():
    p=default_project_policy(); c=AuthorizationContext("tenant-1","project-1","user-1",frozenset({"planner"}))
    assert p.is_allowed(c,Permission.PROJECT_SCHEDULE)

def test_default_project_policy_grants_admin_all_project_permissions():
    p=default_project_policy(); c=AuthorizationContext("tenant-1","project-1","user-1",frozenset({"project_admin"}))
    assert all(p.is_allowed(c,x) for x in Permission)

def test_authorization_context_rejects_empty_scope():
    p=default_project_policy(); c=AuthorizationContext(" ","project-1","user-1",frozenset({"viewer"}))
    try: p.is_allowed(c,Permission.PROJECT_READ)
    except AuthorizationError as e: assert str(e)=="INVALID_AUTHORIZATION_TENANT_ID"
    else: raise AssertionError

def test_authorization_context_rejects_invalid_roles():
    p=default_project_policy(); c=AuthorizationContext("tenant-1","project-1","user-1",frozenset({"viewer",7}))
    try: p.is_allowed(c,Permission.PROJECT_READ)
    except AuthorizationError as e: assert str(e)=="INVALID_AUTHORIZATION_ROLES"
    else: raise AssertionError
