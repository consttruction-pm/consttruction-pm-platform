from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ResourcePersistenceConfig:
    """Infrastructure configuration for Resource/Cost persistence."""

    backend: str = "sqlite"
    database_url: str = ":memory:"

    @classmethod
    def from_environment(cls) -> "ResourcePersistenceConfig":
        return cls(
            backend=os.getenv("CONSTRUCTION_PM_RESOURCE_DB_BACKEND", "sqlite"),
            database_url=os.getenv("CONSTRUCTION_PM_RESOURCE_DATABASE_URL", ":memory:"),
        )

    def validate(self) -> None:
        if self.backend != "sqlite":
            raise ValueError(f"Unsupported resource persistence backend: {self.backend}")
        if not self.database_url:
            raise ValueError("Resource persistence database URL cannot be empty")
