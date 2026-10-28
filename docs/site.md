# Contribute to the documentation

The site uses the published Telescope 0.2.1 native CLI. Its archive URLs and
SHA-256 digests are pinned in [site/toolchain.json](https://github.com/finos/morphir-python/blob/main/site/toolchain.json).
Local preview is qualified on macOS arm64, and CI uses Linux x64. Other site
builder platforms are unqualified. Python 3.14 is sufficient to install and run
the stock builder. No MoonBit compiler or neighboring Telescope checkout is used.

## Build and preview

From the repository root, run:

```bash
python3 scripts/site_tool.py setup
python3 scripts/site_tool.py build
python3 scripts/site_tool.py check
python3 scripts/site_tool.py serve
```

Open `http://127.0.0.1:4173/morphir-python/`. Stop preview with Ctrl-C.
The server serves an existing build; rebuild after editing a page. The equivalent
mise commands are `site:setup`, `site:build`, `site:check` and `site:serve`.
The direct Python commands avoid installing the repository's Rust toolchain for
a prose-only edit.

Use `--base / --out .dev/site-root` on build/check/serve to test root hosting.
The default output is `_site/`, with the Pages base `/morphir-python/`. A build
checks links and resources before replacing prior output. Templates, OpenSpec,
local planning artifacts and generated output stay outside the published tree.

## Write a guide

Keep Markdown under `docs/`, add it to the sidebar in `site/site.json`, and use
relative links to sources and other guides. The home page lives in
`site/pages/index.md`. Keep headings descriptive so search and the page contents
list are useful. Use language-tagged fenced code without shell prompt characters.
Existing guide paths remain useful on GitHub.

Runnable examples have canonical files under `examples/`. Their prerequisite
manifest distinguishes released and development packages. Synchronize marked
snippets with `python3 scripts/docs_examples.py sync`; `check` refuses drift.
Run `mise run docs:test` for installed-example, type-check and snippet checks.
Compilation itself never imports submitted source. Verification of generated
behavior runs in its own process.

Run the browser suite with `npm ci --prefix site/browser`,
`npm exec --prefix site/browser -- playwright install chromium`, and
`npm test --prefix site/browser`. It checks desktop/phone layouts, themes,
search, navigation, copying and keyboard focus at both deployment bases.
Screenshots and reports are under `.dev/site-browser/`.

## Qualify host instructions

`python3 scripts/docs_hosts.py prepare` verifies/downloads the declared host and
bundle and prints their absolute paths. `qualify` runs the exact displayed
Rust-host recipe, the existing offline v3/v4 bundle qualification, and two
MoonBit plain-IR refusal probes. It needs the installed Python compiler, mise,
Node and access to the pinned source/tool releases. It builds the MoonBit CLI
in this repository's disposable `.dev/` tool cache, without changing its repo.

To change a supported host claim, update `site/integrations.json`, the recipe
and guides together, run `python3 scripts/docs_hosts.py qualify`, then inspect
`.dev/docs-hosts/report.json`. Store a reviewed reusable report at
`site/evidence/hosts.json`. Run `python3 scripts/docs_hosts.py verify --report
site/evidence/hosts.json` to check it still matches every relevant input hash.
Changing any recipe, fixture, pin or checker invalidates reuse. Network or
tool acquisition failures remain failed qualification, with no successful
receipt written. CI produces fresh evidence on relevant changes and full runs.

## Publish and recover

Pull requests validate without production credentials. After successful main CI, the publication workflow validates the producer and
promotes the exact checked output with its source, tool and example
evidence manifest, after required checks succeed. A failed, missing or
unexpectedly skipped required result blocks promotion. The deploy job alone
uses Pages/OIDC write permissions and the `github-pages` environment.

A maintainer must enable GitHub Pages with **GitHub Actions** as the build
source and approve deployment when the repository environment requires it.
Do not change settings or merge merely to test a preview. A manual main CI run repeats qualification before publication. The separate
Publish documentation workflow accepts a successful main CI run ID for restoring
its retained artifact. It refuses pull-request, fork, failed and unrelated
workflow producers, and checks out the producer SHA before verification. Retain the verified Pages artifact,
its digest and the producing run for 30 days. To recover, rerun deployment of
that artifact from its original authorized run without rebuilding, or revert
the content and validate a new main revision. The deployment receipt identifies
the source and artifact selected. A site rollback does not roll back packages.

For tool updates, change the exact version, URL and digest together, then repeat
clean installs, base-path checks and browser tests. See
[foundation decisions](site-foundation.md) for upstream reports and limitations.
