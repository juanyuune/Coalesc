# Architecture

```
browser (templates/index.html)
   │  POST /run (multipart form)
   ▼
web.py     validate form -> Params; save upload; check protein/DNA; call run_job
jobs.py    build command line(s); run CD-HIT; merge cluster files of "levels" jobs
cdhit.py   modes table, file sniffing, Runner, merge_pass_clstrs
config.py  COALESC_* environment settings
```

- **Modes** (`cdhit.MODES`): the only program names accepted from the browser.
- **Levels jobs** run `cd-hit`/`cd-hit-est` once per pass on the previous pass's
  representatives (the `h-cd-hit` wrapper is not required) and merge the `.clstr` files with
  CD-HIT's `clstr_rev.pl`. If merging fails the last pass's file is returned and the JSON
  field `clstr_full` is `false`.
- **Sequence type check**: if at least 90 % of the first ~5000 letters are A/C/G/T/U/N the file
  is treated as nucleotide, otherwise protein. A mismatch with the chosen type returns HTTP 400.
- **API**: `GET /`, `GET /healthz`, `POST /run`, `GET /download/<job_id>/<fasta|clstr>`.
