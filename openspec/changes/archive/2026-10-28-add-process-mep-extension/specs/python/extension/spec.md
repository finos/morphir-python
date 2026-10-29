# Spec Delta

## MODIFIED Requirements

### Requirement: MEP behavior remains compatible
The extension SHALL retain identity `morphir-python`, Python language/target identifiers, initialization and capability negotiation, legacy compile/generate methods and advertised IR v3/v4 support. Native Rust, Python, packaged WASM and process invocations SHALL agree on supported model semantics and language diagnostic codes. New model methods MUST require their negotiated draft and admitted capabilities. (bead: morphir-5hxy)

#### Scenario: Existing host installs the replacement bundle
- **WHEN** a compatible Morphir host installs the bundle built from morphir-python
- **THEN** initialization, capability discovery, Python compilation and Python generation succeed through the existing protocol

#### Scenario: Users select different supported runtimes
- **WHEN** qualified WASM and process guests handle equivalent supported compilation or generation requests
- **THEN** they agree on compiler identity, supported semantics, deterministic artifacts and language diagnostic codes

## ADDED Requirements

### Requirement: A native process guest serves framed MEP sessions
A released native process guest SHALL serve JSON-RPC MEP over Content-Length-framed stdin/stdout without CPython or Rust installed by the user. It MUST enforce documented header/body bounds, UTF-8 byte lengths, request identity and the SDK lifecycle. Stdout MUST contain only protocol frames; notifications MUST NOT receive responses. (bead: morphir-5hxy)

#### Scenario: Multiple operations in one process
- **WHEN** a host initializes the guest, performs supported operations, requests shutdown and sends exit
- **THEN** responses retain request IDs, session capabilities remain fixed, and the process exits cleanly

#### Scenario: Numeric and string request identity
- **WHEN** a supported request uses either a numeric or string JSON-RPC ID
- **THEN** its response preserves that exact ID type and value in both runtime routes

#### Scenario: Malformed or oversized frame
- **WHEN** a frame has conflicting lengths, truncated data, invalid JSON, invalid UTF-8 or exceeds a declared bound
- **THEN** the guest refuses it without unbounded allocation or logging non-protocol text to stdout

#### Scenario: Operation outside its lifecycle
- **WHEN** an operation is requested before initialization or after shutdown
- **THEN** the guest applies the protocol lifecycle refusal and does not invoke the compiler

### Requirement: Both runtime choices have qualified release artifacts
Extension releases SHALL retain portable WASM and provide qualified process artifacts for each advertised process platform. Descriptors MUST bind runtime, platform, arguments, executable mode, digest, protocol versions and capability claims to the selected bytes. Unsupported runtime/platform combinations MUST fail explicitly. (bead: morphir-5hxy)

#### Scenario: Process artifact is selected offline
- **WHEN** a compatible host selects a qualified installed process artifact
- **THEN** it verifies and launches the locked executable and arguments without obtaining Python, Rust or another artifact from the network

#### Scenario: Existing user continues with WASM
- **WHEN** a compatible host selects the retained WASM runtime
- **THEN** the extension remains portable and its operations preserve the qualified compiler behavior

### Requirement: Host support claims follow actual qualification
Each documented successful host route SHALL have retained candidate-bound installation, lifecycle and operation evidence for the stated host revision and runtime. Unqualified or incompatible Rust or MoonBit routes MUST be labeled unsupported with their observed limitations. A transport wrapper alone MUST NOT establish model-envelope support. (bead: morphir-5hxy)

#### Scenario: A host requires unavailable model behavior
- **WHEN** a host route requires a profile or model operation that the selected guest cannot admit
- **THEN** documentation records that route as unsupported rather than claiming that process transport resolves the incompatibility
