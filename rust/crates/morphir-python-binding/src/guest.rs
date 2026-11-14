//! The Python guest's protocol offer, shared by stdio and WASM.
//!
//! SDK 0.4.0 unconditionally adds the retired `0.1` offer. Keep its dispatch,
//! model admission and lifecycle, but expose only the Python guest's supported
//! draft. This is a guest policy, not a host-side compatibility conversion.

use crate::PythonExtension;
use morphir_extension_sdk::{
    __ProtocolSession, __dispatch_backend, __dispatch_frontend, __dispatch_request, ExtensionError,
    ExtensionType, NativeProtocol,
    protocol::{ExtensionRequest, ExtensionResponse, RpcError, methods},
};
use serde_json::json;

/// An independent Python guest session supporting exactly MEP 0.2.0-draft.1.
#[derive(Default)]
pub struct PythonSession(__ProtocolSession);

impl PythonSession {
    /// Create a guest session before initialization.
    pub const fn new() -> Self {
        Self(__ProtocolSession::new())
    }
}

impl NativeProtocol for PythonSession {
    fn handle(&self, request: ExtensionRequest) -> ExtensionResponse {
        self.0.dispatch(&request, || {
            let mut request = request.clone();
            let handshake = matches!(
                request.method.as_str(),
                methods::DESCRIBE | methods::INITIALIZE
            );
            if handshake
                && let Some(versions) = request
                    .params
                    .get_mut("protocolVersions")
                    .and_then(|v| v.as_array_mut())
                && versions.iter().all(serde_json::Value::is_string)
            {
                let offered: Vec<String> = versions
                    .iter()
                    .filter_map(|v| v.as_str().map(String::from))
                    .collect();
                versions.retain(|v| v == "0.2.0-draft.1");
                if versions.is_empty() {
                    return ExtensionResponse::from_extension_error_with_id(
                        request.id,
                        &ExtensionError::ProtocolVersionMismatch {
                            host_versions: offered,
                            extension_versions: vec!["0.2.0-draft.1".into()],
                        },
                    );
                }
            }
            if request.method == methods::INITIALIZE
                && request
                    .params
                    .get("modelTransport")
                    .is_none_or(|v| v.is_null())
            {
                return ExtensionResponse::error_with_id(
                    request.id,
                    RpcError::invalid_params("MEP 0.2.0-draft.1 requires a modelTransport offer"),
                );
            }
            let mut response = __dispatch_request::<PythonExtension>(
                &request,
                &[
                    __dispatch_frontend::<PythonExtension>,
                    __dispatch_backend::<PythonExtension>,
                ],
                &[ExtensionType::Frontend, ExtensionType::Backend],
            );
            if request.method == methods::DESCRIBE
                && let Some(claims) = response.result.as_mut()
            {
                claims["protocolVersions"] = json!(["0.2.0-draft.1"]);
            }
            response
        })
    }
}

#[cfg(target_arch = "wasm32")]
mod wasm {
    use super::*;
    use extism_pdk::*;
    use morphir_extension_sdk::{Extension, extism_pdk};

    #[plugin_fn]
    pub fn morphir_extension_info() -> FnResult<Json<morphir_extension_sdk::ExtensionInfo>> {
        Ok(Json(PythonExtension::info()))
    }

    #[plugin_fn]
    pub fn morphir_extension_capabilities()
    -> FnResult<Json<morphir_extension_sdk::ExtensionCapabilities>> {
        Ok(Json(PythonExtension::capabilities()))
    }

    #[plugin_fn]
    pub fn handle(Json(request): Json<ExtensionRequest>) -> FnResult<Json<ExtensionResponse>> {
        static SESSION: PythonSession = PythonSession::new();
        Ok(Json(SESSION.handle(request)))
    }
}
