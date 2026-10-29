"""The site tool installs only verified release archives."""

import os
import subprocess
from typing import TYPE_CHECKING

import pytest

from scripts.site_tool import SiteError, install_archive, setup

if TYPE_CHECKING:
    from pathlib import Path


def test_bad_download_preserves_the_previous_installation(tmp_path: Path) -> None:
    archive = tmp_path / "download.tar.gz"
    archive.write_bytes(b"corrupt download")
    installed = tmp_path / "installed"
    installed.mkdir()
    (installed / "telescope").write_bytes(b"previous installation")
    with pytest.raises(SiteError, match="SHA-256"):
        install_archive(archive, installed, "0" * 64, "0.2.1")
    assert (installed / "telescope").read_bytes() == b"previous installation"


@pytest.mark.skipif(
    not os.environ.get("MORPHIR_SITE_TEST"), reason="explicit site qualification"
)
@pytest.mark.parametrize("base", ["/", "/morphir-python/"])
def test_broken_fragment_preserves_checked_output(tmp_path: Path, base: str) -> None:
    import json

    binary = setup()
    (tmp_path / "docs/templates").mkdir(parents=True)
    (tmp_path / "docs/templates/private.md").write_text("# Privatetemplatetoken\n")
    page = tmp_path / "docs/guide.md"
    page.write_text("# Guide\n\n## Topic\n\n[Go](#topic)\n")
    (tmp_path / "site").mkdir()
    (tmp_path / "site/site.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Fixture",
                "description": "Fixture",
                "base_path": base,
                "site_url": "https://example.test" + base,
                "repo_url": "https://github.com/example/repo",
                "repo_ref": "main",
                "packages": [],
                "source_roots": ["docs"],
            }
        )
    )
    command = [str(binary), "build", "--config", "site/site.json", "--out", "output"]
    subprocess.run(command, cwd=tmp_path, check=True, capture_output=True)
    original = (tmp_path / "output/docs/guide/index.html").read_bytes()
    assert (
        "Privatetemplatetoken"
        not in (tmp_path / "output/search-index.json").read_text()
    )
    page.write_text("# Guide\n\n[Missing](#absent)\n")
    failed = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert failed.returncode == 1
    assert "absent" in failed.stderr + failed.stdout
    assert (tmp_path / "output/docs/guide/index.html").read_bytes() == original


@pytest.mark.skipif(
    not os.environ.get("MORPHIR_SITE_TEST"), reason="explicit site qualification"
)
def test_branding_is_checked_before_replacing_the_site(tmp_path: Path) -> None:
    import json

    from scripts.site_tool import build_site

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/guide.md").write_text("# Guide\n")
    (tmp_path / "site/theme").mkdir(parents=True)
    (tmp_path / "site/site.json").write_text(
        json.dumps(
            {
                "title": "Fixture",
                "description": "Fixture",
                "base_path": "/",
                "site_url": "https://example.test/",
                "repo_url": "https://github.com/example/repo",
                "packages": [],
                "source_roots": ["docs"],
            }
        )
    )
    theme = tmp_path / "site/theme/morphir.css"
    theme.write_text(":root { --brand-blue: #00a3e2; }\n")
    build_site(setup(), "/", "output", root=tmp_path)
    css = tmp_path / "output/assets/site.css"
    checked = css.read_bytes()
    assert b"--brand-blue: #00a3e2" in checked
    theme.write_text("body { background: url(missing-brand-image.svg); }\n")
    with pytest.raises(subprocess.CalledProcessError):
        build_site(setup(), "/", "output", root=tmp_path)
    assert css.read_bytes() == checked
