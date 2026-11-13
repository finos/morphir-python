//! Shipped guests expose the supported draft without the SDK's legacy offer.
use morphir_extension_sdk::{Extension, NativeProtocol, protocol::ExtensionRequest};
use morphir_python_binding::{PythonExtension, guest::PythonSession};
use serde_json::{Value, json};

fn request(method: &str, versions: Value) -> ExtensionRequest {
    ExtensionRequest::new(
        method,
        json!({
            "protocolVersions": versions,
            "host": {"name": "test", "version": "1"},
            "modelTransport": PythonExtension::capabilities().model_transport.unwrap(),
        }),
        1,
    )
    .unwrap()
}

#[test]
fn describes_only_the_supported_draft_and_negotiates_it_from_a_mixed_offer() {
    let session = PythonSession::new();
    let versions = json!(["0.1", "0.2.0-draft.1"]);
    let described = session.handle(request("morphir.extension.describe", versions.clone()));
    assert_eq!(
        described.result.unwrap()["protocolVersions"],
        json!(["0.2.0-draft.1"])
    );
    let initialized = session.handle(request("morphir.initialize", versions));
    assert_eq!(
        initialized.result.unwrap()["protocolVersion"],
        "0.2.0-draft.1"
    );
}

#[test]
fn legacy_and_other_drafts_are_refused_without_initializing_the_session() {
    for method in ["morphir.extension.describe", "morphir.initialize"] {
        for version in ["0.1", "0.1.0", "0.2.0-draft.2"] {
            let session = PythonSession::new();
            let refused = session.handle(request(method, json!([version])));
            assert_eq!(refused.error.unwrap().code, -32011);
            let initialized =
                session.handle(request("morphir.initialize", json!(["0.2.0-draft.1"])));
            assert!(initialized.error.is_none());
        }
    }
}

#[test]
fn malformed_offers_are_not_repaired_and_missing_model_offer_cannot_fall_back() {
    for method in ["morphir.extension.describe", "morphir.initialize"] {
        let session = PythonSession::new();
        let refused = session.handle(request(method, json!(["0.2.0-draft.1", 1])));
        assert_eq!(refused.error.unwrap().code, -32602);
    }
    let session = PythonSession::new();
    let mut start = request("morphir.initialize", json!(["0.2.0-draft.1", "0.1"]));
    start
        .params
        .as_object_mut()
        .unwrap()
        .remove("modelTransport");
    assert_eq!(session.handle(start).error.unwrap().code, -32602);
}
