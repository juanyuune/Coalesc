# Deployment

Tested on Ubuntu 24.04 (WSL2) with CD-HIT 4.8.1 and Flask 3.1. Other setups are untested.

## 1. Requirements
- Python 3.10+
- CD-HIT (`cd-hit`, `cd-hit-est`, `cd-hit-2d`, `cd-hit-est-2d`) and Perl (for `clstr_rev.pl`,
  used to merge "levels" jobs). Install from your package manager, conda, or build from source.

## 2. Install
```bash
sudo useradd --system --home /opt/coalesc --shell /usr/sbin/nologin coalesc
sudo git clone https://github.com/juanyuune/Coalesc /opt/coalesc
cd /opt/coalesc && sudo python3 -m venv .venv && sudo .venv/bin/pip install .
sudo install -d -o coalesc -g coalesc -m 750 /opt/compbio/cdhit-server/{uploads,results}
sudo cp .env.example /etc/coalesc.env     # then edit
sudo cp deploy/coalesc.service /etc/systemd/system/
sudo cp deploy/coalesc.tmpfiles.conf /etc/tmpfiles.d/coalesc.conf
sudo systemctl daemon-reload && sudo systemctl enable --now coalesc
```

## 3. More than a handful of users
`python -m coalesc` uses Flask's development server. For heavier use run it under gunicorn.
Long CD-HIT jobs need a long timeout:
```bash
.venv/bin/pip install gunicorn
.venv/bin/gunicorn -w 2 -b 0.0.0.0:8001 --timeout 7200 wsgi:app
```
(Smoke-tested with gunicorn 27.0.1.)

## 4. Security notes
- There is **no login**. Run it only on a trusted network or behind a reverse proxy that
  adds authentication.
- The service should run as an unprivileged user, never root.
- Only the six known modes are accepted and numeric fields are validated before anything
  reaches the command line; CD-HIT is run without a shell.
- Uploaded files are deleted when a job ends (`COALESC_KEEP_UPLOADS=1` keeps them). Results
  are kept until the tmpfiles rule removes them.
