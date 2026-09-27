from construction_pm.enterprise_identity import (
    EnterpriseIdentityError,
    ReferenceEnterpriseIdentityAdapter,
)


def test_reference_identity_adapter_maps_oidc_claims_and_preserves_tenant():
    result = ReferenceEnterpriseIdentityAdapter(
        issuer="https://idp.example", tenant_id="tenant-1"
    ).resolve({"sub":"user-7","tenant_id":"tenant-1","roles":["admin","admin","viewer"],"email":"u@example.com","name":"User"})
    assert result.subject == "user-7"
    assert result.issuer == "https://idp.example"
    assert result.auth_method == "oidc"
    assert result.tenant_id == "tenant-1"
    assert result.roles == ("admin","viewer")
    assert result.email == "u@example.com"


def test_reference_identity_adapter_supports_saml_as_same_platform_contract():
    result = ReferenceEnterpriseIdentityAdapter(
        issuer="https://sso.example", tenant_id="tenant-2", auth_method="saml"
    ).resolve({"sub":"user-8","tenant_id":"tenant-2","roles":["project.viewer"]})
    assert result.auth_method == "saml"
    assert result.tenant_id == "tenant-2"


def test_identity_adapter_rejects_missing_subject():
    try:
        ReferenceEnterpriseIdentityAdapter(
            issuer="https://idp.example", tenant_id="tenant-1"
        ).resolve({"tenant_id":"tenant-1","roles":["viewer"]})
    except EnterpriseIdentityError as exc:
        assert str(exc) == "INVALID_ENTERPRISE_IDENTITY_SUBJECT"
    else:
        raise AssertionError("missing subject must be rejected")


def test_identity_adapter_rejects_invalid_roles():
    try:
        ReferenceEnterpriseIdentityAdapter(
            issuer="https://idp.example", tenant_id="tenant-1"
        ).resolve({"sub":"user-1","tenant_id":"tenant-1","roles":["viewer", 7]})
    except EnterpriseIdentityError as exc:
        assert str(exc) == "INVALID_ENTERPRISE_IDENTITY_ROLES"
    else:
        raise AssertionError("invalid roles must be rejected")


def test_identity_adapter_rejects_missing_tenant_claim():
    try:
        ReferenceEnterpriseIdentityAdapter(
            issuer="https://idp.example", tenant_id="tenant-1"
        ).resolve({"sub":"user-9","roles":["viewer"]})
    except EnterpriseIdentityError as exc:
        assert str(exc) == "INVALID_ENTERPRISE_IDENTITY_TENANT_ID"
    else:
        raise AssertionError("missing tenant claim must be rejected")


def test_identity_adapter_rejects_cross_tenant_claim():
    try:
        ReferenceEnterpriseIdentityAdapter(
            issuer="https://idp.example", tenant_id="tenant-1"
        ).resolve({"sub":"user-10","tenant_id":"tenant-2","roles":["viewer"]})
    except EnterpriseIdentityError as exc:
        assert str(exc) == "ENTERPRISE_IDENTITY_TENANT_MISMATCH"
    else:
        raise AssertionError("cross-tenant identity claim must be rejected")
