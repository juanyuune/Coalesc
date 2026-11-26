#!/usr/bin/env python3
"""Generate small, fully synthetic FASTA files for tests and demos (random sequences only)."""
import random
import sys
from pathlib import Path

DNA, AA = "ACGT", "ACDEFGHIKLMNPQRSTVWY"


def mutate(seq, rate, alphabet, rng):
    return "".join(rng.choice(alphabet) if rng.random() < rate else c for c in seq)


def families(rng, alphabet, n_fam, per_fam, length, rate, prefix):
    out = []
    for f in range(n_fam):
        base = "".join(rng.choice(alphabet) for _ in range(length))
        for k in range(per_fam):
            out.append((f"{prefix}{f:03d}_{k}", base if k == 0 else mutate(base, rate, alphabet, rng)))
    return out


def write(path, recs):
    with open(path, "w") as fh:
        for name, seq in recs:
            fh.write(f">{name}\n")
            for i in range(0, len(seq), 70):
                fh.write(seq[i:i + 70] + "\n")


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(1607)
    write(out / "protein_example.fasta", families(rng, AA, 20, 4, 250, 0.03, "prot"))
    write(out / "dna_example.fasta", families(rng, DNA, 20, 4, 600, 0.02, "dna"))
    write(out / "dna_example_set2.fasta", families(rng, DNA, 6, 2, 600, 0.02, "dnb"))
    write(out / "dna_levels_example.fasta",
          families(rng, DNA, 30, 2, 600, 0.02, "lvA") + families(rng, DNA, 30, 2, 600, 0.10, "lvB"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "examples")
