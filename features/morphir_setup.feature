Feature: Morphir Python Setup
  As a developer
  I want to verify the project is set up correctly
  So that I can start developing Morphir features

  Scenario: Morphir core library can be imported
    Given the Python environment is set up
    When I import the morphir module
    Then the module should be available
    And it should have a version attribute

  Scenario: Morphir tools can be imported
    Given the Python environment is set up
    When I import the morphir_tools module
    Then the module should be available
    And it should have a version attribute

  Scenario: Morphir IR module can be imported
    Given the Python environment is set up
    When I import the morphir.ir module
    Then the module should be available
