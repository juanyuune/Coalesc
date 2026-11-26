"""Coalesc, a web front end for CD-HIT."""
from __future__ import annotations

from flask import Flask

from .cdhit import Runner
from .config import Config

__version__ = "1.0.0"


def create_app(config: Config | None = None) -> Flask:
    cfg = config or Config.from_env()
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = cfg.max_upload_mb * 1024 * 1024
    app.config["COALESC"] = cfg
    app.config["RUNNER"] = Runner(cfg.bin_dir, cfg.job_timeout_s)
    cfg.upload_dir.mkdir(parents=True, exist_ok=True)
    cfg.results_dir.mkdir(parents=True, exist_ok=True)

    from .web import bp
    app.register_blueprint(bp)
    return app
