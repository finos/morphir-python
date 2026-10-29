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
