Feature: IR interchange
  As a Morphir tooling user
  I want to inspect and convert versioned morphir-ir.json files
  So that I can move models between IR format 3.0.0 and draft IR v4

  Scenario: Inspect a morphir-elm format 3 file
    Given the golden fixture "elm-simpleValueTree.json"
    When I run "ir inspect" on it
    Then the command exits with code 0
    And the output contains "format: 3.0.0"
    And the output contains "kind: Library"
    And the output contains "package: morphir/example/app"

  Scenario: Upgrade a format 3 file to draft v4 and back
    Given the golden fixture "elm-simpleValueTree.json"
    When I convert it to "v4"
    Then the command exits with code 0
    And the converted file declares formatVersion 4
    When I inspect the converted file
    Then the output contains "draft"
    When I convert the converted file to "v3"
    Then the command exits with code 0
    And the converted file has the same JSON as the fixture

  Scenario: Unversioned IR is rejected
    Given a file with the JSON '{"distribution": []}'
    When I run "ir inspect" on it
    Then the command exits with code 1
    And the errors contain "missing_format_version"

  Scenario: Specs cannot be downgraded
    Given a file with the JSON '{"formatVersion": 4, "distribution": {"Specs": {"packageName": "a"}}}'
    When I convert it to "v3"
    Then the command exits with code 1
    And the errors contain "unsupported_v4_downgrade"
    And no converted file exists
