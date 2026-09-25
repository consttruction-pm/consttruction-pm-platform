from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from .models import LanguagePackManifest


class LanguagePackManager:
    """Local language-pack cache and activation manager.

    This module deliberately avoids UI, network-client and cryptographic-library
    dependencies. Network transport and signature verification are injected so
    Web/Desktop/Mobile implementations share the same deterministic lifecycle.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        signature_verifier: Callable[[Path, LanguagePackManifest], bool] | None = None,
    ) -> None:
        self.root = Path(root)
        self.packs_dir = self.root / "packs"
        self.active_dir = self.root / "active"
        self.backup_dir = self.root / "backup"
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.signature_verifier = signature_verifier or (lambda _path, _manifest: True)

    def cache_pack(
        self,
        manifest: LanguagePackManifest,
        artifact_path: str | Path,
    ) -> Path:
        """Verify and cache a complete pack artifact without activating it."""
        source = Path(artifact_path)
        if not source.is_file():
            raise FileNotFoundError(source)

        self._verify_checksum(source, manifest.integrity.checksum)
        if not self.signature_verifier(source, manifest):
            raise ValueError("language pack signature verification failed")

        package_dir = self.packs_dir / manifest.package_id / manifest.version
        package_dir.parent.mkdir(parents=True, exist_ok=True)
        staged_dir = Path(tempfile.mkdtemp(prefix=".stage-", dir=package_dir.parent))
        try:
            destination = staged_dir / "pack.artifact"
            shutil.copy2(source, destination)
            manifest_path = staged_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(_manifest_to_dict(manifest), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if package_dir.exists():
                shutil.rmtree(package_dir)
            os.replace(staged_dir, package_dir)
        except Exception:
            shutil.rmtree(staged_dir, ignore_errors=True)
            raise
        return package_dir

    def activate(self, manifest: LanguagePackManifest) -> Path:
        """Atomically activate a verified cached pack."""
        package_dir = self.packs_dir / manifest.package_id / manifest.version
        if not package_dir.is_dir():
            raise FileNotFoundError(
                f"cached pack not found: {manifest.package_id}@{manifest.version}"
            )

        source_artifact = package_dir / "pack.artifact"
        self._verify_checksum(source_artifact, manifest.integrity.checksum)
        if not self.signature_verifier(source_artifact, manifest):
            raise ValueError("language pack signature verification failed")

        active_package_dir = self.active_dir / manifest.package_id
        staged = Path(tempfile.mkdtemp(prefix=".activate-", dir=self.active_dir))
        staged_target = staged / "active"
        shutil.copytree(package_dir, staged_target)

        try:
            if active_package_dir.exists():
                backup_target = self.backup_dir / manifest.package_id
                if backup_target.exists():
                    shutil.rmtree(backup_target)
                os.replace(active_package_dir, backup_target)
            os.replace(staged_target, active_package_dir)
        except Exception:
            if active_package_dir.exists():
                shutil.rmtree(active_package_dir)
            backup_target = self.backup_dir / manifest.package_id
            if backup_target.exists():
                os.replace(backup_target, active_package_dir)
            raise
        finally:
            shutil.rmtree(staged, ignore_errors=True)

        return active_package_dir

    def rollback(self, package_id: str) -> Path:
        """Restore the previous active pack atomically."""
        backup = self.backup_dir / package_id
        active = self.active_dir / package_id
        if not backup.is_dir():
            raise FileNotFoundError(f"no rollback pack available for {package_id}")

        staged = Path(tempfile.mkdtemp(prefix=".rollback-", dir=self.active_dir))
        try:
            staged_target = staged / "active"
            shutil.copytree(backup, staged_target)
            if active.exists():
                shutil.rmtree(active)
            os.replace(staged_target, active)
            return active
        finally:
            shutil.rmtree(staged, ignore_errors=True)

    def installed_versions(self, package_id: str) -> list[str]:
        base = self.packs_dir / package_id
        if not base.is_dir():
            return []
        return sorted(p.name for p in base.iterdir() if p.is_dir())

    @staticmethod
    def _verify_checksum(path: Path, expected: str) -> None:
        prefix, separator, digest = expected.partition(":")
        if separator == "" or prefix.lower() != "sha256" or len(digest) != 64:
            raise ValueError("only sha256:<64-hex> checksums are supported")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual.lower() != digest.lower():
            raise ValueError("language pack checksum mismatch")


def _manifest_to_dict(manifest: LanguagePackManifest) -> dict:
    return {
        "package_id": manifest.package_id,
        "language_tag": manifest.language_tag,
        "version": manifest.version,
        "app_compatibility": {
            "min_version": manifest.app_compatibility.min_version,
            "max_version": manifest.app_compatibility.max_version,
        },
        "artifact": {
            "format": manifest.artifact.format,
            "compressed_size_bytes": manifest.artifact.compressed_size_bytes,
            "download_uri": manifest.artifact.download_uri,
            "delta_from": manifest.artifact.delta_from,
        },
        "resources": {
            "translation": manifest.resources.translation,
            "glossary": manifest.resources.glossary,
            "help": manifest.resources.help,
            "reports": manifest.resources.reports,
            "voice_input": manifest.resources.voice_input,
            "voice_output": manifest.resources.voice_output,
            "offline_ai_model": manifest.resources.offline_ai_model,
        },
        "integrity": {
            "checksum": manifest.integrity.checksum,
            "signature": manifest.integrity.signature,
            "signing_key_id": manifest.integrity.signing_key_id,
        },
        "capabilities": {
            "ui": manifest.capabilities.ui,
            "help": manifest.capabilities.help,
            "ai_text": manifest.capabilities.ai_text,
            "voice_input": manifest.capabilities.voice_input,
            "voice_output": manifest.capabilities.voice_output,
            "offline_ai": manifest.capabilities.offline_ai,
        },
        "rollback": {
            "previous_version": manifest.rollback.previous_version,
            "rollback_supported": manifest.rollback.rollback_supported,
        },
    }
