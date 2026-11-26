"""CD-HIT helpers."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

ALLOWED_EXTENSIONS = {"fasta", "fa", "faa", "fna", "txt"}


@dataclass(frozen=True)
class Mode:
    # one of the six tasks on the page

    name: str
    nucleotide: bool
    two_d: bool
    levels: bool

    @property
    def program(self) -> str:
        # levels jobs run plain cd-hit / cd-hit-est once per pass, so h-cd-hit is not needed
        base = "cd-hit-est" if self.nucleotide else "cd-hit"
        return base + "-2d" if self.two_d else base


# only these names are accepted from the browser
MODES: dict[str, Mode] = {
    "cd-hit": Mode("cd-hit", nucleotide=False, two_d=False, levels=False),
    "cd-hit-est": Mode("cd-hit-est", nucleotide=True, two_d=False, levels=False),
    "h-cd-hit": Mode("h-cd-hit", nucleotide=False, two_d=False, levels=True),
    "h-cd-hit-est": Mode("h-cd-hit-est", nucleotide=True, two_d=False, levels=True),
    "cd-hit-2d": Mode("cd-hit-2d", nucleotide=False, two_d=True, levels=False),
    "cd-hit-est-2d": Mode("cd-hit-est-2d", nucleotide=True, two_d=True, levels=False),
}


def allowed_filename(name: str) -> bool:
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def auto_word_size(identity: float, nucleotide: bool) -> int:
    # word size (-n) for an identity cut-off, within what CD-HIT accepts
    if nucleotide:
        if identity >= 0.90:
            return 11
        if identity >= 0.88:
            return 9
        if identity >= 0.85:
            return 7
        return 6
    if identity >= 0.70:
        return 5
    if identity >= 0.60:
        return 4
    if identity >= 0.50:
        return 3
    return 2


def count_seqs(path: str | os.PathLike) -> int:
    try:
        with open(path, errors="ignore") as fh:
            return sum(1 for line in fh if line.startswith(">"))
    except OSError:
        return 0


def count_clusters(path: str | os.PathLike) -> int:
    try:
        with open(path, errors="ignore") as fh:
            return sum(1 for line in fh if line.startswith(">Cluster"))
    except OSError:
        return 0


def count_members(clstr_text: str) -> int:
    return sum(1 for line in clstr_text.splitlines() if line.strip() and not line.startswith(">"))


def sniff_seq_type(path: str | os.PathLike, limit: int = 5000) -> str | None:
    """Return 'nuc', 'prot', or None if there is too little sequence to tell.

    Nucleotide means at least 90% of the first `limit` letters are A, C, G, T, U or N.
    """
    letters = nuc = 0
    try:
        with open(path, errors="ignore") as fh:
            for line in fh:
                if line.startswith(">"):
                    continue
                for ch in line.strip().upper():
                    if ch.isalpha():
                        letters += 1
                        if ch in "ACGTUN":
                            nuc += 1
                if letters >= limit:
                    break
    except OSError:
        return None
    if letters < 30:
        return None
    return "nuc" if nuc / letters >= 0.9 else "prot"


class Runner:
    def __init__(self, bin_dir: Path | None, timeout: int):
        self.bin_dir = bin_dir
        self.timeout = timeout

    def find(self, name: str) -> str | None:
        if self.bin_dir is not None:
            candidate = Path(self.bin_dir) / name
            if candidate.is_file():
                return str(candidate)
        return shutil.which(name)

    def run(self, cmd: list[str]) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        if self.bin_dir is not None:
            env["PATH"] = f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}"
        return subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout, env=env)


def merge_pass_clstrs(runner: Runner, paths: list[str]) -> str | None:
    """Merge the .clstr files of the passes with CD-HIT's clstr_rev.pl.

    Returns the merged text, or None if the script is missing or the result looks wrong.
    """
    script = runner.find("clstr_rev.pl")
    if script is None:
        return None
    made: list[str] = []
    try:
        with open(paths[0], errors="ignore") as fh:
            expected = count_members(fh.read())
        current = paths[0]
        for k, nxt in enumerate(paths[1:], start=1):
            res = runner.run(["perl", script, current, nxt])
            if res.returncode != 0 or not res.stdout.strip():
                return None
            current = f"{paths[0]}.merge{k}"
            with open(current, "w") as fh:
                fh.write(res.stdout)
            made.append(current)
        with open(current, errors="ignore") as fh:
            text = fh.read()
        return text if count_members(text) == expected else None
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        for p in made:
            try:
                os.remove(p)
            except OSError:
                pass
