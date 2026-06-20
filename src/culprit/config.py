"""Central configuration, loaded from environment / .env.

Everything tunable lives here so the rest of the codebase never reads
``os.environ`` directly. Import the singleton:

    from culprit.config import settings
    settings.tau, settings.judge_model, settings.db_path
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = .../CULPRIT_AINS (this file is src/culprit/config.py).
REPO_ROOT: Path = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for the whole pipeline.

    Field names map to ``CULPRIT_<UPPER>`` environment variables (plus the
    bare ``NVIDIA_API_KEY``). Relative paths are resolved against the repo
    root so commands behave the same regardless of the working directory.
    """

    model_config = SettingsConfigDict(
        env_prefix="CULPRIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM provider (NVIDIA NIM, OpenAI-compatible API) ---
    nvidia_api_key: str | None = Field(default=None, alias="NVIDIA_API_KEY")
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    # --- Models ---
    judge_model: str = "deepseek-ai/deepseek-v4-pro"
    agent_model: str = "deepseek-ai/deepseek-v4-pro"
    tagger_model: str = "deepseek-ai/deepseek-v4-pro"

    # --- Evaluation knobs ---
    tau: float = Field(default=0.7, ge=0.0, le=1.0)
    judge_samples: int = Field(default=5, ge=1)

    # --- Storage / paths ---
    db_path: Path = Path("data/culprit.db")
    output_dir: Path = Path("data/outputs")
    contracts_dir: Path = REPO_ROOT / "src" / "culprit" / "contracts"

    @field_validator("db_path", "output_dir", "contracts_dir")
    @classmethod
    def _resolve_against_root(cls, value: Path) -> Path:
        """Anchor relative paths to the repo root, leave absolute ones alone."""
        return value if value.is_absolute() else REPO_ROOT / value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton (cached after first load)."""
    return Settings()


settings = get_settings()
