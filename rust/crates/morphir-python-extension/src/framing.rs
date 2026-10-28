//! Bounded Content-Length framing for UTF-8 MEP messages.
//!
//! Framing preserves message bytes. The session layer validates JSON and MEP.
//!
//! ```
//! use morphir_python_extension::framing::{read_frame, write_frame};
//! let mut wire = Vec::new();
//! write_frame(&mut wire, br#"{"jsonrpc":"2.0","id":1}"#).unwrap();
//! assert!(read_frame(&mut std::io::Cursor::new(wire)).unwrap().is_some());
//! ```
use std::io::{self, BufRead, Write};

/// Maximum header size, including the terminating CRLF pair.
pub const MAX_HEADER_BYTES: usize = 8 * 1024;
/// Maximum complete UTF-8 JSON body, including model-envelope overhead.
pub const MAX_BODY_BYTES: usize = 16 * 1024 * 1024;

fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message)
}

/// Read one bounded frame, or return `None` for EOF between messages.
///
/// Duplicate or invalid lengths, non-ASCII headers, truncation and invalid
/// UTF-8 bodies are refused. Body limits are checked before allocation.
pub fn read_frame(reader: &mut impl BufRead) -> io::Result<Option<Vec<u8>>> {
    let mut header = Vec::with_capacity(128);
    loop {
        let mut byte = [0];
        match reader.read_exact(&mut byte) {
            Ok(()) => {}
            Err(error) if error.kind() == io::ErrorKind::UnexpectedEof && header.is_empty() => {
                return Ok(None);
            }
            Err(error) => return Err(error),
        }
        if header.len() == MAX_HEADER_BYTES {
            return Err(invalid("MEP header exceeds 8 KiB"));
        }
        header.push(byte[0]);
        if header.ends_with(b"\r\n\r\n") {
            break;
        }
    }
    if !header.is_ascii() {
        return Err(invalid("MEP headers must be ASCII"));
    }
    let text = std::str::from_utf8(&header).map_err(|_| invalid("Invalid MEP header"))?;
    let mut length = None;
    for line in text[..text.len() - 4].split("\r\n") {
        if line
            .bytes()
            .any(|byte| byte.is_ascii_control() && byte != b'\t')
        {
            return Err(invalid("Invalid control character in MEP header"));
        }
        let (name, value) = line
            .split_once(':')
            .ok_or_else(|| invalid("Malformed MEP header"))?;
        if name.is_empty()
            || !name
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || b"!#$%&'*+-.^_`|~".contains(&byte))
        {
            return Err(invalid("Invalid MEP header name"));
        }
        if name.eq_ignore_ascii_case("Content-Length") {
            if length.is_some() {
                return Err(invalid("Duplicate Content-Length"));
            }
            let value = value.trim();
            if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
                return Err(invalid("Content-Length must contain decimal digits"));
            }
            let size = value
                .parse::<usize>()
                .map_err(|_| invalid("Content-Length overflows the platform size"))?;
            if size > MAX_BODY_BYTES {
                return Err(invalid("MEP body exceeds 16 MiB"));
            }
            length = Some(size);
        }
    }
    let length = length.ok_or_else(|| invalid("Missing Content-Length"))?;
    let mut body = vec![0; length];
    reader.read_exact(&mut body)?;
    std::str::from_utf8(&body).map_err(|_| invalid("MEP body must be UTF-8"))?;
    Ok(Some(body))
}

/// Write and flush one bounded UTF-8 frame, using byte length rather than characters.
pub fn write_frame(writer: &mut impl Write, body: &[u8]) -> io::Result<()> {
    if body.len() > MAX_BODY_BYTES {
        return Err(invalid("MEP response exceeds 16 MiB"));
    }
    std::str::from_utf8(body).map_err(|_| invalid("MEP response must be UTF-8"))?;
    write!(writer, "Content-Length: {}\r\n\r\n", body.len())?;
    writer.write_all(body)?;
    writer.flush()
}
