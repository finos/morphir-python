//! A real process and in-memory streams share the same SDK lifecycle.
use morphir_python_extension::{
    framing::{read_frame, write_frame},
    serve,
};
use serde_json::{Value, json};
use std::io::{Cursor, Write};
use std::process::{Command, Stdio};

fn wire(messages: &[Value]) -> Vec<u8> {
    let mut bytes = Vec::new();
    for message in messages {
        write_frame(&mut bytes, &serde_json::to_vec(message).unwrap()).unwrap();
    }
    bytes
}
fn responses(bytes: Vec<u8>) -> Vec<Value> {
    let mut input = Cursor::new(bytes);
    let mut responses = Vec::new();
    while let Some(body) = read_frame(&mut input).unwrap() {
        responses.push(serde_json::from_slice(&body).unwrap());
    }
    responses
}
fn initialize() -> Value {
    json!({"jsonrpc":"2.0","id":1,"method":"morphir.initialize","params":{"protocolVersions":["0.1"],"host":{"name":"test","version":"1"}}})
}

#[test]
fn sessions_preserve_lifecycle_ids_and_notification_silence() {
    let messages = [
        json!({"jsonrpc":"2.0","id":0,"method":"morphir.extension.info","params":{}}),
        initialize(),
        json!({"jsonrpc":"2.0","method":"morphir.initialized"}),
        json!({"jsonrpc":"2.0","method":"unknown.notification","params":{"text":"λ"}}),
        json!({"jsonrpc":"2.0","id":2,"method":"morphir.ping","params":{}}),
        json!({"jsonrpc":"2.0","id":3,"method":"morphir.shutdown","params":{}}),
        json!({"jsonrpc":"2.0","id":4,"method":"morphir.extension.info","params":{}}),
        json!({"jsonrpc":"2.0","method":"morphir.exit"}),
        json!({"jsonrpc":"2.0","id":5,"method":"morphir.ping","params":{}}),
    ];
    let mut output = Vec::new();
    serve(&mut Cursor::new(wire(&messages)), &mut output).unwrap();
    let replies = responses(output);
    assert_eq!(replies.len(), 5);
    assert_eq!(
        replies
            .iter()
            .map(|value| value["id"].as_u64().unwrap())
            .collect::<Vec<_>>(),
        [0, 1, 2, 3, 4]
    );
    assert_eq!(replies[0]["error"]["code"], -32014);
    assert_eq!(replies[1]["result"]["protocolVersion"], "0.1");
    assert_eq!(replies[2]["result"]["ok"], true);
    assert_eq!(replies[4]["error"]["code"], -32014);
}

#[test]
fn invalid_json_is_refused_and_the_next_framed_request_can_recover() {
    let mut input = Vec::new();
    write_frame(&mut input, b"{invalid").unwrap();
    input.extend(wire(&[
        json!({"jsonrpc":"2.0","id":7,"method":"morphir.ping","params":{}}),
    ]));
    let mut output = Vec::new();
    serve(&mut Cursor::new(input), &mut output).unwrap();
    let replies = responses(output);
    assert_eq!(replies.len(), 2);
    assert_eq!(replies[0]["error"]["code"], -32700);
    assert_eq!(replies[0]["id"], Value::Null);
    assert_eq!(replies[1]["id"], 7);
}

#[test]
fn malformed_frames_fail_without_writing_non_protocol_output() {
    let mut output = Vec::new();
    assert!(
        serve(
            &mut Cursor::new(b"Content-Length: 999999999\r\n\r\n"),
            &mut output
        )
        .is_err()
    );
    assert!(output.is_empty());
}

#[test]
fn standalone_process_needs_no_python_or_rust_environment() {
    standalone(&["--stdio"]);
    standalone(&[]);
}

fn standalone(arguments: &[&str]) {
    let mut child = Command::new(env!("CARGO_BIN_EXE_morphir-python-extension"))
        .args(arguments)
        .env_clear()
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let input = wire(&[
        initialize(),
        json!({"jsonrpc":"2.0","method":"morphir.exit"}),
    ]);
    child.stdin.take().unwrap().write_all(&input).unwrap();
    let result = child.wait_with_output().unwrap();
    assert!(result.status.success(), "{:?}", result.stderr);
    assert!(result.stderr.is_empty());
    let replies = responses(result.stdout);
    assert_eq!(replies.len(), 1);
    assert_eq!(replies[0]["result"]["extension"]["id"], "morphir-python");
}

#[test]
fn invalid_request_ids_do_not_become_notifications_or_poison_the_session() {
    let mut messages = Vec::new();
    for id in [
        Value::Null,
        json!(true),
        json!([]),
        json!({}),
        json!(-1),
        json!(1.5),
    ] {
        messages.push(json!({"jsonrpc":"2.0","id":id,"method":"morphir.ping","params":{}}));
    }
    messages.push(json!({"jsonrpc":"2.0","id":77,"method":"morphir.ping","params":{}}));
    let mut output = Vec::new();
    serve(&mut Cursor::new(wire(&messages)), &mut output).unwrap();
    let replies = responses(output);
    assert_eq!(replies.len(), 7);
    for reply in &replies[..6] {
        assert_eq!(reply["id"], Value::Null);
        assert_eq!(reply["error"]["code"], -32600);
    }
    assert_eq!(replies[6]["id"], 77);
    assert_eq!(replies[6]["result"]["ok"], true);
}

#[test]
fn independent_stream_sessions_cannot_share_initialization_state() {
    let mut first = Vec::new();
    serve(&mut Cursor::new(wire(&[initialize()])), &mut first).unwrap();
    assert_eq!(responses(first)[0]["result"]["protocolVersion"], "0.1");
    let mut second = Vec::new();
    serve(
        &mut Cursor::new(wire(&[
            json!({"jsonrpc":"2.0","id":2,"method":"morphir.extension.info","params":{}}),
        ])),
        &mut second,
    )
    .unwrap();
    assert_eq!(responses(second)[0]["error"]["code"], -32014);
}

#[test]
fn canonical_numeric_and_string_ids_survive_requests_and_lifecycle() {
    let ids = [json!(u64::MAX), json!("λ/request"), json!(""), json!(0)];
    let mut messages = vec![initialize()];
    for id in &ids {
        messages.push(json!({"jsonrpc":"2.0","id":id,"method":"morphir.ping"}));
    }
    messages.extend([
        json!({"jsonrpc":"2.0","id":"shutdown","method":"morphir.shutdown","params":{}}),
        json!({"jsonrpc":"2.0","method":"morphir.exit"}),
    ]);
    let mut output = Vec::new();
    serve(&mut Cursor::new(wire(&messages)), &mut output).unwrap();
    let replies = responses(output);
    assert_eq!(replies.len(), 6);
    for (reply, id) in replies[1..5].iter().zip(ids) {
        assert_eq!(reply["id"], id);
        assert_eq!(reply["result"]["ok"], true);
    }
    assert_eq!(replies[5]["id"], "shutdown");
    assert!(replies[5].get("error").is_none());
}

#[test]
fn canonical_empty_parameter_requests_need_no_params_member() {
    let mut output = Vec::new();
    serve(
        &mut Cursor::new(wire(&[
            initialize(),
            json!({"jsonrpc":"2.0","id":2,"method":"morphir.ping"}),
            json!({"jsonrpc":"2.0","id":3,"method":"morphir.shutdown"}),
            json!({"jsonrpc":"2.0","method":"morphir.exit"}),
        ])),
        &mut output,
    )
    .unwrap();
    let replies = responses(output);
    assert_eq!(replies[1]["id"], 2);
    assert_eq!(replies[1]["result"]["ok"], true);
    assert_eq!(replies[2]["id"], 3);
    assert!(replies[2].get("error").is_none());
}

#[test]
fn truncated_input_exits_with_diagnostics_only_on_stderr() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_morphir-python-extension"))
        .env_clear()
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(b"Content-Length: 10\r\n\r\n{}")
        .unwrap();
    let result = child.wait_with_output().unwrap();
    assert_eq!(result.status.code(), Some(1));
    assert!(result.stdout.is_empty());
    assert!(
        String::from_utf8(result.stderr)
            .unwrap()
            .contains("morphir-python-extension:")
    );
}

#[test]
fn description_is_fixed_across_initialization_and_reinitialization_refusal() {
    let describe = |id| json!({"jsonrpc":"2.0","id":id,"method":"morphir.extension.describe","params":{"protocolVersions":["0.1"]}});
    let mut second_init = initialize();
    second_init["id"] = json!(3);
    second_init["params"]["protocolVersions"] = json!(["0.2.0-draft.99"]);
    let mut output = Vec::new();
    serve(
        &mut Cursor::new(wire(&[
            describe(0),
            initialize(),
            describe(2),
            second_init,
            describe(4),
        ])),
        &mut output,
    )
    .unwrap();
    let replies = responses(output);
    assert_eq!(replies.len(), 5);
    assert_eq!(
        replies[0]["result"]["protocolVersions"],
        json!(["0.2.0-draft.1", "0.1"])
    );
    assert_eq!(replies[0]["result"], replies[2]["result"]);
    assert_eq!(replies[2]["result"], replies[4]["result"]);
    assert_eq!(replies[3]["error"]["code"], -32600);
}
