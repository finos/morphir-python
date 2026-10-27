//! The JSON bridge contract, exercised without an interpreter.

use std::thread;

use _native::{BridgeOutput, CompileInput, run_json};
use serde_json::{Value, json};

const RULES: &str = "def choose(flag: bool, first: int, second: int) -> int:\n    return first if flag else second\n";

fn compile(request: Value) -> Value {
    serde_json::from_str(&run_json::<CompileInput, _>(
        &request.to_string(),
        _native::compile_input,
    ))
    .unwrap()
}

fn generate(ir: &str) -> Value {
    serde_json::from_str(&run_json::<Value, _>(ir, _native::generate_input)).unwrap()
}

fn request(version: &str) -> Value {
    json!({
        "package": "acme/example",
        "sources": [{"path": "rules.py", "text": RULES}],
        "exposedModules": null,
        "irVersion": version,
    })
}

#[test]
fn compiles_and_generates_in_both_versions() {
    for version in ["3", "4"] {
        let compiled = compile(request(version));
        assert_eq!(compiled["success"], true, "{compiled}");
        let ir = compiled["ir"].as_str().unwrap();
        let document: Value = serde_json::from_str(ir).unwrap();
        assert_eq!(document["formatVersion"], version.parse::<u64>().unwrap());
        assert!(compiled.get("internalError").is_none());
        let generated = generate(ir);
        assert_eq!(generated["success"], true, "{generated}");
        let artifacts = generated["artifacts"].as_array().unwrap();
        assert_eq!(artifacts.len(), 1);
        assert_eq!(artifacts[0]["path"], "rules.py");
        assert!(
            artifacts[0]["content"]
                .as_str()
                .unwrap()
                .contains("def choose(")
        );
    }
}

#[test]
fn language_errors_are_diagnostics_with_locations_and_no_model() {
    let mut bad = request("3");
    bad["sources"][0]["text"] = json!("def broken(:\n");
    let compiled = compile(bad);
    assert_eq!(compiled["success"], false);
    assert!(compiled.get("ir").is_none());
    let diagnostic = &compiled["diagnostics"][0];
    assert_eq!(diagnostic["severity"], "error");
    assert_eq!(diagnostic["code"], "PY002");
    assert_eq!(diagnostic["location"]["path"], "rules.py");
    assert_eq!(diagnostic["location"]["start"]["line"], 0);
}

#[test]
fn unsupported_statements_are_rejected_without_execution() {
    let mut bad = request("3");
    bad["sources"][0]["text"] = json!("open('owned.txt', 'w').write('x')\n");
    let compiled = compile(bad);
    assert_eq!(compiled["success"], false);
    assert_eq!(compiled["diagnostics"][0]["code"], "PY004");
    assert!(!std::path::Path::new("owned.txt").exists());
}

#[test]
fn malformed_requests_are_internal_errors() {
    let output = run_json::<CompileInput, _>("{\"package\": 1}", |_| unreachable!());
    let output: Value = serde_json::from_str(&output).unwrap();
    assert_eq!(output["success"], false);
    assert!(
        output["internalError"]
            .as_str()
            .unwrap()
            .starts_with("invalid bridge request")
    );
    let mut extra = request("3");
    extra["unexpected"] = json!(true);
    assert!(compile(extra)["internalError"].is_string());
}

#[test]
fn panics_become_internal_errors() {
    let output = run_json::<Value, _>("{}", |_| -> BridgeOutput { panic!("boom") });
    let output: Value = serde_json::from_str(&output).unwrap();
    assert_eq!(
        output["internalError"],
        "the native compiler panicked: boom"
    );
}

#[test]
fn integer_lexemes_survive_generation_input() {
    let compiled = compile(request("4"));
    let ir = compiled["ir"].as_str().unwrap();
    assert!(generate(ir)["success"].as_bool().unwrap());
    let invalid = generate("{\"formatVersion\": 4");
    assert!(
        invalid["internalError"]
            .as_str()
            .unwrap()
            .starts_with("invalid bridge request")
    );
}

#[test]
fn concurrent_requests_do_not_share_state() {
    let expected: Vec<Value> = (0..8)
        .map(|index| compile(request(if index % 2 == 0 { "3" } else { "4" })))
        .collect();
    let handles: Vec<_> = (0..8)
        .map(|index| {
            thread::spawn(move || {
                (0..20)
                    .map(|_| compile(request(if index % 2 == 0 { "3" } else { "4" })))
                    .collect::<Vec<_>>()
            })
        })
        .collect();
    for (index, handle) in handles.into_iter().enumerate() {
        for output in handle.join().unwrap() {
            assert_eq!(output, expected[index]);
        }
    }
}
