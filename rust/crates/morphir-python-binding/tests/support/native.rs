//! Native protocol fixture with a completed initialization handshake.

use morphir_extension_sdk::{
    Extension, NativeExtension,
    protocol::{ExtensionRequest, InitializeParams, MEP_VERSION, PeerInfo, methods},
};
use morphir_python_binding::PythonExtension;

pub fn an_initialized_extension() -> NativeExtension {
    let extension = NativeExtension::frontend_backend(PythonExtension).unwrap();
    let response = extension.protocol().handle(
        ExtensionRequest::new(
            methods::INITIALIZE,
            InitializeParams {
                model_transport: None,
                protocol_versions: vec![MEP_VERSION.into()],
                host: PeerInfo {
                    kind: Default::default(),
                    name: "binding-test".into(),
                    version: "1.0.0".into(),
                },
            },
            0,
        )
        .unwrap(),
    );
    assert!(response.error.is_none(), "{:?}", response.error);
    let mut capabilities = PythonExtension::capabilities();
    assert!(capabilities.model_transport.is_some());
    // This fixture deliberately selects legacy0.1; model support is static
    // inventory, but must be absent from the selected legacy session.
    capabilities.model_transport = None;
    let expected = serde_json::to_value(capabilities).unwrap();
    assert_eq!(expected["frontend"]["multiDocument"], true);
    assert_eq!(response.result.unwrap()["capabilities"], expected);
    let response = extension
        .protocol()
        .handle(ExtensionRequest::new(methods::CAPABILITIES, serde_json::json!({}), 1).unwrap());
    assert!(response.error.is_none(), "{:?}", response.error);
    assert_eq!(response.result.unwrap(), expected);
    extension
}
