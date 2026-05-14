# Changelog

All notable changes to Tide are documented here.

## 1.3.1 - 2026-05-14

### Added

- Added Codex plugin metadata, skills, and slash command docs via `.codex-plugin/`, `codex-skills/`, and `commands/`.
- Added local Codex marketplace wrapper files for installing Tide from this repository.
- Added Cursor project rules and commands via `.cursor/rules/*.mdc` and `.cursor/commands/*.md`.
- Added contract tests for Codex and Cursor adapter files.
- Added a Superpowers implementation plan for no-source mode generalization.
- Added bilingual README docs and bilingual architecture diagrams.

### Changed

- Improved no-source mode prompt behavior so scenario confidence and L4/L5 assertion planning can use HAR evidence and end-to-end chain heuristics.
- Improved case-writer prompt guidance for existing project naming conventions and dynamic ID fallback.
- Improved project-scanner prompt guidance for detecting snake_case vs PascalCase test class naming.
- Made Chinese the default README entry and moved English docs to `README-EN.md`.

### Removed

- Removed historical Superpowers plan/spec archives from the release tree.

### Fixed

- Restored `.repos/` compatibility in scaffold-generated `.gitignore` files while retaining `.tide/` ignores.
