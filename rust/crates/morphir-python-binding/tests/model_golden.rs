//! Golden outputs of the MEP `0.2.0-draft.1` model operations.
//!
//! Each model operation runs through a real SDK session negotiated with a host
//! that offers every tuple this extension serves. The envelope, the decoded IR
//! payload and the generated files must equal the files in `tests/golden/`.
//! Set `MORPHIR_UPDATE_GOLDEN=1` to write the files again after an intended
//! change, then review the difference.
use morphir_extension_sdk::{NativeExtension, NativeProtocol};
use morphir_python_binding::PythonExtension;
use serde_json::{Value, json};
use std::path::PathBuf;

const ENVELOPE: &str = "0.1.0-draft.1";

fn send(protocol: &dyn NativeProtocol, request: Value) -> Value {
    serde_json::to_value(protocol.handle(serde_json::from_value(request).unwrap())).unwrap()
}

fn tuple(operation: &str, ir_version: &str) -> Value {
    json!({"operation":operation,"profile":"morphir-ir","codec":"morphir-json",
        "envelopeVersion":ENVELOPE,"irVersion":ir_version})
}

fn every_tuple() -> Vec<Value> {
    [
        "morphir.frontend.compileModel",
        "morphir.backend.generateModel",
    ]
    .into_iter()
    .flat_map(|operation| ["3.0.0", "4.0.0"].map(|version| tuple(operation, version)))
    .collect()
}

fn session() -> std::sync::Arc<dyn NativeProtocol> {
    let extension = NativeExtension::frontend_backend(PythonExtension).unwrap();
    let session = extension.open_protocol();
    let selected = send(
        session.as_ref(),
        json!({"jsonrpc":"2.0","id":1,"method":"morphir.initialize","params":{
            "protocolVersions":["0.2.0-draft.1","0.1"],
            "host":{"name":"golden-test","version":"1"},
            "modelTransport":{"tuples":every_tuple(),
                "limits":{"maxEncodedBytes":1048576,"maxDecodedBytes":786432,"maxDepth":128,"maxNodes":100000},
                "guarantees":[]},
        }}),
    );
    assert_eq!(
        selected["result"]["protocolVersion"], "0.2.0-draft.1",
        "{selected}"
    );
    assert_eq!(
        selected["result"]["capabilities"]["modelTransport"]["tuples"],
        json!(every_tuple())
    );
    session
}

fn fixture(name: &str) -> String {
    std::fs::read_to_string(
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(format!("tests/fixtures/{name}")),
    )
    .unwrap()
}

fn compile_model(session: &dyn NativeProtocol, ir_version: &str) -> Value {
    let documents: Vec<Value> = ["models.py", "functions.py"]
        .iter()
        .map(|name| json!({"uri":format!("acme/{name}"),"languageId":"python","version":1,"text":fixture(name)}))
        .collect();
    send(
        session,
        json!({"jsonrpc":"2.0","id":2,"method":"morphir.frontend.compileModel","params":{
            "languageId":"python","sources":{"documents":documents},
            "package":{"name":"acme"},"dependencies":[],
            "options":{"irVersion":ir_version,"typesOnly":false},"contextDigest":"a".repeat(64),
            "output":tuple("morphir.frontend.compileModel", ir_version),
        }}),
    )
}

fn generate_model(session: &dyn NativeProtocol, model: &Value) -> Value {
    send(
        session,
        json!({"jsonrpc":"2.0","id":3,"method":"morphir.backend.generateModel","params":{
            "model":model,"target":"python","contextDigest":"a".repeat(64),
            "requiredGuarantees":[],"options":{},
            "input":tuple("morphir.backend.generateModel", model["irVersion"].as_str().unwrap()),
        }}),
    )
}

/// Compares `actual` with the golden file, or writes it when asked to.
fn golden(name: &str, actual: &Value) {
    golden_text(
        name,
        &format!("{}\n", serde_json::to_string_pretty(actual).unwrap()),
    );
}

fn golden_text(name: &str, text: &str) {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/golden")
        .join(name);
    if std::env::var_os("MORPHIR_UPDATE_GOLDEN").is_some() {
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(&path, text).unwrap();
        return;
    }
    let expected = std::fs::read_to_string(&path).unwrap_or_else(|_| {
        panic!(
            "missing {}; run with MORPHIR_UPDATE_GOLDEN=1",
            path.display()
        )
    });
    assert!(text == expected, "{name} differs from its golden file");
}

/// The exact decoded payload, after the SDK checks its length and digest.
fn payload(model: &Value) -> String {
    use morphir_extension_sdk::model::{ModelTransportLimits, MorphirModel, retain_model};
    let envelope: MorphirModel = serde_json::from_value(model.clone()).unwrap();
    let input =
        serde_json::from_value(tuple("morphir.backend.generateModel", &envelope.ir_version))
            .unwrap();
    let limits = ModelTransportLimits {
        max_encoded_bytes: 1024 * 1024,
        max_decoded_bytes: 1024 * 1024,
        max_depth: 128,
        max_nodes: 100_000,
    };
    let retained = retain_model(&envelope, &input, &limits).unwrap();
    String::from_utf8(retained.bytes().to_vec()).unwrap()
}

#[test]
fn compile_model_and_generate_model_match_their_golden_outputs() {
    for (ir, version) in [("ir3", "3.0.0"), ("ir4", "4.0.0")] {
        let session = session();
        let compiled = compile_model(session.as_ref(), version);
        assert!(compiled.get("error").is_none(), "{}", compiled["error"]);
        let result = &compiled["result"];
        assert_eq!(result["success"], true, "{}", result["diagnostics"]);
        let model = &result["model"];
        assert_eq!(model["envelopeVersion"], ENVELOPE);
        assert_eq!(model["irVersion"], version);

        let mut envelope = model.clone();
        envelope["payload"]["content"] = json!("<base64 of the payload golden file>");
        golden(
            &format!("compile-model-{ir}.json"),
            &json!({"model":envelope,"diagnostics":result["diagnostics"],"modules":result["modules"]}),
        );
        // The payload golden file holds the exact bytes the envelope digests.
        golden_text(&format!("compile-model-{ir}.payload.json"), &payload(model));

        let generated = generate_model(session.as_ref(), model);
        assert!(generated.get("error").is_none(), "{}", generated["error"]);
        assert_eq!(
            generated["result"]["success"], true,
            "{}",
            generated["result"]["diagnostics"]
        );
        golden(&format!("generate-model-{ir}.json"), &generated["result"]);
    }
}
