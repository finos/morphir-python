# Site foundation and upstream work

This site consumes [Telescope 0.2.1](https://github.com/moonrockz/telescope/releases/tag/v0.2.1).
It reuses static rendering, navigation, search, themes, page contents and code
copying. Python example execution stays in this repository. Telescope is a
build-time dependency and adds no Python runtime dependencies.

## Python API reference

Telescope's current API adapter reads `moon doc` metadata. It does not read
Python type annotations. We maintain concise [Python reference pages](api-reference.md)
and verify their symbols/signatures against installed packages. This is a
non-blocking consumer choice. A Python metadata adapter would be a reusable
extension if a larger generated reference becomes necessary.

## Tested source snippets

Telescope 0.2.1 does not include checked source regions. The consumer sync/check
utility maps fenced snippets to canonical examples, while domain tests check
their behavior. Telescope's `standardize-tutorial-components` intent is already
exploring reusable tutorial components. We do not depend on that unmerged work.
Record its durable proposal link when published and avoid duplicate reports.

## Report a limitation

Before adding a second renderer or patching a private copy, reproduce a missing
generic feature with the pinned CLI in a minimal consumer. Search
[Telescope issues](https://github.com/moonrockz/telescope/issues) and existing
proposals. Report the version, fixture, commands, expected/actual behavior,
consumer impact and acceptance criteria, and link the report here with any
temporary workaround. A workaround does not turn an unmet acceptance criterion
into a passing check. Adopt upstream fixes through a pinned published release.

## Repository source links

Telescope 0.2.1 treats existing files outside discovered roots as missing.
[Telescope issue 10](https://github.com/moonrockz/telescope/issues/10) records the
minimal reproduction and requested source-link contract. Explicit GitHub URLs
are the current non-blocking workaround; internal published-page links remain
relative and checked.
