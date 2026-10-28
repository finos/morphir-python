# Spec Delta

## Purpose

Expose the Python compiler through the current canonical MEP draft with explicit model transport negotiation, bounded envelopes and truthful supported-profile claims.

## ADDED Requirements

### Requirement: New model operations require exact draft negotiation
The extension SHALL support MEP `0.2.0-draft.1` for model operations while preserving legacy `0.1` behavior. Draft negotiation MUST match the full version exactly. A session negotiated as `0.1` MUST NOT enable model operations. Package, claims, model-envelope and IR versions MUST remain independent. (bead: morphir-5hxy)

#### Scenario: Host offers the supported new draft
- **WHEN** a host and extension both offer `0.2.0-draft.1`
- **THEN** initialization selects the exact draft before any model operation is admitted

#### Scenario: Legacy or different draft session
- **WHEN** the session selects `0.1` or the host offers only another draft version
- **THEN** model operations are unavailable and an incompatible-only handshake is refused

### Requirement: Model operation admission is bilateral
Each model operation SHALL require an initialized, advertised tuple matching operation, profile, codec, envelope version and semantic IR version. Session tuples and limits MUST remain within both peers' offers and permitted static claims. Unknown required guarantees and unadmitted tuples MUST be refused. (bead: morphir-5hxy)

#### Scenario: Compile support does not grant generation
- **WHEN** only a compile tuple was admitted and the host requests model generation
- **THEN** the operation is refused without invoking the generator

#### Scenario: Independent lists would produce an unsupported combination
- **WHEN** an operation combines otherwise known tuple members in a combination not admitted as a complete tuple
- **THEN** the extension refuses that combination rather than forming a Cartesian product

### Requirement: Model envelopes bind exact bounded bytes
Model payloads SHALL use the canonical `0.1.0-draft.1` envelope and validate codec, layout, canonical padded base64, decoded length, SHA-256, semantic IR version and required critical fields before compiler invocation. Advertised and local message/decoded limits MUST be enforced before unbounded allocation or decoding. (bead: morphir-5hxy)

#### Scenario: Payload length or digest disagrees
- **WHEN** an envelope's declared length or digest differs from its decoded bytes
- **THEN** admission fails without compiling or generating

#### Scenario: Oversized or unknown critical input
- **WHEN** input exceeds an applicable bound or names a critical field the receiver does not understand
- **THEN** the extension refuses the request and does not silently ignore that condition

### Requirement: Initial profile support is explicit and lossless
The initial model adapter SHALL support `morphir-ir` with `morphir-json` for supported v3/v4 Library models through `compileModel` and `generateModel`. Unsupported rich Ion profiles, distribution forms or preservation guarantees MUST be refused explicitly. No automatic lossy conversion or fallback SHALL occur. (bead: morphir-5hxy)

#### Scenario: Supported JSON model round trip
- **WHEN** a qualified JSON-profile model is compiled, generated and recompiled using an admitted tuple
- **THEN** its supported semantics and diagnostics agree with the existing compiler for the selected IR version

#### Scenario: Rich model requires unsupported preservation
- **WHEN** a host requests an Ion profile or guarantee not advertised by this increment
- **THEN** the extension refuses it rather than converting to JSON and discarding information

### Requirement: New protocol claims require executable conformance evidence
The extension SHALL advertise the new draft and model tuples only after candidate-bound executable guest qualification covers negotiation, lifecycle, supported operations and negative admission cases. Documentation MUST distinguish implemented profiles from unimplemented optional MEP capabilities. (bead: morphir-5hxy)

#### Scenario: Protocol constants exist without operation support
- **WHEN** an SDK exposes model types or method names but the Python adapter has not passed qualification
- **THEN** those symbols do not establish or justify an advertised support claim
