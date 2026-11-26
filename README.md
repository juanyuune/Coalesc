# Coalesc

A small web interface for [CD-HIT](https://github.com/weizhongli/cdhit), the sequence
clustering suite. Upload a FASTA file, pick the identity cut-off, and download the
representative sequences and the cluster list. Built for a lab server.

> **Independent project.** Coalesc is not affiliated with or endorsed by the CD-HIT authors.
> CD-HIT is a separate program (GPL v2) that must be installed on the server; it is not
> included here.

## Features
- Cluster protein (`cd-hit`) or DNA/RNA (`cd-hit-est`) sequences
- Compare two sets (`cd-hit-2d`, `cd-hit-est-2d`)
- Levels: 2–3 successive passes with one merged cluster list covering every input sequence
- Warns when a file looks like protein but DNA is selected (and the reverse); the server checks too
- Advanced CD-HIT options (word size, length limits, alignment coverage, strand, …)
- Input validation, no shell use, fixed list of programs

## Quick start
```bash
git clone https://github.com/<you>/coalesc && cd coalesc
python3 -m venv .venv && . .venv/bin/activate
pip install .
export COALESC_BIN_DIR=/path/to/cdhit/bin     # optional if cd-hit is on PATH
python -m coalesc                             # http://127.0.0.1:8001
```
Try it with the synthetic files in `examples/`.

## Configuration
Environment variables (see `.env.example`): `COALESC_BIN_DIR`, `COALESC_UPLOAD_DIR`,
`COALESC_RESULTS_DIR`, `COALESC_MAX_UPLOAD_MB`, `COALESC_JOB_TIMEOUT_S`,
`COALESC_KEEP_UPLOADS`, `COALESC_HOST`, `COALESC_PORT`.

## Layout
```
src/coalesc/   application package (web, jobs, cdhit helpers, config, page template)
tests/         pytest suite (API tests use the real CD-HIT; ui/ has browser tests)
examples/      small synthetic FASTA files
scripts/       test-data generator
deploy/        systemd unit and tmpfiles rule
docs/          architecture, deployment, development
```
See [docs/deployment.md](docs/deployment.md) — note there is **no authentication**.

## Tests
`pytest` (needs CD-HIT on PATH). See [docs/development.md](docs/development.md).
Tested with CD-HIT 4.8.1 and Flask 3.1.3 on Ubuntu 24.04. Chrome was the only browser tried.

## Citing CD-HIT
Please cite the CD-HIT papers listed at https://github.com/weizhongli/cdhit when you use results.

## License
MIT for Coalesc's own code (see `LICENSE`).
