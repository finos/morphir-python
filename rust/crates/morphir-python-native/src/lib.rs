//! Private CPython bridge to the Morphir Python compiler.
//!
//! The `morphir_python_native._native` module exposes two functions that take and
//! return JSON text. They are a private boundary for `morphir_tools.python`; the
//! public, typed Python API lives there.
//!
//! Each call extracts its whole request into owned Rust values while attached to
//! the interpreter, then detaches and runs the compiler. Detached work never
//! touches Python objects or calls back into Python, and holds no state shared
//! between calls, so concurrent calls from several threads are independent.
//! Panics are caught and reported as an internal-error result, never as a Python
//! `PanicException`.

use std::panic::{AssertUnwindSafe, catch_unwind};

use morphir_extension_sdk::prelude::*;
use morphir_python_binding::PythonExtension;
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Revision of the JSON contract between this module and `morphir_tools.python`.
///
/// Increment it whenever a request or result member changes meaning, is added, or
/// is removed. The tools package refuses to use a module with another revision.
pub const BRIDGE_API: u32 = 1;

/// One source document, identified by its path relative to the source root.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceInput {
    pub path: String,
    pub text: String,
}

/// A complete compilation request, owned by Rust before the interpreter is released.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct CompileInput {
    pub package: String,
    pub sources: Vec<SourceInput>,
    /// `None` exposes every module; an empty list exposes none.
    pub exposed_modules: Option<Vec<String>>,
    /// `"3"` or `"4"`.
    pub ir_version: String,
}

/// A zero-based line and UTF-16 character offset.
#[derive(Debug, Serialize)]
pub struct PositionOutput {
    pub line: u32,
    pub character: u32,
}

/// The source document and range a diagnostic refers to.
#[derive(Debug, Serialize)]
pub struct LocationOutput {
    pub path: String,
    pub start: PositionOutput,
    pub end: PositionOutput,
}

/// One compiler diagnostic.
#[derive(Debug, Serialize)]
pub struct DiagnosticOutput {
    pub severity: &'static str,
    pub code: Option<String>,
    pub message: String,
    pub location: Option<LocationOutput>,
}

/// One generated file.
#[derive(Debug, Serialize)]
pub struct ArtifactOutput {
    pub path: String,
    pub content: String,
}

/// The result of one bridge call.
///
/// `internal_error` is set only when the compiler failed in a way that is not a
/// language diagnostic, such as a panic or an invalid bridge request.
#[derive(Debug, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BridgeOutput {
    pub success: bool,
    /// The compiled IR document as JSON text, so that number lexemes and member
    /// order reach the Python codecs unchanged.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ir: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub artifacts: Option<Vec<ArtifactOutput>>,
    pub diagnostics: Vec<DiagnosticOutput>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub internal_error: Option<String>,
}

impl BridgeOutput {
    fn internal(message: impl Into<String>) -> Self {
        Self {
            internal_error: Some(message.into()),
            ..Self::default()
        }
    }
}

fn severity(value: &DiagnosticSeverity) -> &'static str {
    match value {
        DiagnosticSeverity::Error => "error",
        DiagnosticSeverity::Warning => "warning",
        DiagnosticSeverity::Info => "info",
        DiagnosticSeverity::Hint => "hint",
    }
}

fn diagnostics(items: Vec<Diagnostic>) -> Vec<DiagnosticOutput> {
    items
        .into_iter()
        .map(|item| DiagnosticOutput {
            severity: severity(&item.severity),
            code: item.code,
            message: item.message,
            location: item.location.map(|location| LocationOutput {
                path: location.uri,
                start: PositionOutput {
                    line: location.range.start.line,
                    character: location.range.start.character,
                },
                end: PositionOutput {
                    line: location.range.end.line,
                    character: location.range.end.character,
                },
            }),
        })
        .collect()
}

/// Build the SDK request the bridge sends to the compiler.
pub fn compile_request(input: CompileInput) -> CompileRequest {
    CompileRequest {
        language_id: "python".into(),
        sources: SourceSet {
            root: None,
            documents: input
                .sources
                .into_iter()
                .map(|source| SourceDocument {
                    uri: source.path,
                    language_id: "python".into(),
                    version: 1,
                    text: source.text,
                })
                .collect(),
        },
        package: CompilePackage {
            name: input.package,
            exposed_modules: input.exposed_modules,
        },
        dependencies: vec![],
        options: CompileOptions {
            types_only: false,
            ir_version: input.ir_version,
            ..Default::default()
        },
        baseline: None,
    }
}

/// Compile an owned request with the native frontend. Pure Rust; never touches Python.
pub fn compile_input(input: CompileInput) -> BridgeOutput {
    match PythonExtension.compile(compile_request(input)) {
        Ok(result) => BridgeOutput {
            success: result.success && result.ir.is_some(),
            ir: if result.success {
                result.ir.as_ref().map(Value::to_string)
            } else {
                None
            },
            artifacts: None,
            diagnostics: diagnostics(result.diagnostics),
            internal_error: None,
        },
        Err(error) => BridgeOutput::internal(error.to_string()),
    }
}

/// Generate Python from owned IR with the native backend. Pure Rust; never touches Python.
pub fn generate_input(ir: Value) -> BridgeOutput {
    let request = GenerateRequest {
        ir,
        target: "python".into(),
        options: Default::default(),
    };
    match PythonExtension.generate(request) {
        Ok(result) => BridgeOutput {
            success: result.success,
            ir: None,
            artifacts: Some(if result.success {
                result
                    .artifacts
                    .into_iter()
                    .map(|artifact| ArtifactOutput {
                        path: artifact.path,
                        content: artifact.content,
                    })
                    .collect()
            } else {
                vec![]
            }),
            diagnostics: diagnostics(result.diagnostics),
            internal_error: None,
        },
        Err(error) => BridgeOutput::internal(error.to_string()),
    }
}

/// Parse, run and serialize one request, converting panics into an internal error.
///
/// The SDK enables serde_json's `arbitrary_precision`, so numbers keep their lexemes.
pub fn run_json<I, F>(request: &str, operation: F) -> String
where
    I: for<'de> Deserialize<'de>,
    F: FnOnce(I) -> BridgeOutput,
{
    let output = match serde_json::from_str::<I>(request) {
        Ok(input) => catch_unwind(AssertUnwindSafe(|| operation(input))).unwrap_or_else(|panic| {
            let detail = panic
                .downcast_ref::<&str>()
                .map(|text| (*text).to_owned())
                .or_else(|| panic.downcast_ref::<String>().cloned())
                .unwrap_or_else(|| "unknown panic".into());
            BridgeOutput::internal(format!("the native compiler panicked: {detail}"))
        }),
        Err(error) => BridgeOutput::internal(format!("invalid bridge request: {error}")),
    };
    serde_json::to_string(&output).unwrap_or_else(|error| {
        format!(r#"{{"success":false,"diagnostics":[],"internalError":"cannot serialize result: {error}"}}"#)
    })
}

#[cfg(feature = "python")]
#[pyo3::pymodule(name = "_native")]
mod native {
    use pyo3::prelude::*;

    #[pymodule_export]
    const BRIDGE_API: u32 = super::BRIDGE_API;

    #[pymodule_export]
    #[allow(non_upper_case_globals)]
    const __version__: &str = env!("CARGO_PKG_VERSION");

    /// Records the version the linked `morphir-python-binding` compiler reports.
    #[pymodule_init]
    fn init(module: &Bound<'_, PyModule>) -> PyResult<()> {
        use morphir_extension_sdk::Extension;
        module.add(
            "COMPILER_VERSION",
            morphir_python_binding::PythonExtension::info().version,
        )
    }

    /// Compile a JSON request and return a JSON result.
    #[pyfunction]
    fn compile(py: Python<'_>, request: String) -> String {
        py.detach(move || super::run_json(&request, super::compile_input))
    }

    /// Generate Python from a versioned IR document's JSON text and return a JSON result.
    #[pyfunction]
    fn generate(py: Python<'_>, ir: String) -> String {
        py.detach(move || super::run_json(&ir, super::generate_input))
    }
}
