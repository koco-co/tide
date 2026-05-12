# Changelog

All notable changes to Tide are documented here.

## Unreleased

### Added

- Added Codex plugin metadata, skills, and slash command docs via `.codex-plugin/`, `codex-skills/`, and `commands/`.
- Added Cursor project rules and commands via `.cursor/rules/*.mdc` and `.cursor/commands/*.md`.
- Added contract tests for Codex and Cursor adapter files.
- Added a Superpowers implementation plan for no-source mode generalization.

### Changed

- Improved no-source mode prompt behavior so scenario confidence and L4/L5 assertion planning can use HAR evidence and end-to-end chain heuristics.
- Improved case-writer prompt guidance for existing project naming conventions and dynamic ID fallback.
- Improved project-scanner prompt guidance for detecting snake_case vs PascalCase test class naming.

### Fixed

- Restored `.repos/` compatibility in scaffold-generated `.gitignore` files while retaining `.tide/` ignores.
