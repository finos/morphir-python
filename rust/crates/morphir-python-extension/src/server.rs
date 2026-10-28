//! Framed stdio sessions around the SDK's native protocol endpoint.
use crate::framing::{MAX_BODY_BYTES, read_frame, write_frame};
use morphir_extension_sdk::{
    NativeExtension,
    protocol::{ExtensionRequest, error_codes, methods},
};
use morphir_python_binding::PythonExtension;
use serde::{Deserialize, Deserializer, Serialize};
use serde_json::value::RawValue;
use std::io::{self, BufRead, Write};

#[derive(Deserialize)]
struct MessageHead {
    jsonrpc: String,
    method: String,
    // Explicit null is a malformed request ID, not a notification.
    #[serde(default, deserialize_with = "present_id")]
    id: Option<Box<RawValue>>,
}

fn present_id<'de, D: Deserializer<'de>>(reader: D) -> Result<Option<Box<RawValue>>, D::Error> {
    Box::<RawValue>::deserialize(reader).map(Some)
}

fn write_error(writer: &mut impl Write, code: i32, message: &str) -> io::Result<()> {
    write_response(
        writer,
        &serde_json::json!({
            "jsonrpc": "2.0", "id": null, "error": { "code": code, "message": message },
        }),
    )
}

fn write_response(writer: &mut impl Write, value: &impl Serialize) -> io::Result<()> {
    struct Body(Vec<u8>);
    impl Write for Body {
        fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
            if self.0.len().saturating_add(bytes.len()) > MAX_BODY_BYTES {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    "MEP response exceeds 16 MiB",
                ));
            }
            self.0.extend_from_slice(bytes);
            Ok(bytes.len())
        }
        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }
    let mut body = Body(Vec::new());
    serde_json::to_writer(&mut body, value).map_err(io::Error::other)?;
    write_frame(writer, &body.0)
}

/// Serve a fresh SDK session, with protocol frames as the only output.
///
/// Invalid JSON or request envelopes receive JSON-RPC errors without entering
/// the compiler. A damaged frame is fatal because its next boundary is unknown.
/// Notifications receive no response; exit stops processing further messages.
/// Every invocation owns an independent native SDK session.
pub fn serve(reader: &mut impl BufRead, writer: &mut impl Write) -> io::Result<()> {
    let extension = NativeExtension::frontend_backend(PythonExtension)
        .map_err(|error| io::Error::other(error.to_string()))?;
    let session = extension.open_protocol();
    while let Some(body) = read_frame(reader)? {
        // Borrow the raw document to validate syntax without materializing
        // opaque parameters or giving serde-private-looking keys meaning.
        if serde_json::from_slice::<&RawValue>(&body).is_err() {
            write_error(writer, error_codes::PARSE_ERROR, "Invalid JSON")?;
            continue;
        }
        let head = match serde_json::from_slice::<MessageHead>(&body) {
            Ok(head) if head.jsonrpc == "2.0" => head,
            _ => {
                write_error(
                    writer,
                    error_codes::INVALID_REQUEST,
                    "Invalid JSON-RPC request",
                )?;
                continue;
            }
        };
        if head.id.is_none() {
            if head.method == methods::EXIT {
                break;
            }
            // Initialized acknowledges a handshake already held by the SDK.
            // Unknown or unadvertised notifications do no work.
            continue;
        }
        let request = match serde_json::from_slice::<ExtensionRequest>(&body) {
            Ok(request) => request,
            Err(_) => {
                write_error(writer, error_codes::INVALID_REQUEST, "Invalid MEP request")?;
                continue;
            }
        };
        write_response(writer, &session.handle(request))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn oversized_response_is_refused_before_any_frame_is_emitted() {
        let mut output = Vec::new();
        let value = "x".repeat(MAX_BODY_BYTES);
        assert!(write_response(&mut output, &value).is_err());
        assert!(output.is_empty());
    }
}
