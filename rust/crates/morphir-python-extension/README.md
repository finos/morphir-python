# Morphir Python process guest

This crate runs the shared Python compiler as a native MEP process. It has no
CPython or PyO3 dependency, and the executable needs no user Rust toolchain.
Source is parsed statically and is never imported or executed.

Development build and entry point:

```bash
cargo build --manifest-path rust/Cargo.toml --release -p morphir-python-extension
./rust/target/release/morphir-python-extension --stdio
```

In stdio mode stdout contains only Content-Length-framed UTF-8 JSON-RPC.
Headers are bounded to 8 KiB and complete bodies to 16 MiB. Lengths count bytes;
unknown headers are ignored and duplicate lengths are refused. A damaged frame
ends the connection. Invalid JSON in an otherwise valid frame gets a parse-error
response and the next framed request can recover. Notifications get no response;
`morphir.exit` ends the process. Each process owns its SDK protocol session.

The host owns deadlines and process cleanup. A native process has ordinary OS
rights; choosing it does not provide a WASM sandbox.

The current development build advertises legacy MEP 0.1. Exact-draft discovery
and model transport wait for the qualified published SDK prerequisite and
conformance checks. Platform archives and installation recipes are still under
development. The retained WASM release remains the qualified installation route.
