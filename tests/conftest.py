import io
import shutil
from pathlib import Path

import pytest

from coalesc import create_app
from coalesc.config import Config

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
BIN_DIR = Config.from_env().bin_dir
HAVE_CDHIT = BIN_DIR is not None
needs_cdhit = pytest.mark.skipif(not HAVE_CDHIT, reason="CD-HIT (cd-hit, cd-hit-est) not installed")


@pytest.fixture
def cfg(tmp_path):
    return Config(bin_dir=BIN_DIR, upload_dir=tmp_path / "up", results_dir=tmp_path / "res",
                  job_timeout_s=120)


@pytest.fixture
def client(cfg):
    return create_app(cfg).test_client()


@pytest.fixture
def post(client):
    def _post(fasta, mode="cd-hit", name="x.fasta", **fields):
        data = {"file": (io.BytesIO(Path(EXAMPLES / fasta).read_bytes() if isinstance(fasta, str) else fasta), name),
                "mode": mode, "threads": "2"}
        data.update({k: (v if not isinstance(v, Path) else (io.BytesIO(v.read_bytes()), v.name))
                     for k, v in fields.items()})
        return client.post("/run", data=data, content_type="multipart/form-data")
    return _post
