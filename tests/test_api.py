"""End-to-end tests of the HTTP API against the real CD-HIT programs."""
import io
import json
from pathlib import Path

import pytest

from conftest import EXAMPLES, needs_cdhit

pytestmark = needs_cdhit


def clstr_text(client, job):
    return client.get(f"/download/{job}/clstr").data.decode()


def test_page_and_health(client):
    r = client.get("/")
    assert r.status_code == 200 and b"Coalesc" in r.data
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_protein_clustering(post, client):
    r = post("protein_example.fasta", identity="0.9")
    assert r.status_code == 200
    j = r.get_json()
    assert set(j) == {"job_id", "n_input", "n_output", "n_clusters", "reduction", "clstr_full", "log"}
    assert j["n_input"] == 80 and j["n_clusters"] == j["n_output"] == 20
    assert j["reduction"] == 75.0
    assert client.get(f"/download/{j['job_id']}/fasta").status_code == 200
    assert clstr_text(client, j["job_id"]).count(">Cluster") == 20


def test_dna_clustering(post):
    j = post("dna_example.fasta", mode="cd-hit-est", identity="0.95").get_json()
    assert j["n_input"] == 80 and j["n_clusters"] == 20


def test_dna_both_strands_flag_is_accepted(post):
    assert post("dna_example.fasta", mode="cd-hit-est", identity="0.95", strand="0").status_code == 200


def test_compare_two_databases(post):
    r = post("dna_example.fasta", mode="cd-hit-est-2d", identity="0.95",
             file2=EXAMPLES / "dna_example_set2.fasta")
    assert r.status_code == 200, r.get_json()


def test_levels_merges_clusters_across_passes(post, client):
    j = post("dna_levels_example.fasta", mode="h-cd-hit-est", identity="0.95", identity2="0.85",
             identity3="0.80", num_runs="3").get_json()
    assert j["clstr_full"] is True
    text = clstr_text(client, j["job_id"])
    members = [l for l in text.splitlines() if l.strip() and not l.startswith(">")]
    assert len(members) == j["n_input"] == 120          # every original sequence is listed


def test_levels_protein(post):
    j = post("protein_example.fasta", mode="h-cd-hit", identity="0.9", identity2="0.7", num_runs="2").get_json()
    assert j["clstr_full"] is True and j["n_output"] <= 20


def test_levels_without_merge_script_falls_back(cfg, post, client, monkeypatch):
    runner = client.application.config["RUNNER"]
    real_find = runner.find
    monkeypatch.setattr(runner, "find", lambda n: None if n == "clstr_rev.pl" else real_find(n))
    j = post("dna_levels_example.fasta", mode="h-cd-hit-est", identity="0.95", identity2="0.9",
             num_runs="2").get_json()
    assert j["clstr_full"] is False and j["n_clusters"] > 0


def test_protein_file_with_dna_mode_is_rejected(post):
    r = post("protein_example.fasta", mode="cd-hit-est")
    assert r.status_code == 400 and "looks like protein" in r.get_json()["error"]


def test_dna_file_with_protein_mode_is_rejected(post, cfg):
    r = post("dna_example.fasta", mode="cd-hit")
    assert r.status_code == 400 and "looks like DNA" in r.get_json()["error"]
    assert list(cfg.upload_dir.iterdir()) == []         # nothing left behind


def test_uploads_are_deleted_after_a_job(post, cfg):
    assert post("protein_example.fasta").status_code == 200
    assert list(cfg.upload_dir.iterdir()) == []


@pytest.mark.parametrize("mode", ["../../../../bin/echo", "/bin/echo", "CD-HIT", "", "cd-hit ", "h-cd-hit-x"])
def test_unknown_mode_is_rejected(post, mode, cfg):
    r = post("protein_example.fasta", mode=mode)
    assert r.status_code == 400 and r.get_json()["error"] == "Unknown mode."
    assert list(cfg.upload_dir.iterdir()) == []


@pytest.mark.parametrize("field,value", [
    ("identity", "abc"), ("identity", "0.5e"), ("identity", "nan"), ("identity", "2"),
    ("threads", "-1"), ("threads", "1; rm -rf /"), ("memory", "x"), ("word_size", "99"),
    ("global_identity", "5"), ("bandwidth", "0"), ("num_runs", "9"),
])
def test_bad_numbers_are_rejected(post, field, value):
    r = post("protein_example.fasta", **{field: value})
    assert r.status_code == 400 and "error" in r.get_json()


def test_identity_floors_match_cdhit(post):
    assert post("dna_example.fasta", mode="cd-hit-est", identity="0.79").status_code == 400
    assert post("protein_example.fasta", identity="0.39").status_code == 400
    assert post("protein_example.fasta", identity="0.40", word_size="2").status_code == 200


def test_bad_uploads(post):
    assert post(b"", name="x.fasta").get_json()["error"].startswith("No sequences")
    assert post(b">a\nMKV\n", name="x.exe").status_code == 400


def test_missing_file(client):
    assert client.post("/run", data={"mode": "cd-hit"}).status_code == 400


@pytest.mark.parametrize("path", ["/download/../etc/passwd/fasta", "/download/zzzz/fasta",
                                  "/download/abcd1234abcd/fasta", "/download/abcd1234/other",
                                  "/download/abcd1234/fasta"])
def test_download_rejects_bad_requests(client, path):
    assert client.get(path).status_code in (400, 404)


def test_no_cors_headers(client):
    r = client.get("/", headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in r.headers
