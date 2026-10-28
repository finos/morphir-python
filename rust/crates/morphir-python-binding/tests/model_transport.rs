//! The model boundary retains supported semantics and refuses unsupported admission.
use morphir_extension_sdk::model::*;
use morphir_extension_sdk::prelude::*;
use morphir_python_binding::PythonExtension;
use serde_json::{Value, json};

fn a_request(version: &str) -> CompileModelRequest {
    CompileModelRequest {
        language_id: "python".into(),
        sources: SourceSet {
            root: None,
            documents: vec![SourceDocument {
                uri: "model.py".into(), language_id: "python".into(), version: 1,
                text: "from dataclasses import dataclass\n@dataclass(frozen=True)\nclass Box:\n    value: int\n".into(),
            }],
        },
        package: CompilePackage { name: "acme".into(), exposed_modules: None },
        dependencies: vec![],
        options: CompileOptions { ir_version: version.into(), ..Default::default() },
        context_digest: "a".repeat(64),
        output: ModelTransportTuple {
            operation: ModelOperation::CompileModel, profile: "morphir-ir".into(),
            codec: ModelCodec::MorphirJson, envelope_version: MODEL_ENVELOPE_VERSION.into(), ir_version: version.into(),
        },
    }
}

fn a_model(version: &str) -> MorphirModel {
    match PythonExtension.compile_model(a_request(version)).unwrap() {
        CompileModelResult::Compiled { model, .. } => *model,
        CompileModelResult::Failed { diagnostics } => panic!("{diagnostics:?}"),
    }
}

fn generation(model: MorphirModel) -> GenerateModelRequest {
    GenerateModelRequest {
        input: ModelTransportTuple {
            operation: ModelOperation::GenerateModel,
            profile: "morphir-ir".into(),
            codec: ModelCodec::MorphirJson,
            envelope_version: MODEL_ENVELOPE_VERSION.into(),
            ir_version: model.ir_version.clone(),
        },
        model,
        target: "python".into(),
        context_digest: "a".repeat(64),
        required_guarantees: vec![],
        options: Default::default(),
    }
}

#[test]
fn json_models_compile_and_generate_with_the_legacy_semantics() {
    for version in ["3.0.0", "4.0.0"] {
        let model = a_model(version);
        assert_eq!(model.envelope_version, MODEL_ENVELOPE_VERSION);
        assert_eq!(model.ir_version, version);
        assert_eq!(model.model_id, "acme");
        let request = generation(model);
        let retained = retain_model(
            &request.model,
            &request.input,
            &ModelTransportLimits {
                max_encoded_bytes: 1024 * 1024,
                max_decoded_bytes: 1024 * 1024,
                max_depth: 128,
                max_nodes: 100_000,
            },
        )
        .unwrap();
        let ir: Value = serde_json::from_slice(retained.bytes()).unwrap();
        let legacy = PythonExtension
            .generate(GenerateRequest {
                ir,
                target: "python".into(),
                options: Default::default(),
            })
            .unwrap();
        let generated = PythonExtension.generate_model(request).unwrap();
        assert!(generated.success, "{:?}", generated.diagnostics);
        let mut recompile = a_request(version);
        recompile.sources.documents = generated
            .artifacts
            .iter()
            .map(|artifact| SourceDocument {
                uri: artifact.path.clone(),
                language_id: "python".into(),
                version: 1,
                text: artifact.content.clone(),
            })
            .collect();
        let reparsed = PythonExtension.compile_model(recompile).unwrap();
        let CompileModelResult::Compiled {
            model: reparsed, ..
        } = reparsed
        else {
            panic!("generated model should recompile")
        };
        assert_eq!(reparsed.payload, a_model(version).payload);
        assert_eq!(
            serde_json::to_value(generated).unwrap(),
            serde_json::to_value(legacy).unwrap()
        );
    }
}

#[test]
fn model_compilation_preserves_language_diagnostics() {
    let mut request = a_request("4.0.0");
    request.sources.documents[0].text = "import os\n".into();
    let legacy = PythonExtension
        .compile(CompileRequest {
            language_id: request.language_id.clone(),
            sources: request.sources.clone(),
            package: request.package.clone(),
            dependencies: vec![],
            options: request.options.clone(),
            baseline: None,
        })
        .unwrap();
    assert!(!legacy.success);
    let CompileModelResult::Failed { diagnostics } =
        PythonExtension.compile_model(request).unwrap()
    else {
        panic!("unsupported source must fail")
    };
    assert_eq!(
        serde_json::to_value(diagnostics).unwrap(),
        serde_json::to_value(legacy.diagnostics).unwrap()
    );
}

#[test]
fn malformed_envelopes_guarantees_and_unadvertised_forms_are_refused() {
    let baseline = generation(a_model("4.0.0"));
    let mut value = serde_json::to_value(&baseline).unwrap();
    value["model"]["critical"] = json!([]);
    for (path, invalid) in [
        ("/model/payload/sha256", json!("0".repeat(64))),
        ("/model/payload/decodedByteLength", json!(1)),
        ("/model/payload/content", json!("not canonical base64")),
        ("/model/critical", json!(["future.required"])),
        ("/model/irVersion", json!("3.0.0")),
        ("/input/codec", json!("ion-binary")),
        ("/input/profile", json!("rich-model")),
        ("/input/operation", json!("morphir.frontend.compileModel")),
        (
            "/requiredGuarantees",
            json!([{"guarantee":"example.typed","scope":"model:acme"}]),
        ),
    ] {
        let mut invalid_request = value.clone();
        *invalid_request.pointer_mut(path).unwrap() = invalid;
        let request = serde_json::from_value(invalid_request).unwrap();
        assert!(
            PythonExtension.generate_model(request).is_err(),
            "accepted {path}"
        );
    }
    let mut request = a_request("4.0.0");
    request.output.ir_version = "3.1.0".into();
    assert!(PythonExtension.compile_model(request).is_err());
}

#[test]
fn model_round_trip_retains_large_integer_precision_and_v3_refuses_it() {
    let decimal = "1234567890123456789012345678901234567890";
    for version in ["3.0.0", "4.0.0"] {
        let mut request = a_request(version);
        request.options.types_only = false;
        request.sources.documents[0].text = format!("def number() -> int:\n    return {decimal}\n");
        match PythonExtension.compile_model(request).unwrap() {
            CompileModelResult::Compiled { model, .. } => {
                assert_eq!(version, "4.0.0");
                let generated = PythonExtension.generate_model(generation(*model)).unwrap();
                assert!(generated.success, "{:?}", generated.diagnostics);
                assert!(
                    generated
                        .artifacts
                        .iter()
                        .any(|artifact| artifact.content.contains(decimal))
                );
            }
            CompileModelResult::Failed { diagnostics } => {
                assert_eq!(version, "3.0.0");
                assert!(
                    diagnostics
                        .iter()
                        .any(|item| item.message.contains("64-bit"))
                );
            }
        }
    }
}

#[test]
fn aggregate_nodes_and_dependency_support_are_bounded() {
    let mut request = generation(a_model("4.0.0"));
    let retained = retain_model(
        &request.model,
        &request.input,
        &ModelTransportLimits {
            max_encoded_bytes: 1024 * 1024,
            max_decoded_bytes: 1024 * 1024,
            max_depth: 128,
            max_nodes: 100_000,
        },
    )
    .unwrap();
    let mut ir: Value = serde_json::from_slice(retained.bytes()).unwrap();
    ir["extra"] = json!(vec![0; 100_001]);
    request.model.payload =
        ModelPayload::from_bytes(ModelCodec::MorphirJson, &serde_json::to_vec(&ir).unwrap())
            .unwrap();
    let error = PythonExtension.generate_model(request).unwrap_err();
    assert!(error.to_string().contains("node_limit"), "{error}");

    let mut request = a_request("4.0.0");
    request.dependencies.push(CompileModelDependency {
        package_name: "dep".into(),
        model: a_model("4.0.0"),
    });
    let CompileModelResult::Failed { diagnostics } =
        PythonExtension.compile_model(request).unwrap()
    else {
        panic!("dependencies are unsupported")
    };
    assert_eq!(diagnostics[0].code.as_deref(), Some("PY001"));
}

#[test]
fn ion_evidence_is_refused_uniformly_across_native_and_wasm() {
    let mut request = generation(a_model("4.0.0"));
    request.model.evidence.push(ModelGuaranteeEvidence {
        guarantee: "urn:example:optional".into(),
        model_id: request.model.model_id.clone(),
        model_revision: request.model.revision.clone(),
        context_digest: request.context_digest.clone(),
        scope: format!("model:{}", request.model.model_id),
        producer: "fixture".into(),
        evidence: ModelPayload::from_bytes(ModelCodec::IonBinary, &[0xe0, 1, 0, 0xea, 0x21, 1])
            .unwrap(),
    });
    let error = PythonExtension.generate_model(request).unwrap_err();
    assert!(error.to_string().contains("JSON-only"), "{error}");
}

#[test]
fn unsupported_distribution_forms_are_explicit_language_refusals() {
    for distribution in [
        json!({"Specs":{"packageName":"acme","dependencies":{},"spec":{"modules":{}}}}),
        json!({"Application":{"packageName":"acme","dependencies":{},"def":{"modules":{}},"entryPoints":{}}}),
    ] {
        let ir = json!({"formatVersion":4,"distribution":distribution});
        // Prove these are complete valid IR, rather than malformed enum inputs.
        serde_json::from_value::<morphir_core::ir::v4::IRFile>(ir.clone()).unwrap();
        let mut request = generation(a_model("4.0.0"));
        request.model.payload =
            ModelPayload::from_bytes(ModelCodec::MorphirJson, &serde_json::to_vec(&ir).unwrap())
                .unwrap();
        let result = PythonExtension.generate_model(request).unwrap();
        assert!(!result.success);
        assert!(result.artifacts.is_empty());
        assert_eq!(result.diagnostics[0].code.as_deref(), Some("PY004"));
        assert!(result.diagnostics[0].message.contains("Only Library"));
    }
}

#[test]
fn semantic_versions_and_payload_resource_limits_are_checked_before_generation() {
    let payloads = [
        (
            br#"{"formatVersion":3,"distribution":{}}"#.to_vec(),
            "unsupported_ir_version",
        ),
        (
            format!("{}0{}", "[".repeat(128), "]".repeat(128)).into_bytes(),
            "depth_limit",
        ),
        (vec![b' '; 8 * 1024 * 1024 + 1], "decoded_limit"),
    ];
    for (bytes, reason) in payloads {
        let mut request = generation(a_model("4.0.0"));
        request.model.payload = ModelPayload::from_bytes(ModelCodec::MorphirJson, &bytes).unwrap();
        let error = PythonExtension.generate_model(request).unwrap_err();
        assert!(error.to_string().contains(reason), "{reason}: {error}");
    }
    let mut request = generation(a_model("4.0.0"));
    request.model.payload.content = "A".repeat(12 * 1024 * 1024 + 4);
    let error = PythonExtension.generate_model(request).unwrap_err();
    assert!(error.to_string().contains("encoded_limit"), "{error}");
}
