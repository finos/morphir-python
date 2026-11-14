# Python extension 0.6.0 release record

Extension [0.6.0](https://github.com/finos/morphir-python/releases/tag/extension/python/v0.6.0)
was published on 2026-11-01 from commit
`560a6503b8ffcab87ea667391579b747757bec0d`. It contains a WASM module and
five native process executables. It does not contain the installable process
packages or Windows ARM64 executable added for the 0.6.2 candidate.

This page records the released model-line implementation. The
[0.5.0 host recipe](python-extension.md) and its committed receipt retain their
original inputs and hashes. The separate
[.NET process installation guide](dotnet-process-extension.md) describes the
0.6.2 candidate, which has not been published as part of this close-out.

## Published bytes

The [release pins](https://github.com/finos/morphir-python/blob/main/site/releases/python-0.6.0.json)
record the exact asset names and SHA-256 values. Download the WASM, its
`.wasm.sha256` file and its `.release.json` descriptor from the release. Check
their bytes against the release's `SHA256SUMS` before using them.

| Asset | SHA-256 |
| --- | --- |
| `morphir-python-binding-0.6.0.wasm` | `ce0cba07f0395ff8179b42eb021ade05c68197f69b8e9c0c8bc369d2a035727c` |
| `morphir-python-binding-0.6.0.wasm.sha256` | `e5fd91b19d1b3ad0f09ec0e54a69add31fd557835964dfb571f2cfcd5dabf096` |
| `morphir-python-binding-0.6.0.release.json` | `83db8a9203844585d00601457a8e1e348bd2b517f0c4dc4524faaadd8c43479f` |

The descriptor identifies the released source commit and the WASM digest.
Release 0.6.0 advertises both `0.2.0-draft.1` and historical `0.1`. Its model
operations use complete `morphir-ir` / `morphir-json` / envelope
`0.1.0-draft.1` tuples for IR `3.0.0` and `4.0.0`. It does not offer Ion.
The newer 0.6.2 process and WASM guest code offers only `0.2.0-draft.1` and
refuses retired `0.1`; that later decision does not change released 0.6.0 bytes.

The published Python CLI and native package 0.1.2 still pair with compiler
0.5.0. A standalone extension release does not upgrade those installed packages.

## Delivery evidence

- [PR #80](https://github.com/finos/morphir-python/pull/80) merged the negotiation
  tests and exact model-envelope, payload and generated-code goldens.
- [Manual release run 41267831018](https://github.com/finos/morphir-python/actions/runs/41267831018)
  passed the five-platform candidate checks and skipped every publication job.
- [Release run 41300584158](https://github.com/finos/morphir-python/actions/runs/41300584158)
  published the reviewed 0.6.0 assets. The published `bundle-host.json` records
  offline v3/v4 round trips and installed-integrity refusal on Rust host
  `0.4.0-beta.10`, using its historical MEP 0.1 route.
- The [dry-run MoonBit receipt](https://github.com/finos/morphir-python/pull/80#issuecomment-6553253719)
  records 32 passing model-line rows for candidate WASM and process bytes on
  macOS ARM64, from native and npm CLIs at host revision `40623b8`.
  Its WASM SHA-256 is exactly the published WASM SHA-256 above. This carries
  the module evidence forward by byte identity; it is not a fresh post-release
  host run or a claim about every published process executable.

At that MoonBit revision, the model-line CLI supports IR 4 and refuses IR 3.
The guest's IR 3 model behavior is covered by its Rust session and golden tests.
The npm WASM worker uses the host's documented `thread-termination` stop method;
the native WASM worker and process guest report `exited-after-exit`.

## Evidence limits

No GitHub provenance attestation was emitted for this release. Checksums and
conformance reports do not establish signed build provenance.
[Issue #89](https://github.com/finos/morphir-python/issues/89) tracks producing
and verifying attestations for a future release. Historical assets stay intact.

These receipts do not qualify the .NET host or its packaging. Its experimental
process-package route has separate installation checks and documentation.
