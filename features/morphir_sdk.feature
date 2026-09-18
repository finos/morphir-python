Feature: Morphir SDK
  As a developer of Morphir models
  I want a Python runtime for the Morphir SDK
  So that compiled models behave as they do in Elm

  Scenario Outline: Every core SDK module can be imported
    When I import the SDK module "<module>"
    Then the SDK module should be available

    Examples:
      | module  |
      | basics  |
      | char    |
      | string  |
      | list    |
      | dict    |
      | set     |
      | maybe   |
      | result  |
      | tuple   |
      | decimal |
      | int     |
      | number  |

  Scenario: A dictionary lists its entries in key order
    Given an SDK dictionary built from the pairs "b=2, a=1, c=3"
    When I list the keys of the dictionary
    Then the keys should be "a, b, c"

  Scenario: Two dictionaries built in a different order are equal
    Given an SDK dictionary built from the pairs "b=2, a=1"
    And another SDK dictionary built from the pairs "a=1, b=2"
    Then the two dictionaries should be equal

  Scenario: Rounding follows Elm and not Python
    When I round the float 2.5 with the SDK
    Then the rounded value should be 3

  Scenario: Decimal arithmetic is exact
    When I add the decimals "0.1" and "0.2" with the SDK
    Then the decimal result should print as "0.3"
