//! Independent source-pinned Rust host qualification of actual guest bytes.
//! This verifies legacy interoperability; it is not the canonical MCK guest kit.
use anyhow::{Context, Result, bail, ensure};
use async_trait::async_trait;
use morphir_extension_sdk::{
    CompileOptions, CompilePackage, CompileRequest, GenerateRequest, SourceDocument, SourceSet,
    protocol::{ExtensionResponse, PeerInfo},
};
use morphir_host::{
    Channel, ChannelError, ChannelState, ExpectedChecks, ExpectedExtension, HostConfig,
    JsonRpcConnection, Outgoing, Session,
};
use morphir_host_native::{
    CheckedConnection,
    extism::{ExtensionContainer, ExtismChannel, MorphirHostFunctions},
    process::{ProcessChannel, ProcessLaunch},
};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs,
    io::Read,
    path::{Path, PathBuf},
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::sync::Mutex;

const HOST_SOURCE: &str = "d51daa8aea7ae09ae295ff254d72b27770c64104";
const ID: &str = "morphir-python";
const TYPES_SOURCE: &str =
    "from dataclasses import dataclass\n@dataclass(frozen=True)\nclass Box:\n    value: int\n";
const FUNCTION_SOURCE: &str = "\ndef choose(flag: bool, first: int, second: int) -> int:\n    return first if flag else second\n";

#[derive(Clone)]
struct SharedProcess(Arc<Mutex<ProcessChannel>>);

#[async_trait]
impl Channel for SharedProcess {
    async fn send(&mut self, message: Outgoing) -> Result<(), ChannelError> {
        self.0.lock().await.send(message).await
    }
    async fn receive(&mut self) -> Result<ExtensionResponse, ChannelError> {
        self.0.lock().await.receive().await
    }
    async fn close(&mut self) -> Result<ChannelState, ChannelError> {
        self.0.lock().await.close().await
    }
    async fn abort(&mut self) -> Result<ChannelState, ChannelError> {
        self.0.lock().await.abort().await
    }
}

fn host_config() -> HostConfig {
    HostConfig::new(PeerInfo {
        name: "morphir-python-qualification".into(),
        version: env!("CARGO_PKG_VERSION").into(),
        kind: Default::default(),
    })
}

fn request(version: &str, types_only: bool) -> CompileRequest {
    CompileRequest {
        language_id: "python".into(),
        sources: SourceSet {
            root: None,
            documents: vec![SourceDocument {
                uri: "models.py".into(),
                language_id: "python".into(),
                version: 1,
                text: if types_only {
                    TYPES_SOURCE.into()
                } else {
                    format!("{TYPES_SOURCE}{FUNCTION_SOURCE}")
                },
            }],
        },
        package: CompilePackage {
            name: "acme".into(),
            exposed_modules: None,
        },
        dependencies: vec![],
        options: CompileOptions {
            ir_version: version.into(),
            types_only,
            ..Default::default()
        },
        baseline: None,
    }
}

fn hash_file(path: &Path) -> Result<String> {
    let mut file = fs::File::open(path)?;
    let mut digest = Sha256::new();
    let mut buffer = [0_u8; 65536];
    loop {
        let size = file.read(&mut buffer)?;
        if size == 0 {
            break;
        }
        digest.update(&buffer[..size]);
    }
    Ok(hex::encode(digest.finalize()))
}

fn canonical_digest(value: &Value) -> Result<String> {
    let mut canonical = value.clone();
    canonical.sort_all_objects();
    Ok(hex::encode(Sha256::digest(serde_json::to_vec(&canonical)?)))
}

async fn process_session(
    executable: &Path,
    cwd: &Path,
    timeout: Duration,
) -> Result<(Session, SharedProcess)> {
    // ProcessLaunch inherits no user environment. No Python or Rust launcher.
    let launch = ProcessLaunch::new(ID, executable, cwd).request_timeout(timeout);
    let channel = ProcessChannel::spawn(launch).await?;
    let expected = channel.expectation();
    let shared = SharedProcess(Arc::new(Mutex::new(channel)));
    let connection = CheckedConnection::new(JsonRpcConnection::new(
        shared.clone(),
        ExpectedChecks::new(expected),
    ));
    let session = Session::open(connection, &host_config()).await?;
    Ok((session, shared))
}

async fn qualify_runtime(
    wasm: &Path,
    process: &Path,
    runtime: &str,
    types_source: &str,
    values_source: &str,
) -> Result<Value> {
    let work = tempfile::tempdir()?;
    let started = Instant::now();
    let (mut session, child) = if runtime == "process" {
        let (session, child) =
            process_session(process, work.path(), Duration::from_secs(30)).await?;
        (session, Some(child))
    } else {
        let bytes = fs::read(wasm)?;
        let container =
            ExtensionContainer::from_bytes(ID, &bytes, MorphirHostFunctions::default())?;
        let channel = ExtismChannel::new(container, ExpectedExtension::identified(ID));
        let expected = channel.expectation();
        let connection = CheckedConnection::new(JsonRpcConnection::new(
            channel,
            ExpectedChecks::new(expected),
        ));
        (Session::open(connection, &host_config()).await?, None)
    };
    let startup_ns = started.elapsed().as_nanos();
    ensure!(session.negotiated().protocol_version() == "0.1");
    let mut operations = Vec::new();
    for version in ["3", "4"] {
        for types_only in [true, false] {
            let compile_start = Instant::now();
            let mut input = request(version, types_only);
            input.sources.documents[0].text = if types_only {
                types_source.into()
            } else {
                values_source.into()
            };
            let compiled = session.compile(input).await?;
            let compile_ns = compile_start.elapsed().as_nanos();
            ensure!(compiled.success, "compile: {:?}", compiled.diagnostics);
            let ir = compiled.ir.context("successful compile has IR")?;
            let generate_start = Instant::now();
            let generated = session
                .generate(GenerateRequest {
                    ir: ir.clone(),
                    target: "python".into(),
                    options: Default::default(),
                })
                .await?;
            let generate_ns = generate_start.elapsed().as_nanos();
            ensure!(generated.success, "generate: {:?}", generated.diagnostics);
            let mut recompile = request(version, types_only);
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
            let again = session.compile(recompile).await?;
            ensure!(
                again.success && again.ir.as_ref() == Some(&ir),
                "generated source changed IR"
            );
            let mut invalid = request(version, types_only);
            invalid.sources.documents[0].text = "import os\n".into();
            let refused = session.compile(invalid).await?;
            ensure!(!refused.success && refused.ir.is_none() && !refused.diagnostics.is_empty());
            operations.push(json!({
                "irVersion":version, "typesOnly":types_only,
                "irSha256":canonical_digest(&ir)?,
                "artifacts":generated.artifacts, "diagnostics":refused.diagnostics,
                "compileNs":compile_ns, "generateNs":generate_ns,
            }));
        }
    }
    session.close().await?;
    if let Some(child) = child {
        let mut channel = child.0.lock().await;
        ensure!(!channel.is_running()?, "closed guest is still running");
        ensure!(
            channel.stdout_is_exhausted().await?,
            "stdout contains unread bytes"
        );
        ensure!(
            channel.stderr_output().is_empty(),
            "unexpected guest diagnostics"
        );
    }
    Ok(
        json!({"runtime":runtime,"protocolVersion":"0.1","startupNs":startup_ns,"operations":operations,"orderlyClose":true}),
    )
}

async fn timeout_cleanup(process: &Path) -> Result<Value> {
    let work = tempfile::tempdir()?;
    let channel = ProcessChannel::spawn(
        ProcessLaunch::new(ID, process, work.path()).request_timeout(Duration::from_millis(1)),
    )
    .await?;
    let expected = channel.expectation();
    let shared = SharedProcess(Arc::new(Mutex::new(channel)));
    let connection = CheckedConnection::new(JsonRpcConnection::new(
        shared.clone(),
        ExpectedChecks::new(expected),
    ));
    let (phase, reason) = match Session::open(connection, &host_config()).await {
        Err(error) => ("initialize", error.to_string()),
        Ok(mut session) => {
            let mut large = request("4", true);
            let mut source = "from dataclasses import dataclass\n".to_owned();
            for index in 0..20000 {
                source.push_str(&format!(
                    "@dataclass(frozen=True)\nclass Item{index}:\n    value: int\n"
                ));
            }
            large.sources.documents[0].text = source;
            let error = session
                .compile(large)
                .await
                .expect_err("large request should exceed 1ms deadline");
            ("compile", error.to_string())
        }
    };
    ensure!(
        reason.contains("timed out") || reason.contains("timeout"),
        "{reason}"
    );
    ensure!(
        !shared.0.lock().await.is_running()?,
        "timed-out child was not reaped"
    );
    Ok(json!({"deadlineMs":1,"phase":phase,"error":reason,"childRunning":false}))
}

fn equivalent(first: &Value, second: &Value) -> bool {
    let mut first = first.clone();
    let mut second = second.clone();
    for value in [&mut first, &mut second] {
        for entry in value.as_array_mut().unwrap() {
            entry.as_object_mut().unwrap().remove("compileNs");
            entry.as_object_mut().unwrap().remove("generateNs");
        }
    }
    first == second
}

#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<()> {
    let mut arguments = std::env::args_os().skip(1);
    let wasm = arguments
        .next()
        .map(PathBuf::from)
        .context("usage: qualifier WASM PROCESS REPORT [TYPES_SOURCE VALUES_SOURCE]")?;
    let process = arguments
        .next()
        .map(PathBuf::from)
        .context("missing process executable")?
        .canonicalize()?;
    let report = arguments
        .next()
        .map(PathBuf::from)
        .context("missing report path")?;
    let sources = if let Some(types_path) = arguments.next() {
        let values_path = arguments.next().context("missing values source path")?;
        (
            fs::read_to_string(types_path)?,
            fs::read_to_string(values_path)?,
        )
    } else {
        (
            TYPES_SOURCE.into(),
            format!("{TYPES_SOURCE}{FUNCTION_SOURCE}"),
        )
    };
    if arguments.next().is_some() {
        bail!("unexpected arguments");
    }
    let wasm = wasm.canonicalize()?;
    let owned = tempfile::tempdir()?;
    let wasm_copy = owned.path().join("guest.wasm");
    let process_copy = owned
        .path()
        .join(process.file_name().context("missing process filename")?);
    fs::copy(&wasm, &wasm_copy)?;
    fs::copy(&process, &process_copy)?;
    ensure!(hash_file(&wasm)? == hash_file(&wasm_copy)?);
    ensure!(hash_file(&process)? == hash_file(&process_copy)?);
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&process_copy, fs::Permissions::from_mode(0o700))?;
    }
    let wasm = wasm_copy;
    let process = process_copy;
    let wasm_result = qualify_runtime(&wasm, &process, "wasm", &sources.0, &sources.1).await?;
    let process_result =
        qualify_runtime(&wasm, &process, "process", &sources.0, &sources.1).await?;
    ensure!(
        equivalent(&wasm_result["operations"], &process_result["operations"]),
        "runtime results or diagnostics differ"
    );
    let timeout = timeout_cleanup(&process).await?;
    let result = json!({
        "scope":"source-pinned-legacy-host-interoperability",
        "hostSource":HOST_SOURCE, "rustc":env!("QUALIFICATION_RUSTC"),
        "build":{
            "profile":env!("QUALIFICATION_PROFILE"),
            "optLevel":env!("QUALIFICATION_OPT_LEVEL"),
            "debug":env!("QUALIFICATION_DEBUG"),
        },
        "definitionInputs":{
            "Cargo.toml":hex::encode(Sha256::digest(include_bytes!("../Cargo.toml"))),
            "Cargo.lock":hex::encode(Sha256::digest(include_bytes!("../Cargo.lock"))),
            "build.rs":hex::encode(Sha256::digest(include_bytes!("../build.rs"))),
            "src/main.rs":hex::encode(Sha256::digest(include_bytes!("main.rs"))),
        },
        "checkerBinarySha256":hash_file(&std::env::current_exe()?)?,
        "wasmSha256":hash_file(&wasm)?, "processSha256":hash_file(&process)?,
        "inputs":{
            "typesOnlySha256":hex::encode(Sha256::digest(sources.0.as_bytes())),
            "typesAndValuesSha256":hex::encode(Sha256::digest(sources.1.as_bytes())),
        },
        "results":[wasm_result,process_result],"timeout":timeout,
    });
    if let Some(parent) = report.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&report, serde_json::to_vec_pretty(&result)?)?;
    println!(
        "host interoperability qualified; report {}",
        report.display()
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parity_ignores_observation_times_but_preserves_diagnostics_and_ir() {
        let first = json!([{"compileNs":1,"generateNs":2,"irSha256":"abc","diagnostics":[{"code":"PY004"}]}]);
        let second = json!([{"compileNs":3,"generateNs":4,"irSha256":"abc","diagnostics":[{"code":"PY004"}]}]);
        assert!(equivalent(&first, &second));
        let different_diagnostic = json!([{"compileNs":3,"generateNs":4,"irSha256":"abc","diagnostics":[{"code":"PY003"}]}]);
        assert!(!equivalent(&first, &different_diagnostic));
        let different_ir = json!([{"compileNs":3,"generateNs":4,"irSha256":"def","diagnostics":[{"code":"PY004"}]}]);
        assert!(!equivalent(&first, &different_ir));
    }
}
