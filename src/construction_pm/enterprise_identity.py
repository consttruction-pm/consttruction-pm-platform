from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


class EnterpriseIdentityError(ValueError):
    pass


@dataclass(frozen=True)
class EnterpriseIdentityClaims:
    subject: str
    issuer: str
    auth_method: str
    tenant_id: str
    roles: tuple[str, ...]
    email: str | None = None
    display_name: str | None = None
    contract_version: str = "1.0"

    def validate(self) -> None:
        if self.contract_version != "1.0":
            raise EnterpriseIdentityError("UNSUPPORTED_ENTERPRISE_IDENTITY_CONTRACT_VERSION")
        for name, value in (
            ("subject", self.subject),
            ("issuer", self.issuer),
            ("tenant_id", self.tenant_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise EnterpriseIdentityError(f"INVALID_ENTERPRISE_IDENTITY_{name.upper()}")
        if self.auth_method not in {"oidc", "saml"}:
            raise EnterpriseIdentityError("INVALID_ENTERPRISE_IDENTITY_AUTH_METHOD")
        if not isinstance(self.roles, tuple) or any(
            not isinstance(role, str) or not role.strip() for role in self.roles
        ):
            raise EnterpriseIdentityError("INVALID_ENTERPRISE_IDENTITY_ROLES")
        if self.email is not None and not isinstance(self.email, str):
            raise EnterpriseIdentityError("INVALID_ENTERPRISE_IDENTITY_EMAIL")
        if self.display_name is not None and not isinstance(self.display_name, str):
            raise EnterpriseIdentityError("INVALID_ENTERPRISE_IDENTITY_DISPLAY_NAME")


class EnterpriseIdentityAdapter(Protocol):
    def resolve(self, claims: Mapping[str, object]) -> EnterpriseIdentityClaims: ...


class ReferenceEnterpriseIdentityAdapter:
    """Deterministic claims-mapping seam; no OIDC/SAML SDK or token verification is embedded."""

    def __init__(self, *, issuer: str, tenant_id: str, auth_method: str = "oidc") -> None:
        self.issuer = issuer
        self.tenant_id = tenant_id
        self.auth_method = auth_method

    def resolve(self, claims: Mapping[str, object]) -> EnterpriseIdentityClaims:
        if not isinstance(claims, Mapping):
            raise EnterpriseIdentityError("INVALID_ENTERPRISE_IDENTITY_CLAIMS")
        subject = claims.get("sub")
        roles = claims.get("roles", ())
        email = claims.get("email")
        display_name = claims.get("name")
        if not isinstance(subject, str) or not subject.strip():
            raise EnterpriseIdentityError("INVALID_ENTERPRISE_IDENTITY_SUBJECT")
        if not isinstance(roles, (list, tuple)) or any(
            not isinstance(role, str) or not role.strip() for role in roles
        ):
            raise EnterpriseIdentityError("INVALID_ENTERPRISE_IDENTITY_ROLES")
        result = EnterpriseIdentityClaims(
            subject=subject,
            issuer=self.issuer,
            auth_method=self.auth_method,
            tenant_id=self.tenant_id,
            roles=tuple(dict.fromkeys(roles)),
            email=email,
            display_name=display_name,
        )
        result.validate()
        return result
