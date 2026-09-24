"""Shared fixtures. The scripts are loaded from the skill directory by path, so
the tests exercise exactly the files a user installs."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "evidence-based-brand-systems" / "scripts"
FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def bc():
    return _load("brandcheck")


@pytest.fixture
def run(bc, capsys):
    """Run the brandcheck CLI in-process; return (exit code, stdout)."""
    def _run(*argv):
        code = bc.main([str(a) for a in argv])
        return code, capsys.readouterr().out
    return _run


@pytest.fixture(scope="session")
def ba():
    return _load("brandassets")


@pytest.fixture
def ba_run(ba, capsys):
    """Run the brandassets CLI in-process; return (exit code, stdout)."""
    def _run(*argv):
        code = ba.main([str(a) for a in argv])
        return code, capsys.readouterr().out
    return _run


@pytest.fixture
def write(tmp_path):
    def _write(rel: str, text: str) -> pathlib.Path:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p
    return _write


@pytest.fixture(scope="session")
def fixture_font(tmp_path_factory):
    from fontfactory import build_font
    return build_font(tmp_path_factory.mktemp("font") / "FixtureSans.ttf")


_BROWSER = None


def browser_available() -> bool:
    """True when Playwright and a Chromium build it can launch are installed."""
    global _BROWSER
    if _BROWSER is None:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                p.chromium.launch().close()
            _BROWSER = True
        except Exception:
            _BROWSER = False
    return _BROWSER
