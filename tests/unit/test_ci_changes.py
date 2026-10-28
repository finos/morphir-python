"""Change selection and the aggregate gate for CI."""

from __future__ import annotations

import pytest

from scripts import ci_changes as c

ALL = frozenset(c.CATEGORIES)


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["README.md", "docs/templates/x.html", "openspec/changes/a/tasks.md"], set()),
        (["docs/python-compiler.md"], {"docs", "docs-examples"}),
        (
            ["packages/morphir-python-native/README.md"],
            {"python", "native", "docs", "docs-examples"},
        ),
        (
            ["rust/crates/morphir-python-native/src/lib.rs"],
            {"python", "native", "rust"},
        ),
        (["rust/crates/morphir-python-binding/src/lib.rs"], ALL),
        (["rust/Cargo.lock"], ALL),
        (
            ["packages/morphir/src/morphir/ir/json.py"],
            {"python", "native", "docs", "docs-examples"},
        ),
        (["uv.lock"], {"python", "native", "docs", "docs-examples"}),
        (
            ["examples/install/mise-pipx.toml"],
            {"python", "native", "docs", "docs-examples"},
        ),
        (["rust/extension.toml"], {"bundle", "docs", "docs-examples", "docs-hosts"}),
        (
            ["tests/fixtures/python/loans/acme/rules.py"],
            {"python", "native", "bundle", "docs", "docs-hosts"},
        ),
        (["scripts/extension_bundle.py"], {"python", "bundle", "docs", "docs-hosts"}),
        ([".gitignore"], {"python", "native", "docs", "docs-examples"}),
        ([".github/workflows/ci.yml"], ALL),
        ([".config/mise/tasks/test"], ALL),
        (["something/new.txt"], ALL),
    ],
)
def test_selection(paths: list[str], expected: set[str]) -> None:
    assert c.select(paths).categories == expected


def test_documentation_only_changes_run_no_jobs() -> None:
    jobs = c.select(["README.md"]).jobs()
    assert not any(jobs.values())


def test_native_only_changes_skip_rust_and_bundle() -> None:
    jobs = c.select(["packages/morphir-python-native/pyproject.toml"]).jobs()
    assert jobs["native-wheel"] and jobs["test"] and jobs["build"]
    assert not jobs["rust"] and not jobs["bundle"]


def test_bundle_only_changes_build_the_wheel_the_bundle_check_uses() -> None:
    jobs = c.select(["rust/extension.toml"]).jobs()
    assert jobs["bundle"] and jobs["native-wheel"]
    assert not jobs["test"] and not jobs["rust"]


def test_full_runs_select_everything() -> None:
    assert c.select([], full=True).categories == ALL
    assert all(c.select([], full=True).jobs().values())


def test_site_prose_runs_site_checks_without_compiler_builds() -> None:
    selection = c.select(["docs/site-foundation.md"])
    assert selection.jobs()["docs"]
    assert not selection.jobs()["native-wheel"]
    assert not selection.jobs()["rust"]
    assert "docs-examples" not in selection.categories


def test_examples_select_installed_checks_without_rebuilding_the_native_wheel() -> None:
    selection = c.select(["examples/compiler_api.py"])
    assert "docs-examples" in selection.categories
    assert selection.jobs()["docs"]
    assert not selection.jobs()["native-wheel"]


def test_host_recipe_changes_require_fresh_host_evidence() -> None:
    selection = c.select(["examples/extension.sh"])
    assert "docs-hosts" in selection.categories
    assert selection.jobs()["docs"]


def needs(**results: str) -> dict[str, dict[str, str]]:
    return {"changes": {"result": "success"}} | {
        job.replace("_", "-"): {"result": result} for job, result in results.items()
    }


def test_aggregate_passes_selected_success_and_unselected_skip() -> None:
    selected = c.select(["rust/extension.toml"]).jobs()
    results = needs(**{job.replace("-", "_"): "skipped" for job in selected})
    for job, required in selected.items():
        if required:
            results[job] = {"result": "success"}
    assert c.aggregate(selected, results) == []


@pytest.mark.parametrize("outcome", ["failure", "cancelled", "skipped"])
def test_aggregate_fails_selected_jobs_that_did_not_succeed(outcome: str) -> None:
    selected = c.select([], full=True).jobs()
    results = needs(**{job.replace("-", "_"): "success" for job in selected})
    results["test"] = {"result": outcome}
    assert c.aggregate(selected, results) == [f"test: selected but {outcome}"]


def test_aggregate_fails_missing_results() -> None:
    selected = c.select([], full=True).jobs()
    results = needs(**{job.replace("-", "_"): "success" for job in selected})
    del results["bundle"]
    assert c.aggregate(selected, results) == ["bundle: no result"]


def test_aggregate_fails_unselected_jobs_that_ran_or_failed() -> None:
    selected = c.select(["README.md"]).jobs()
    results = needs(**{job.replace("-", "_"): "skipped" for job in selected})
    results["rust"] = {"result": "failure"}
    assert c.aggregate(selected, results) == ["rust: not selected but failure"]


def test_aggregate_fails_when_selection_failed() -> None:
    results = needs()
    results["changes"] = {"result": "failure"}
    assert c.aggregate({}, results) == ["changes: failure"]


def test_select_command_prints_outputs(capsys: pytest.CaptureFixture[str]) -> None:
    c.main(["select", "rust/extension.toml"])
    lines = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert lines["bundle"] == "true"
    assert lines["python"] == "false"


def test_aggregate_command_exits_non_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        c.main(
            [
                "aggregate",
                "--selected",
                '{"lint": true}',
                "--needs",
                '{"changes": {"result": "success"}, "lint": {"result": "cancelled"}}',
            ]
        )
    assert "lint: selected but cancelled" in capsys.readouterr().out
