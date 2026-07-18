from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ASTERISM_", env_file=".env", extra="ignore")

    env: str = "development"
    deployment_profile: Literal["development", "local-private"] = "development"
    database_url: str = "sqlite:///./data/asterism.db"
    artifact_root: Path = Path("./data/artifacts")
    token_file: Path = Path("~/.evolastra/companion-token")
    api_token: SecretStr | None = None
    pairing_ttl_seconds: int = Field(default=300, ge=60, le=1_800)
    session_ttl_seconds: int = Field(default=28_800, ge=300, le=86_400)
    codex_spool: Path = Path("~/.codex/evolastra-outbox")
    drain_codex_spool: bool = False
    serve_web: bool = False
    web_root: Path = Path("./apps/web/dist")
    companion_port: int = Field(default=8000, ge=1_024, le=65_535)
    instance_id: str = "development"
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )
    allowed_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["127.0.0.1", "localhost", "testserver"]
    )
    max_request_bytes: int = 5 * 1024 * 1024
    capture_content: bool = False
    codex_dispatch_enabled: bool = False
    codex_workspace_root: Path = Path.cwd()

    @field_validator("allowed_origins", "allowed_hosts", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def auth_required(self) -> bool:
        return self.deployment_profile != "development" or self.production

    @property
    def local_data(self) -> bool:
        return True


@lru_cache
def get_settings() -> Settings:
    return Settings()
