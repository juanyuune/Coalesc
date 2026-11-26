"""HTTP routes: the page, /run, /download."""
from __future__ import annotations

import os

from flask import Blueprint, current_app, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from .cdhit import MODES, allowed_filename, count_seqs, sniff_seq_type
from .jobs import JobError, Params, new_job_id, run_job

bp = Blueprint("coalesc", __name__)


class FormError(ValueError):
    pass


def _num(name: str, cast, default, lo=None, hi=None):
    raw = request.form.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        val = cast(raw)
    except ValueError:
        raise FormError(f"Invalid value for {name}: {raw!r}.") from None
    if val != val or (lo is not None and val < lo) or (hi is not None and val > hi):
        raise FormError(f"Value for {name} is out of range.")
    return val


def _choice(name: str, allowed: set[str], default: str) -> str:
    raw = request.form.get(name, default).strip()
    if raw not in allowed:
        raise FormError(f"Invalid value for {name}: {raw!r}.")
    return raw


def parse_params() -> Params:
    mode_name = request.form.get("mode", "cd-hit")
    mode = MODES.get(mode_name)
    if mode is None:
        raise FormError("Unknown mode.")
    nuc = mode.nucleotide
    return Params(
        mode=mode,
        identity=_num("identity", float, 0.90, 0.80 if nuc else 0.40, 1.0),
        word_size=_num("word_size", int, 0, 0, 11),
        num_runs=_num("num_runs", int, 1, 1, 3),
        identity2=_num("identity2", float, 0.80, 0.80 if nuc else 0.40, 1.0),
        identity3=_num("identity3", float, 0.60, 0.80 if nuc else 0.40, 1.0),
        glob_id=_choice("global_identity", {"0", "1"}, "1"),
        best_cl=_choice("best_cluster", {"0", "1"}, "1"),
        strand=_choice("strand", {"0", "1"}, "1"),
        annot=str(_num("annot", int, 0, 0, 1000)),
        bandwidth=_num("bandwidth", int, 20, 1, 1000),
        skip_len=_num("skip_len", int, 10, 1, 1000),
        aL=_num("aL", float, 0.0, 0.0, 1.0),
        AL=_num("AL", int, 99999999, 0),
        aS=_num("aS", float, 0.0, 0.0, 1.0),
        AS=_num("AS", int, 99999999, 0),
        s_sim=_num("s_sim", float, 0.0, 0.0, 1.0),
        S_diff=_num("S_diff", int, 99999999, 0),
        s2val=_num("s2val", float, 1.0, 0.0, 1.0),
        S2val=_num("S2val", int, 0, 0),
        threads=_num("threads", int, 8, 0, 256),
        memory=_num("memory", int, 4000, 0),
    )


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@bp.post("/run")
def run():
    cfg = current_app.config["COALESC"]
    runner = current_app.config["RUNNER"]

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
    f = request.files["file"]
    if not f.filename or not allowed_filename(f.filename):
        return jsonify({"error": "Invalid file type. Use .fasta .fa .faa .fna .txt"}), 400
    try:
        params = parse_params()
    except FormError as exc:
        return jsonify({"error": str(exc)}), 400

    job = new_job_id()
    input1 = os.path.join(cfg.upload_dir, f"{job}_db1_{secure_filename(f.filename)}")
    input2 = None
    saved = [input1]
    f.save(input1)
    try:
        n_input = count_seqs(input1)
        if n_input == 0:
            return jsonify({"error": "No sequences found. Check the file is valid FASTA format."}), 400

        detected = sniff_seq_type(input1)
        wanted = "nuc" if params.mode.nucleotide else "prot"
        if detected and detected != wanted:
            if detected == "prot":
                msg = ("This file looks like protein, but Sequence type is set to DNA or RNA. "
                       "Switch it to Protein and run again.")
            else:
                msg = ("This file looks like DNA or RNA, but Sequence type is set to Protein. "
                       "Switch it to DNA or RNA and run again.")
            return jsonify({"error": msg}), 400

        f2 = request.files.get("file2")
        if params.mode.two_d and f2 and f2.filename and allowed_filename(f2.filename):
            input2 = os.path.join(cfg.upload_dir, f"{job}_db2_{secure_filename(f2.filename)}")
            saved.append(input2)
            f2.save(input2)

        result = run_job(runner, params, job, input1, input2, str(cfg.results_dir), n_input)
        return jsonify(result.as_json())
    except JobError as exc:
        return jsonify({"error": str(exc)}), exc.status
    finally:
        if not cfg.keep_uploads:
            for path in saved:
                try:
                    os.remove(path)
                except OSError:
                    pass


@bp.get("/download/<job_id>/<filetype>")
def download(job_id: str, filetype: str):
    cfg = current_app.config["COALESC"]
    if len(job_id) > 9 or not job_id or not all(c in "0123456789abcdef-" for c in job_id):
        return "Invalid job ID", 400
    if filetype == "fasta":
        path = os.path.join(cfg.results_dir, f"{job_id}_result.fasta")
        name = f"cdhit_{job_id}_representatives.fasta"
    elif filetype == "clstr":
        path = os.path.join(cfg.results_dir, f"{job_id}_result.fasta.clstr")
        name = f"cdhit_{job_id}_clusters.clstr"
    else:
        return "Invalid file type", 400
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True, download_name=name)
