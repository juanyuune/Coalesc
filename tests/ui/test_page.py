"""Browser tests. Need playwright and Chrome (set CHROME_PATH if not /usr/bin/google-chrome)."""
import os
import threading
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
from werkzeug.serving import make_server

from coalesc import create_app
from conftest import EXAMPLES, needs_cdhit

pytestmark = [pytest.mark.ui, needs_cdhit]


@pytest.fixture
def live(cfg):
    srv = make_server("127.0.0.1", 0, create_app(cfg), threaded=True)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}/"
    srv.shutdown()


@pytest.fixture
def page(live):
    with pw.sync_playwright() as p:
        kw = {"args": ["--no-sandbox"]}
        chrome = os.environ.get("CHROME_PATH", "/usr/bin/google-chrome")
        if Path(chrome).exists():
            kw["executable_path"] = chrome
        browser = p.chromium.launch(**kw)
        pg = browser.new_page()
        pg.errors = []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        pg.goto(live)
        yield pg
        browser.close()


def test_protein_run_from_the_page(page):
    page.set_input_files("#fi1", str(EXAMPLES / "protein_example.fasta"))
    page.click("#tb-params")
    page.click("#runBtn")
    page.wait_for_selector(".res-head", timeout=30000)
    assert "20" in page.inner_text("#resBody")
    assert page.errors == []


def test_dna_file_with_protein_type_shows_a_warning(page):
    page.set_input_files("#fi1", str(EXAMPLES / "dna_example.fasta"))
    page.wait_for_selector("#typeWarn:not([hidden])", timeout=5000)
    assert page.errors == []


def test_levels_run_from_the_page(page):
    page.check('input[name=stype][value=nuc]')
    page.check('input[name=task][value=hier]')
    page.set_input_files("#fi1", str(EXAMPLES / "dna_levels_example.fasta"))
    page.click("#tb-params")
    page.click("#runBtn")
    page.wait_for_selector(".res-head", timeout=60000)
    assert page.errors == []
