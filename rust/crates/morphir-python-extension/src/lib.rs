//! Bounded stdio transport for the Morphir Python process guest.
pub mod framing;
mod server;
pub use server::serve;
