# docs/site Specification

## Purpose

Provide a public, repository-owned documentation site that users can navigate and contributors can preview and validate before publication.

## Requirements

### Requirement: Documentation is discoverable
The site SHALL expose installation, Python API, CLI, extension integration and contributor guides through navigation and search. Repository and package READMEs SHALL link to the site while retaining useful installation summaries. (bead: morphir-ukvn.9.1)

#### Scenario: Find a workflow
- **WHEN** a user opens the home page or searches for Python compilation
- **THEN** the user can reach the corresponding runnable API and CLI guides and their prerequisites

### Requirement: Documentation remains readable across devices
The site SHALL support keyboard navigation, visible focus, light and dark themes, and narrow screens. Code examples SHALL preserve whitespace, identify their language and allow copying without decorative prompt characters. (bead: morphir-ukvn.9.1)

#### Scenario: Read a guide on a narrow screen
- **WHEN** a reader opens a guide at a 360-pixel viewport in either theme
- **THEN** navigation and content remain usable without page-level horizontal overflow, with long code scrollable within its block

#### Scenario: Navigate using a keyboard
- **WHEN** a reader uses keyboard controls to open navigation, search and copy an example
- **THEN** each control is reachable and exposes visible focus and an accessible name

### Requirement: Contributors can reproduce a checked preview
The repository SHALL document a pinned site-tool installation and commands to build, check and serve a local preview. Builds SHALL exclude planning artifacts and validate local pages, resources, fragments and deployment-base paths before publication. (bead: morphir-ukvn.9.1)

#### Scenario: Preview a project-path deployment
- **WHEN** a contributor follows the guide in a clean checkout and builds for the repository's Pages path
- **THEN** the site passes checks and local preview resolves navigation, search and assets beneath that path

#### Scenario: Broken content blocks publication
- **WHEN** a page links to a nonexistent local fragment or resource
- **THEN** validation fails with an actionable location and the invalid output is not published

### Requirement: Publication uses verified output
Site publication SHALL consume the exact output that passed required site and example checks for the selected source revision. Pull requests SHALL receive validation without production publication. Failed, missing or cancelled required checks MUST block publication. (bead: morphir-ukvn.9.4)

#### Scenario: Publish a checked revision
- **WHEN** an authorized main-branch publication passes its required checks
- **THEN** deployment publishes their verified artifact with recorded source and tool versions

#### Scenario: Example verification fails
- **WHEN** required example verification fails or is unexpectedly skipped
- **THEN** no production site deployment occurs for that revision

### Requirement: Reusable site limitations are reported upstream
When a site-foundation limitation obstructs a required experience, contributors MUST record a reproducible report in Telescope's tracker or link existing upstream work, documenting the affected version, consumer need and any temporary workaround. (bead: morphir-ukvn.9.1)

#### Scenario: A required presentation feature is unavailable
- **WHEN** a contributor confirms the pinned foundation cannot render a required example interaction
- **THEN** the change records an upstream report or existing proposal and labels any workaround and remaining acceptance gap

### Requirement: The site follows the Morphir MoonBit visual design
The documentation SHALL use morphir-moonbit's blue/orange palette in light and dark themes, and its landing-page structure with a split hero, code window, workflow pipeline and feature cards. Content and calls to action SHALL describe qualified Python workflows and remain usable at 360 pixels. The displayed model MUST match a canonical checked Python example. (bead: morphir-ukvn.9.1)

#### Scenario: Open the Python landing page
- **WHEN** a reader opens the site at either supported deployment base in either theme
- **THEN** the Morphir palette and responsive landing design are visible, the model matches the checked source, and the main actions reach the API and CLI guides without overflow
