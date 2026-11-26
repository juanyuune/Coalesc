"""Small helpers around the CD-HIT programs: modes, file sniffing, running, merging."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

ALLOWED_EXTENSIONS = {"fasta", "fa", "faa", "fna", "txt"}


@dataclass(frozen=True)
class Mode:
    """One of the six tasks offered by the web page."""

    name: str
    nucleotide: bool
    two_d: bool
    levels: bool

    @property
    def program(self) -> str:
        """The CD-HIT executable that is actually run.

        A "levels" job runs plain cd-hit / cd-hit-est once per pass, so the h-cd-hit
        wrapper scripts are never needed.
        """
        base = "cd-hit-est" if self.nucleotide else "cd-hit"
        return base + "-2d" if self.two_d else base


#: Only these names are accepted from the browser. Never build a program path from user input.
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
    """Word size (-n) to use for an identity cut-off. Always inside CD-HIT's accepted range."""
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
    """Number of sequence lines in the text of a .clstr file."""
    return sum(1 for line in clstr_text.splitlines() if line.strip() and not line.startswith(">"))


def sniff_seq_type(path: str | os.PathLike, limit: int = 5000) -> str | None:
    """Guess whether a FASTA file holds nucleotide ('nuc') or protein ('prot') sequences.

    Looks at the first ``limit`` letters. A file counts as nucleotide when at least 90 % of
    them are A, C, G, T, U or N. Returns None when there is too little sequence to tell.
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
    """Finds and runs CD-HIT programs."""

    def __init__(self, bin_dir: Path | None, timeout: int):
        self.bin_dir = bin_dir
        self.timeout = timeout

    def find(self, name: str) -> str | None:
        """Absolute path of a CD-HIT tool, looked up in bin_dir first, then on PATH."""
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
    """Combine the .clstr files of successive passes into one covering every original sequence.

    Uses CD-HIT's own ``clstr_rev.pl`` (pass 1 + pass 2 -> merged, merged + pass 3 -> ...).
    Returns the merged text, or None when the script is missing or the result looks wrong
    (the caller then falls back to the last pass's file).
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
