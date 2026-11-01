//! Real SDK sessions must admit only the negotiated model tuples and limits.
use morphir_extension_sdk::{NativeExtension, NativeProtocol};
use morphir_python_binding::PythonExtension;
use serde_json::{Value, json};

fn send(protocol: &dyn NativeProtocol, request: Value) -> Value {
    serde_json::to_value(protocol.handle(serde_json::from_value(request).unwrap())).unwrap()
}

fn host_offer() -> Value {
    json!({
        "tuples":[{"operation":"morphir.frontend.compileModel","profile":"morphir-ir",
            "codec":"morphir-json","envelopeVersion":"0.1.0-draft.1","irVersion":"3.0.0"}],
        "limits":{"maxEncodedBytes":65536,"maxDecodedBytes":49152,"maxDepth":64,"maxNodes":10000},
        "guarantees":[],
    })
}

fn initialize(versions: Value, offer: Option<Value>) -> Value {
    let mut params =
        json!({"protocolVersions":versions,"host":{"name":"qualified-test","version":"1"}});
    if let Some(offer) = offer {
        params["modelTransport"] = offer;
    }
    json!({"jsonrpc":"2.0","id":1,"method":"morphir.initialize","params":params})
}

fn compile_model(version: &str) -> Value {
    json!({"jsonrpc":"2.0","id":2,"method":"morphir.frontend.compileModel","params":{
        "languageId":"python","sources":{"documents":[{"uri":"main.py","languageId":"python","version":1,"text":"def identity(flag: bool) -> bool:\n    return flag\n"}]},
        "package":{"name":"mck/python"},"dependencies":[],
        "options":{"irVersion":version,"typesOnly":false},"contextDigest":"a".repeat(64),
        "output":{"operation":"morphir.frontend.compileModel","profile":"morphir-ir","codec":"morphir-json","envelopeVersion":"0.1.0-draft.1","irVersion":version},
    }})
}

#[test]
fn draft_session_selects_complete_tuples_and_each_lower_limit() {
    let extension = NativeExtension::frontend_backend(PythonExtension).unwrap();
    let session = extension.open_protocol();
    let selected = send(
        session.as_ref(),
        initialize(json!(["0.2.0-draft.1", "0.1"]), Some(host_offer())),
    );
    assert!(selected.get("error").is_none(), "{selected}");
    assert_eq!(selected["result"]["protocolVersion"], "0.2.0-draft.1");
    assert_eq!(
        selected["result"]["capabilities"]["modelTransport"],
        host_offer()
    );
    let compiled = send(session.as_ref(), compile_model("3.0.0"));
    assert!(compiled.get("error").is_none(), "{compiled}");
    assert_eq!(compiled["result"]["model"]["irVersion"], "3.0.0");
    let refused = send(session.as_ref(), compile_model("4.0.0"));
    assert!(
        refused.get("error").is_some(),
        "unoffered tuple admitted: {refused}"
    );
    let again = send(session.as_ref(), initialize(json!(["0.1"]), None));
    assert!(again.get("error").is_some(), "session was renegotiated");
    let still_refused = send(session.as_ref(), compile_model("4.0.0"));
    assert!(still_refused.get("error").is_some());
}

#[test]
fn legacy_or_other_drafts_cannot_admit_model_operations() {
    let extension = NativeExtension::frontend_backend(PythonExtension).unwrap();
    let legacy = extension.open_protocol();
    let selected = send(
        legacy.as_ref(),
        initialize(json!(["0.1"]), Some(host_offer())),
    );
    assert!(selected.get("error").is_none(), "{selected}");
    assert_eq!(selected["result"]["protocolVersion"], "0.1");
    assert!(selected["result"]["capabilities"]["modelTransport"].is_null());
    assert!(
        send(legacy.as_ref(), compile_model("3.0.0"))
            .get("error")
            .is_some()
    );
    for (versions, offer) in [
        (json!(["0.2.0-draft.2"]), Some(host_offer())),
        (json!(["0.2.0-draft.1"]), None),
    ] {
        let session = extension.open_protocol();
        let refused = send(session.as_ref(), initialize(versions, offer));
        assert_eq!(refused["error"]["code"], -32011);
    }
}

fn tuple(operation: &str, profile: &str, codec: &str, ir_version: &str) -> Value {
    json!({"operation":operation,"profile":profile,"codec":codec,
        "envelopeVersion":"0.1.0-draft.1","irVersion":ir_version})
}

fn offer(tuples: Vec<Value>) -> Value {
    json!({"tuples":tuples,
        "limits":{"maxEncodedBytes":1048576,"maxDecodedBytes":786432,"maxDepth":128,"maxNodes":100000},
        "guarantees":[]})
}

const COMPILE: &str = "morphir.frontend.compileModel";
const GENERATE: &str = "morphir.backend.generateModel";

fn ion(operation: &str) -> Value {
    tuple(operation, "morphir-model", "ion-binary", "4.0.0")
}

fn json_ir4(operation: &str) -> Value {
    tuple(operation, "morphir-ir", "morphir-json", "4.0.0")
}

fn generate_model(model: &Value) -> Value {
    json!({"jsonrpc":"2.0","id":3,"method":GENERATE,"params":{
        "model":model,"target":"python","contextDigest":"a".repeat(64),
        "requiredGuarantees":[],"options":{},
        "input":tuple(GENERATE, "morphir-ir", "morphir-json", model["irVersion"].as_str().unwrap()),
    }})
}

/// The response is a JSON-RPC error with this code and message text.
fn assert_refused(response: &Value, code: i64, text: &str) {
    assert!(response.get("result").is_none(), "admitted: {response}");
    assert_eq!(response["error"]["code"], code, "{}", response["error"]);
    let message = response["error"]["message"].as_str().unwrap();
    assert!(message.contains(text), "{message}");
}

/// The host default is Ion, which this guest does not serve. The host also
/// offers JSON and does not require Ion, so the guest agrees on JSON, in the
/// host's order, and both model operations work (finos/morphir-gleam#31).
#[test]
fn guest_negotiates_json_when_the_host_prefers_ion_but_offers_both() {
    let extension = NativeExtension::frontend_backend(PythonExtension).unwrap();
    let session = extension.open_protocol();
    let host = offer(vec![
        ion(COMPILE),
        ion(GENERATE),
        json_ir4(COMPILE),
        json_ir4(GENERATE),
    ]);
    let selected = send(
        session.as_ref(),
        initialize(json!(["0.2.0-draft.1", "0.1"]), Some(host)),
    );
    assert!(selected.get("error").is_none(), "{selected}");
    assert_eq!(selected["result"]["protocolVersion"], "0.2.0-draft.1");
    assert_eq!(
        selected["result"]["capabilities"]["modelTransport"]["tuples"],
        json!([json_ir4(COMPILE), json_ir4(GENERATE)])
    );
    let compiled = send(session.as_ref(), compile_model("4.0.0"));
    assert!(compiled.get("error").is_none(), "{}", compiled["error"]);
    assert_eq!(
        compiled["result"]["model"]["payload"]["codec"],
        "morphir-json"
    );
    let generated = send(
        session.as_ref(),
        generate_model(&compiled["result"]["model"]),
    );
    assert!(generated.get("error").is_none(), "{}", generated["error"]);
    assert_eq!(generated["result"]["success"], true);
}

/// A host that offers only Ion leaves no tuple this guest can serve. The
/// session starts with no model tuple, the guest never converts to JSON, and
/// the MEP `0.1` compile method still works in that session.
#[test]
fn a_host_that_offers_only_ion_gets_no_model_operation() {
    let extension = NativeExtension::frontend_backend(PythonExtension).unwrap();
    let session = extension.open_protocol();
    let selected = send(
        session.as_ref(),
        initialize(
            json!(["0.2.0-draft.1"]),
            Some(offer(vec![ion(COMPILE), ion(GENERATE)])),
        ),
    );
    assert!(selected.get("error").is_none(), "{}", selected["error"]);
    assert_eq!(selected["result"]["protocolVersion"], "0.2.0-draft.1");
    assert_eq!(
        selected["result"]["capabilities"]["modelTransport"]["tuples"],
        json!([])
    );
    let refused = send(session.as_ref(), compile_model("4.0.0"));
    assert_refused(&refused, -32013, "not negotiated");
    let mut legacy = compile_model("4.0.0");
    legacy["method"] = json!("morphir.frontend.compile");
    legacy["params"]["options"]["irVersion"] = json!("4");
    for member in ["output", "contextDigest"] {
        legacy["params"].as_object_mut().unwrap().remove(member);
    }
    let compiled = send(session.as_ref(), legacy);
    assert!(compiled.get("error").is_none(), "{}", compiled["error"]);
    assert_eq!(compiled["result"]["success"], true);
}

/// Admission of a compile tuple does not admit generation of that model.
#[test]
fn compile_support_does_not_grant_generation() {
    let extension = NativeExtension::frontend_backend(PythonExtension).unwrap();
    let session = extension.open_protocol();
    let selected = send(
        session.as_ref(),
        initialize(
            json!(["0.2.0-draft.1"]),
            Some(offer(vec![json_ir4(COMPILE)])),
        ),
    );
    assert!(selected.get("error").is_none(), "{selected}");
    let compiled = send(session.as_ref(), compile_model("4.0.0"));
    assert!(compiled.get("error").is_none(), "{}", compiled["error"]);
    let refused = send(
        session.as_ref(),
        generate_model(&compiled["result"]["model"]),
    );
    assert_refused(&refused, -32013, "not negotiated");

    // Positive control: the same request succeeds once generation is agreed.
    let both = extension.open_protocol();
    send(
        both.as_ref(),
        initialize(
            json!(["0.2.0-draft.1"]),
            Some(offer(vec![json_ir4(COMPILE), json_ir4(GENERATE)])),
        ),
    );
    let generated = send(both.as_ref(), generate_model(&compiled["result"]["model"]));
    assert!(generated.get("error").is_none(), "{}", generated["error"]);
    assert_eq!(generated["result"]["success"], true);
}

/// A model operation that names another envelope version is refused, in
/// both directions, even when every other tuple member was agreed.
#[test]
fn a_wrong_envelope_version_is_refused() {
    let extension = NativeExtension::frontend_backend(PythonExtension).unwrap();
    let session = extension.open_protocol();
    send(
        session.as_ref(),
        initialize(
            json!(["0.2.0-draft.1"]),
            Some(offer(vec![json_ir4(COMPILE), json_ir4(GENERATE)])),
        ),
    );
    let mut wrong_output = compile_model("4.0.0");
    wrong_output["params"]["output"]["envelopeVersion"] = json!("0.2.0-draft.1");
    let refused = send(session.as_ref(), wrong_output);
    assert_refused(&refused, -32602, "unsupported_tuple");

    let compiled = send(session.as_ref(), compile_model("4.0.0"));
    assert!(compiled.get("error").is_none(), "{}", compiled["error"]);
    let model = &compiled["result"]["model"];
    // Positive control: the unchanged request is admitted in this session.
    let generated = send(session.as_ref(), generate_model(model));
    assert!(generated.get("error").is_none(), "{}", generated["error"]);
    assert_eq!(generated["result"]["success"], true);
    let mut wrong_input = generate_model(model);
    wrong_input["params"]["input"]["envelopeVersion"] = json!("0.2.0-draft.1");
    assert_refused(
        &send(session.as_ref(), wrong_input),
        -32602,
        "unsupported_tuple",
    );
    let mut wrong_model = generate_model(model);
    wrong_model["params"]["model"]["envelopeVersion"] = json!("0.2.0-draft.1");
    assert_refused(
        &send(session.as_ref(), wrong_model),
        -32602,
        "unsupported_tuple",
    );
}
