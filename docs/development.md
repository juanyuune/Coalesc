# Development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
python scripts/make_test_data.py        # regenerate examples/ (synthetic data only)
pytest                                  # API tests need cd-hit on PATH, otherwise they skip
pytest -m ui                            # browser tests; needs `playwright install chromium`
                                        # or CHROME_PATH=/path/to/chrome
COALESC_BIN_DIR=/path/to/cdhit python -m coalesc
```
