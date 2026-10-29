//! Thin Extism/stdio adapter for the shared executable MCK.
//! No expectations or conformance decisions live here; raw request/response
//! bodies pass through the actual guest's exported `handle` function.
use anyhow::{Context, Result, ensure};
use morphir_host_native::extism::{ExtensionContainer, MorphirHostFunctions};
use serde::{Deserialize, Deserializer};
use serde_json::value::RawValue;
use std::{
    fs,
    io::{BufRead, Write},
    path::PathBuf,
};

const MAX_HEADER: usize = 8192;
const MAX_BODY: usize = 16 * 1024 * 1024;

#[derive(Deserialize)]
struct Head {
    method: String,
    #[serde(default, deserialize_with = "present_id")]
    id: Option<Box<RawValue>>,
}

fn present_id<'de, D: Deserializer<'de>>(input: D) -> Result<Option<Box<RawValue>>, D::Error> {
    Box::<RawValue>::deserialize(input).map(Some)
}

fn read_frame(input: &mut impl BufRead) -> Result<Option<Vec<u8>>> {
    let mut header = Vec::new();
    loop {
        let available = input.fill_buf()?;
        if available.is_empty() {
            ensure!(header.is_empty(), "truncated MCK adapter header");
            return Ok(None);
        }
        let byte = available[0];
        input.consume(1);
        header.push(byte);
        ensure!(header.len() <= MAX_HEADER, "MCK adapter header exceeds8KiB");
        if header.ends_with(b"\r\n\r\n") {
            break;
        }
    }
    let mut length = None;
    for line in std::str::from_utf8(&header)?.trim_end().split("\r\n") {
        let (name, value) = line.split_once(':').context("invalid MCK adapter header")?;
        if name.eq_ignore_ascii_case("content-length") {
            ensure!(length.is_none(), "duplicate Content-Length");
            let value = value.trim();
            ensure!(!value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit()));
            let size: usize = value.parse()?;
            ensure!(size <= MAX_BODY, "MCK adapter body exceeds16MiB");
            length = Some(size);
        }
    }
    let mut body = vec![0; length.context("missing Content-Length")?];
    input.read_exact(&mut body)?;
    Ok(Some(body))
}

#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<()> {
    let mut args = std::env::args_os().skip(1);
    let wasm = args
        .next()
        .map(PathBuf::from)
        .context("usage: mep_wasm_host GUEST.wasm")?;
    ensure!(args.next().is_none(), "unexpected adapter argument");
    // Use the same pinned concrete host container as interoperability checks.
    // Notifications have no Extism request ABI, matching ExtismChannel policy.
    let container = ExtensionContainer::from_bytes(
        "morphir-python",
        &fs::read(wasm)?,
        MorphirHostFunctions::default(),
    )?;
    let mut input = std::io::stdin().lock();
    let mut output = std::io::stdout().lock();
    while let Some(body) = read_frame(&mut input)? {
        let head: Head = serde_json::from_slice(&body)?;
        if head.id.is_none() {
            if head.method == "morphir.exit" {
                break;
            }
            continue;
        }
        let response = container.call_raw("handle", &body).await?;
        ensure!(response.len() <= MAX_BODY, "guest response exceeds16MiB");
        write!(output, "Content-Length: {}\r\n\r\n", response.len())?;
        output.write_all(&response)?;
        output.flush()?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    #[test]
    fn unicode_body_uses_byte_lengths_and_concatenated_frames_keep_boundaries() {
        let body = "λ".as_bytes();
        let mut bytes = format!("Content-Length: {}\r\n\r\n", body.len()).into_bytes();
        bytes.extend(body);
        bytes.extend(b"Content-Length: 2\r\n\r\n{}");
        let mut input = Cursor::new(bytes);
        assert_eq!(read_frame(&mut input).unwrap().unwrap(), body);
        assert_eq!(read_frame(&mut input).unwrap().unwrap(), b"{}");
        assert!(read_frame(&mut input).unwrap().is_none());
    }

    #[test]
    fn invalid_truncated_duplicate_and_unbounded_frames_are_refused() {
        for bytes in [
            b"Content-Length: 2\r\n\r\n{".as_slice(),
            b"Content-Length: 2\r\nContent-Length: 2\r\n\r\n{}",
            b"Content-Length: -1\r\n\r\n",
            b"Content-Length: 999999999999999999999999\r\n\r\n",
            b"Content-Length: 16777217\r\n\r\n",
            b"Content-Length: 2\r\n",
        ] {
            assert!(read_frame(&mut Cursor::new(bytes)).is_err());
        }
        assert!(read_frame(&mut Cursor::new(vec![b'x'; MAX_HEADER + 1])).is_err());
    }
}
