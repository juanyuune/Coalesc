"""Settings from COALESC_* environment variables."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

_TRUE = {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from None


def discover_bin_dir() -> Path | None:
    for name in ("cd-hit-est", "cd-hit"):
        found = shutil.which(name)
        if found:
            return Path(found).parent
    return None


@dataclass(frozen=True)
class Config:
    bin_dir: Path | None = None          # folder with cd-hit, cd-hit-est, ... (and clstr_rev.pl)
    upload_dir: Path = Path("instance/uploads")
    results_dir: Path = Path("instance/results")
    max_upload_mb: int = 500
    job_timeout_s: int = 7200            # per CD-HIT run
    keep_uploads: bool = False           # delete uploaded files when a job ends
    host: str = "127.0.0.1"
    port: int = 8001

    @classmethod
    def from_env(cls) -> "Config":
        bin_env = os.environ.get("COALESC_BIN_DIR", "").strip()
        return cls(
            bin_dir=Path(bin_env) if bin_env else discover_bin_dir(),
            upload_dir=Path(os.environ.get("COALESC_UPLOAD_DIR", "instance/uploads")),
            results_dir=Path(os.environ.get("COALESC_RESULTS_DIR", "instance/results")),
            max_upload_mb=_int_env("COALESC_MAX_UPLOAD_MB", 500),
            job_timeout_s=_int_env("COALESC_JOB_TIMEOUT_S", 7200),
            keep_uploads=os.environ.get("COALESC_KEEP_UPLOADS", "").strip().lower() in _TRUE,
            host=os.environ.get("COALESC_HOST", "127.0.0.1"),
            port=_int_env("COALESC_PORT", 8001),
        )
