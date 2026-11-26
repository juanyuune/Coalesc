"""Build the CD-HIT command lines and run them."""
from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field

from .cdhit import (Mode, Runner, auto_word_size, count_clusters, count_seqs,
                    merge_pass_clstrs)


class JobError(Exception):
    def __init__(self, message: str, status: int = 500):
        super().__init__(message)
        self.status = status


@dataclass
class Params:
    """Form values after validation."""

    mode: Mode
    identity: float = 0.90
    word_size: int = 0                  # 0 = choose automatically
    num_runs: int = 1
    identity2: float = 0.80
    identity3: float = 0.60
    glob_id: str = "1"
    best_cl: str = "1"
    strand: str = "1"
    annot: str = "0"
    bandwidth: int = 20
    skip_len: int = 10
    aL: float = 0.0
    AL: int = 99999999
    aS: float = 0.0
    AS: int = 99999999
    s_sim: float = 0.0
    S_diff: int = 99999999
    s2val: float = 1.0
    S2val: int = 0
    threads: int = 8
    memory: int = 4000


@dataclass
class JobResult:
    job_id: str
    n_input: int
    n_output: int
    n_clusters: int
    reduction: float
    clstr_full: bool
    log: str = field(default="", repr=False)

    def as_json(self) -> dict:
        return {
            "job_id": self.job_id,
            "n_input": self.n_input,
            "n_output": self.n_output,
            "n_clusters": self.n_clusters,
            "reduction": self.reduction,
            "clstr_full": self.clstr_full,
            "log": self.log[-4000:],
        }


def new_job_id() -> str:
    return str(uuid.uuid4())[:8]


def _common_flags(p: Params, word_size: int) -> list[str]:
    flags = [
        "-n", str(word_size), "-T", str(p.threads), "-M", str(p.memory),
        "-G", p.glob_id, "-g", p.best_cl, "-b", str(p.bandwidth), "-l", str(p.skip_len),
        "-d", p.annot,
        "-aL", str(p.aL), "-AL", str(p.AL), "-aS", str(p.aS), "-AS", str(p.AS),
        "-s", str(p.s_sim), "-S", str(p.S_diff),
    ]
    if p.mode.nucleotide:
        flags += ["-r", p.strand]
    return flags


def run_job(runner: Runner, p: Params, job: str, input1: str, input2: str | None,
            results_dir: str, n_input: int) -> JobResult:
    program = runner.find(p.mode.program)
    if program is None:
        raise JobError(f'Program "{p.mode.program}" not found on this server.', 500)

    output = os.path.join(results_dir, f"{job}_result.fasta")
    log = ""
    clstr_full = True

    if p.mode.levels:
        identities = [p.identity, p.identity2, p.identity3][: max(1, min(p.num_runs, 3))]
        current = input1
        pass_outputs = []
        for i, ident in enumerate(identities, start=1):
            ws = p.word_size or auto_word_size(ident, p.mode.nucleotide)
            pass_out = os.path.join(results_dir, f"{job}_pass{i}.fasta")
            cmd = [program, "-i", current, "-o", pass_out, "-c", str(round(ident, 2))]
            cmd += _common_flags(p, ws)
            try:
                res = runner.run(cmd)
            except subprocess.TimeoutExpired:
                raise JobError(f"Pass {i} timed out.", 500) from None
            log += f"\n--- Pass {i} (identity={ident}) ---\n" + res.stdout + res.stderr
            if res.returncode != 0:
                raise JobError(f"Pass {i} failed:\n{(res.stderr or res.stdout)[-2000:]}", 500)
            pass_outputs.append(pass_out)
            current = pass_out

        shutil.copy(current, output)
        merged = merge_pass_clstrs(runner, [po + ".clstr" for po in pass_outputs])
        if merged is not None:
            with open(output + ".clstr", "w") as fh:
                fh.write(merged)
            log += f"\n--- Cluster list merged across passes: covers all {n_input} input sequences ---\n"
        else:
            shutil.copy(current + ".clstr", output + ".clstr")
            clstr_full = False
            log += "\n--- Could not merge the cluster lists of the passes; the .clstr covers the last pass only ---\n"
    else:
        ws = p.word_size or auto_word_size(p.identity, p.mode.nucleotide)
        cmd = [program, "-i", input1, "-o", output, "-c", str(round(p.identity, 2))]
        cmd += _common_flags(p, ws)
        if p.mode.two_d and input2:
            cmd += ["-i2", input2, "-s2", str(p.s2val), "-S2", str(p.S2val)]
        try:
            res = runner.run(cmd)
        except subprocess.TimeoutExpired:
            raise JobError("Job timed out. Try a smaller file or more threads.", 500) from None
        log = res.stdout + res.stderr
        if res.returncode != 0:
            raise JobError((res.stderr or res.stdout)[-3000:], 500)

    n_output = count_seqs(output)
    return JobResult(
        job_id=job,
        n_input=n_input,
        n_output=n_output,
        n_clusters=count_clusters(output + ".clstr"),
        reduction=round((1 - n_output / max(n_input, 1)) * 100, 1),
        clstr_full=clstr_full,
        log=log,
    )
