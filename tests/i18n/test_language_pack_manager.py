from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from construction_pm.i18n import LanguagePackManager, LanguagePackManifest


def manifest_for(path: Path, version: str = "1.0.0") -> LanguagePackManifest:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return LanguagePackManifest.from_dict(
        {
            "package_id": "construction-pm.language.fa",
            "language_tag": "fa",
            "version": version,
            "app_compatibility": {"min_version": "0.1.0", "max_version": None},
            "artifact": {
                "format": "zip",
                "compressed_size_bytes": path.stat().st_size,
                "download_uri": "https://example.invalid/fa.zip",
                "delta_from": None,
            },
            "resources": {
                "translation": "translations.json",
                "glossary": "glossary.json",
                "help": "help.json",
                "reports": "reports.json",
            },
            "integrity": {
                "checksum": f"sha256:{digest}",
                "signature": "test-signature",
                "signing_key_id": "test-key",
            },
            "capabilities": {
                "ui": True,
                "help": True,
                "ai_text": True,
                "voice_input": True,
                "voice_output": True,
                "offline_ai": False,
            },
            "rollback": {
                "previous_version": None,
                "rollback_supported": True,
            },
        }
    )


def test_manifest_requires_core_fields() -> None:
    with pytest.raises(ValueError):
        LanguagePackManifest.from_dict({"package_id": "x"})


def test_cache_activate_and_rollback(tmp_path: Path) -> None:
    manager = LanguagePackManager(tmp_path)
    artifact_v1 = tmp_path / "fa-v1.zip"
    artifact_v1.write_bytes(b"language-pack-v1")
    m1 = manifest_for(artifact_v1, "1.0.0")

    cached1 = manager.cache_pack(m1, artifact_v1)
    assert cached1.is_dir()

    active1 = manager.activate(m1)
    assert (active1 / "pack.artifact").read_bytes() == b"language-pack-v1"

    artifact_v2 = tmp_path / "fa-v2.zip"
    artifact_v2.write_bytes(b"language-pack-v2")
    m2 = manifest_for(artifact_v2, "1.1.0")
    manager.cache_pack(m2, artifact_v2)
    active2 = manager.activate(m2)

    assert (active2 / "pack.artifact").read_bytes() == b"language-pack-v2"

    restored = manager.rollback(m2.package_id)
    assert (restored / "pack.artifact").read_bytes() == b"language-pack-v1"


def test_checksum_mismatch_rejected(tmp_path: Path) -> None:
    manager = LanguagePackManager(tmp_path)
    artifact = tmp_path / "bad.zip"
    artifact.write_bytes(b"actual")
    manifest = LanguagePackManifest.from_dict(
        {
            "package_id": "construction-pm.language.fa",
            "language_tag": "fa",
            "version": "1.0.0",
            "app_compatibility": {"min_version": "0.1.0"},
            "artifact": {
                "format": "zip",
                "compressed_size_bytes": 6,
                "download_uri": "https://example.invalid/fa.zip",
            },
            "resources": {
                "translation": "translations.json",
                "glossary": "glossary.json",
                "help": "help.json",
                "reports": "reports.json",
            },
            "integrity": {"checksum": "sha256:" + "0" * 64, "signature": "x"},
            "capabilities": {
                "ui": True,
                "help": True,
                "ai_text": True,
                "voice_input": False,
                "voice_output": False,
                "offline_ai": False,
            },
        }
    )
    with pytest.raises(ValueError, match="checksum mismatch"):
        manager.cache_pack(manifest, artifact)
