//! Explicit JSON-model admission around the shared compiler, without transcoding.
use crate::{PythonExtension, error};
use morphir_extension_sdk::model::*;
use morphir_extension_sdk::prelude::*;

pub(crate) fn support() -> ModelTransportSupport {
    ModelTransportSupport {
        tuples: [ModelOperation::CompileModel, ModelOperation::GenerateModel]
            .into_iter()
            .flat_map(|operation| {
                ["3.0.0", "4.0.0"].map(|version| ModelTransportTuple {
                    operation,
                    profile: "morphir-ir".into(),
                    codec: ModelCodec::MorphirJson,
                    envelope_version: MODEL_ENVELOPE_VERSION.into(),
                    ir_version: version.into(),
                })
            })
            .collect(),
        // Base64 payloads leave at least 4 MiB for envelope/source metadata in
        // the process transport's 16 MiB complete-message bound.
        limits: ModelTransportLimits {
            max_encoded_bytes: 12 * 1024 * 1024,
            max_decoded_bytes: 8 * 1024 * 1024,
            max_depth: 128,
            max_nodes: 100_000,
        },
        guarantees: vec![],
    }
}

fn invalid(error: impl std::fmt::Display) -> ExtensionError {
    ExtensionError::InvalidParams(format!("MEP model admission: {error}"))
}

fn admit(method: &str, value: &serde_json::Value) -> Result<()> {
    let support = support();
    let admitted = NegotiatedModelTransport::select(&support, &support).map_err(invalid)?;
    let mut capabilities = PythonExtension::capabilities();
    capabilities.model_transport = Some(support);
    validate_model_invocation(&admitted, &capabilities, method, value).map_err(invalid)
}

// Native SDK builds can inspect Ion evidence, but WASM cannot. Keep this
// adapter's accepted subset identical across runtimes, including sidecars.
fn require_json(model: &MorphirModel) -> Result<()> {
    if model.payload.codec != ModelCodec::MorphirJson
        || model
            .evidence
            .iter()
            .any(|item| item.evidence.codec != ModelCodec::MorphirJson)
    {
        return Err(invalid(
            "Python model transport is JSON-only, including evidence",
        ));
    }
    Ok(())
}

pub(crate) fn compile(
    extension: &PythonExtension,
    request: CompileModelRequest,
) -> Result<CompileModelResult> {
    for dependency in &request.dependencies {
        require_json(&dependency.model)?;
    }
    admit(
        "morphir.frontend.compileModel",
        &serde_json::to_value(&request)?,
    )?;
    if !request.dependencies.is_empty() {
        return Ok(CompileModelResult::Failed {
            diagnostics: vec![error("PY001", "Expected Python and no dependencies")],
        });
    }
    let model_id = request.package.name.clone();
    let result = extension.compile(CompileRequest {
        language_id: request.language_id,
        sources: request.sources,
        package: request.package,
        dependencies: vec![],
        options: request.options,
        baseline: None,
    })?;
    if !result.success {
        return Ok(CompileModelResult::Failed {
            diagnostics: result.diagnostics,
        });
    }
    let ir = result
        .ir
        .ok_or_else(|| invalid("successful compiler result is missing IR"))?;
    let bytes = bounded_json(&ir, support().limits.max_decoded_bytes)?;
    let payload = ModelPayload::from_bytes(ModelCodec::MorphirJson, &bytes).map_err(invalid)?;
    let model = MorphirModel {
        envelope_version: MODEL_ENVELOPE_VERSION.into(),
        model_id,
        revision: format!("sha256:{}", payload.sha256),
        ir_version: request.output.ir_version.clone(),
        profile: request.output.profile.clone(),
        payload,
        evidence: vec![],
        critical: vec![],
    };
    retain_model(&model, &request.output, &support().limits).map_err(invalid)?;
    Ok(CompileModelResult::Compiled {
        model: Box::new(model),
        diagnostics: result.diagnostics,
        modules: result.modules,
    })
}

pub(crate) fn generate(
    extension: &PythonExtension,
    request: GenerateModelRequest,
) -> Result<GenerateResult> {
    require_json(&request.model)?;
    admit(
        "morphir.backend.generateModel",
        &serde_json::to_value(&request)?,
    )?;
    let retained =
        retain_model(&request.model, &request.input, &support().limits).map_err(invalid)?;
    let limits = support().limits;
    let source = std::str::from_utf8(retained.bytes()).map_err(invalid)?;
    let ir = morphir_json::read(
        source,
        &mut JsonBudget {
            remaining: limits.max_nodes,
            depth: limits.max_depth as usize,
            string_bytes: limits.max_decoded_bytes as usize,
        },
    )
    .map_err(invalid)?;
    extension.generate(GenerateRequest {
        ir,
        target: request.target,
        options: request.options,
    })
}

/// Stop JSON serialization before extending the payload buffer beyond its bound.
fn bounded_json(value: &serde_json::Value, limit: u32) -> Result<Vec<u8>> {
    struct Buffer {
        bytes: Vec<u8>,
        limit: usize,
    }
    impl std::io::Write for Buffer {
        fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
            if self.bytes.len().saturating_add(bytes.len()) > self.limit {
                return Err(std::io::Error::new(
                    std::io::ErrorKind::InvalidData,
                    "model payload exceeds decoded limit",
                ));
            }
            self.bytes.extend_from_slice(bytes);
            Ok(bytes.len())
        }
        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }
    let mut buffer = Buffer {
        bytes: Vec::new(),
        limit: limit as usize,
    };
    serde_json::to_writer(&mut buffer, value).map_err(invalid)?;
    Ok(buffer.bytes)
}

// Materialize only after SDK admission, using the published literal-JSON reader
// so serde-private-looking keys cannot acquire a different scalar meaning.
struct JsonBudget {
    remaining: u32,
    depth: usize,
    string_bytes: usize,
}
impl morphir_json::ReadBudget for JsonBudget {
    type Error = &'static str;
    fn before_value(
        &mut self,
        depth: usize,
        _: morphir_json::ValueKind,
    ) -> std::result::Result<(), Self::Error> {
        if depth >= self.depth {
            return Err("model depth limit");
        }
        self.remaining = self.remaining.checked_sub(1).ok_or("model node limit")?;
        Ok(())
    }
    fn before_string(&mut self, value: &str) -> std::result::Result<(), Self::Error> {
        if value.len() > self.string_bytes {
            Err("model string limit")
        } else {
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn output_json_stops_at_its_decoded_budget() {
        let value = serde_json::json!("λ");
        assert_eq!(bounded_json(&value, 4).unwrap(), "\"λ\"".as_bytes());
        assert!(
            bounded_json(&value, 3)
                .unwrap_err()
                .to_string()
                .contains("decoded limit")
        );
    }
}
