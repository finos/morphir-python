//! Stream boundaries, byte lengths and resource bounds are transport contracts.
use morphir_python_extension::framing::{
    MAX_BODY_BYTES, MAX_HEADER_BYTES, read_frame, write_frame,
};
use std::io::{BufReader, Cursor};

#[test]
fn unicode_messages_and_adjacent_frames_survive_partial_reads() {
    let mut wire = Vec::new();
    for text in [r#"{"id":"λ"}"#, r#"{"id":2}"#] {
        write_frame(&mut wire, text.as_bytes()).unwrap();
    }
    let mut input = BufReader::with_capacity(1, Cursor::new(wire));
    assert_eq!(
        read_frame(&mut input).unwrap().unwrap(),
        r#"{"id":"λ"}"#.as_bytes()
    );
    assert_eq!(
        read_frame(&mut input).unwrap().unwrap(),
        r#"{"id":2}"#.as_bytes()
    );
    assert_eq!(read_frame(&mut input).unwrap(), None);
}

#[test]
fn malformed_or_truncated_input_is_refused() {
    for wire in [
        b"Content-Length: 2\r\nContent-Length: 2\r\n\r\n{}".as_slice(),
        b"Content-Length: -1\r\n\r\n",
        b"Content-Length: +2\r\n\r\n{}",
        b"Content-Length: 184467440737095516160\r\n\r\n",
        b"Other: value\r\n\r\n{}",
        b"Content-Length: 2\r\n",
        b"Content-Length: 2\r\n\r\n{",
        b"Content-Length: 1\r\n\r\n\xff",
        b"Content-Length: 2\r\nOther: invalid\nline\r\n\r\n{}",
        b"Content-Length: 2\r\nBad Name: value\r\n\r\n{}",
    ] {
        assert!(
            read_frame(&mut Cursor::new(wire)).is_err(),
            "accepted {wire:?}"
        );
    }
}

#[test]
fn bounds_are_applied_before_reading_an_advertised_body() {
    let huge = format!("Content-Length: {}\r\n\r\n", MAX_BODY_BYTES + 1);
    assert!(read_frame(&mut Cursor::new(huge)).is_err());
    let huge_header = vec![b'x'; MAX_HEADER_BYTES + 1];
    assert!(read_frame(&mut Cursor::new(huge_header)).is_err());
    assert!(write_frame(&mut Vec::new(), &vec![b'x'; MAX_BODY_BYTES + 1]).is_err());
}

#[test]
fn content_length_is_case_insensitive_and_uses_bytes() {
    let mut input = Cursor::new(b"content-length: 2\r\nContent-Type: application/json\r\n\r\n{}");
    assert_eq!(read_frame(&mut input).unwrap().unwrap(), b"{}");
    let mut wire = Vec::new();
    write_frame(&mut wire, "λ".as_bytes()).unwrap();
    assert_eq!(wire, "Content-Length: 2\r\n\r\nλ".as_bytes());
}

#[test]
fn a_complete_header_at_the_limit_is_accepted() {
    let prefix = "Content-Length: 2\r\nOther: ";
    let suffix = "\r\n\r\n";
    let header = format!(
        "{prefix}{}{suffix}",
        "x".repeat(MAX_HEADER_BYTES - prefix.len() - suffix.len())
    );
    assert_eq!(header.len(), MAX_HEADER_BYTES);
    let mut input = Cursor::new(format!("{header}{{}}"));
    assert_eq!(read_frame(&mut input).unwrap().unwrap(), b"{}");
}
