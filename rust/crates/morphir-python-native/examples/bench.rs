//! Time the compiler in Rust, directly and through the JSON bridge.
//!
//! Usage: `bench REQUEST.json WARMUP REPETITIONS`. REQUEST is a bridge compile
//! request. Prints JSON with one list of nanosecond samples per stage:
//!
//! - `rust_compile`, `rust_generate`: the `Frontend`/`Backend` trait calls on
//!   owned SDK values, as a native Rust caller makes them;
//! - `bridge_compile`, `bridge_generate`: the bridge functions the CPython module
//!   runs after detaching, including request parsing and result serialization.

use std::time::Instant;

use _native::{CompileInput, compile_input, compile_request, generate_input, run_json};
use morphir_extension_sdk::prelude::*;
use morphir_python_binding::PythonExtension;
use serde_json::{Value, json};

fn time<F: FnMut()>(warmup: usize, repetitions: usize, mut operation: F) -> Vec<u128> {
    for _ in 0..warmup {
        operation();
    }
    (0..repetitions)
        .map(|_| {
            let start = Instant::now();
            operation();
            start.elapsed().as_nanos()
        })
        .collect()
}

fn main() {
    let mut args = std::env::args().skip(1);
    let path = args.next().expect("request path");
    let warmup: usize = args.next().expect("warmup").parse().unwrap();
    let repetitions: usize = args.next().expect("repetitions").parse().unwrap();
    let text = std::fs::read_to_string(path).unwrap();
    let parse = || serde_json::from_str::<CompileInput>(&text).unwrap();

    let request = compile_request(parse());
    let compiled = PythonExtension.compile(request.clone()).unwrap();
    assert!(compiled.success, "{:?}", compiled.diagnostics);
    let ir = compiled.ir.unwrap();
    let ir_text = ir.to_string();
    let generate = GenerateRequest {
        ir,
        target: "python".into(),
        options: Default::default(),
    };

    // Owned input, as a Rust caller passes it: the timed call includes the clone.
    let rust_compile = time(warmup, repetitions, || {
        std::hint::black_box(PythonExtension.compile(request.clone()).unwrap());
    });
    let rust_generate = time(warmup, repetitions, || {
        std::hint::black_box(PythonExtension.generate(generate.clone()).unwrap());
    });
    let bridge_compile = time(warmup, repetitions, || {
        std::hint::black_box(run_json(&text, compile_input));
    });
    let bridge_generate = time(warmup, repetitions, || {
        std::hint::black_box(run_json::<Value, _>(&ir_text, generate_input));
    });
    println!(
        "{}",
        json!({
            "rust_compile": rust_compile,
            "rust_generate": rust_generate,
            "bridge_compile": bridge_compile,
            "bridge_generate": bridge_generate,
            "ir_bytes": ir_text.len(),
        })
    );
}
