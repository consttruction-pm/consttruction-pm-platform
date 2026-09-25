from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PackArtifact:
    format: str
    compressed_size_bytes: int
    download_uri: str
    delta_from: str | None = None


@dataclass(frozen=True)
class PackIntegrity:
    checksum: str
    signature: str
    signing_key_id: str | None = None


@dataclass(frozen=True)
class PackResources:
    translation: str
    glossary: str
    help: str
    reports: str
    voice_input: str | None = None
    voice_output: str | None = None
    offline_ai_model: str | None = None


@dataclass(frozen=True)
class PackCapabilities:
    ui: bool
    help: bool
    ai_text: bool
    voice_input: bool
    voice_output: bool
    offline_ai: bool


@dataclass(frozen=True)
class AppCompatibility:
    min_version: str
    max_version: str | None = None


@dataclass(frozen=True)
class RollbackInfo:
    previous_version: str | None = None
    rollback_supported: bool = True


@dataclass(frozen=True)
class LanguagePackManifest:
    package_id: str
    language_tag: str
    version: str
    app_compatibility: AppCompatibility
    artifact: PackArtifact
    resources: PackResources
    integrity: PackIntegrity
    capabilities: PackCapabilities
    rollback: RollbackInfo = field(default_factory=RollbackInfo)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LanguagePackManifest":
        required = {
            "package_id",
            "language_tag",
            "version",
            "app_compatibility",
            "artifact",
            "resources",
            "integrity",
            "capabilities",
        }
        missing = required.difference(payload)
        if missing:
            raise ValueError(f"missing manifest fields: {sorted(missing)}")

        compatibility = payload["app_compatibility"]
        artifact = payload["artifact"]
        resources = payload["resources"]
        integrity = payload["integrity"]
        capabilities = payload["capabilities"]
        rollback = payload.get("rollback") or {}

        return cls(
            package_id=_require_str(payload, "package_id"),
            language_tag=_require_str(payload, "language_tag"),
            version=_require_str(payload, "version"),
            app_compatibility=AppCompatibility(
                min_version=_require_str(compatibility, "min_version"),
                max_version=_optional_str(compatibility, "max_version"),
            ),
            artifact=PackArtifact(
                format=_require_str(artifact, "format"),
                compressed_size_bytes=_require_non_negative_int(
                    artifact, "compressed_size_bytes"
                ),
                download_uri=_require_str(artifact, "download_uri"),
                delta_from=_optional_str(artifact, "delta_from"),
            ),
            resources=PackResources(
                translation=_require_str(resources, "translation"),
                glossary=_require_str(resources, "glossary"),
                help=_require_str(resources, "help"),
                reports=_require_str(resources, "reports"),
                voice_input=_optional_str(resources, "voice_input"),
                voice_output=_optional_str(resources, "voice_output"),
                offline_ai_model=_optional_str(resources, "offline_ai_model"),
            ),
            integrity=PackIntegrity(
                checksum=_require_str(integrity, "checksum"),
                signature=_require_str(integrity, "signature"),
                signing_key_id=_optional_str(integrity, "signing_key_id"),
            ),
            capabilities=PackCapabilities(
                ui=_require_bool(capabilities, "ui"),
                help=_require_bool(capabilities, "help"),
                ai_text=_require_bool(capabilities, "ai_text"),
                voice_input=_require_bool(capabilities, "voice_input"),
                voice_output=_require_bool(capabilities, "voice_output"),
                offline_ai=_require_bool(capabilities, "offline_ai"),
            ),
            rollback=RollbackInfo(
                previous_version=_optional_str(rollback, "previous_version"),
                rollback_supported=bool(rollback.get("rollback_supported", True)),
            ),
        )


def _require_str(value: dict[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return result.strip()


def _optional_str(value: dict[str, Any], key: str) -> str | None:
    result = value.get(key)
    if result is None:
        return None
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"{key} must be a non-empty string or null")
    return result.strip()


def _require_bool(value: dict[str, Any], key: str) -> bool:
    result = value.get(key)
    if not isinstance(result, bool):
        raise ValueError(f"{key} must be a boolean")
    return result


def _require_non_negative_int(value: dict[str, Any], key: str) -> int:
    result = value.get(key)
    if not isinstance(result, int) or isinstance(result, bool) or result < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return result
