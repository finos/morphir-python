## MODIFIED Requirements

### Requirement: Model operation admission is bilateral
Each model operation SHALL require an initialized, advertised tuple matching operation, profile, codec, envelope version and semantic IR version. Session tuples and limits MUST remain within both peers' offers and permitted static claims. Unknown required guarantees and unadmitted tuples MUST be refused. (bead: morphir-5hxy)

#### Scenario: Compile support does not grant generation
- **WHEN** only a compile tuple was admitted and the host requests model generation
- **THEN** the operation is refused without invoking the generator

#### Scenario: Independent lists would produce an unsupported combination
- **WHEN** an operation combines otherwise known tuple members in a combination not admitted as a complete tuple
- **THEN** the extension refuses that combination rather than forming a Cartesian product

#### Scenario: Host default not supported
- **WHEN** the host offers an Ion tuple first, as its default, and also offers a JSON tuple this extension serves, without requiring Ion
- **THEN** the session agrees on the JSON tuple in the host's order, and the model operations for that tuple succeed

#### Scenario: Host offers only formats the extension does not serve
- **WHEN** the host offers only Ion tuples
- **THEN** the session agrees on no model tuple, model operations are refused, no payload is converted to JSON, and the session does not fall back to retired MEP `0.1`
