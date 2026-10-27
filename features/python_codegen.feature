Feature: Python compilation and generation
  As a Python developer modeling a domain with Morphir
  I want to compile supported Python to Morphir IR and generate Python from IR
  So that my model can move between Python and other Morphir tools

  Scenario Outline: Compile, generate and recompile a multi-module model
    Given the Python sample project "loans"
    When I compile it with package "acme/example" to IR "<version>" exposing "acme/models"
    Then the command exits with code 0
    And the compiled model declares formatVersion <format>
    And module "acme/models" is public and module "acme/rules" is private
    When I generate Python from the compiled model
    Then the command exits with code 0
    And the generated files are "acme/models.py, acme/rules.py"
    And the generated code gives the expected results in a separate process
    When I recompile the generated Python with the same options
    Then the recompiled model equals the compiled model

    Examples:
      | version | format |
      | v3      | 3      |
      | v4      | 4      |

  Scenario: Unsupported Python is rejected without output
    Given a Python source file with the text "total = 1"
    When I compile it with package "acme/example" to IR "v3"
    Then the command exits with code 1
    And the errors contain "PY004"
    And no compiled model is written

  Scenario: Generation refuses a directory that already has files
    Given the Python sample project "loans"
    When I compile it with package "acme/example" to IR "v3"
    And I generate Python into a directory that already contains "notes.txt"
    Then the command exits with code 1
    And the errors contain "not empty"
    And the directory still contains only "notes.txt"

  Scenario: A Python program compiles and generates through the API
    Given the Python sample project "loans"
    When a program compiles the project with the Python API
    Then the program receives a v3 Library model
    And generating Python from that model returns 2 artifacts
