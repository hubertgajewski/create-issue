# Changelog

All notable changes to the `create-issue` package are recorded here. Versions follow
Semantic Versioning 2.0.0.

Each version has one section, newest first, headed `## <version> - <YYYY-MM-DD>`, or
`## <version> - Unreleased` until that version is released. The latest version must equal
`version` in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json).

## 1.0.0 - Unreleased

### Added

- The `create-issue` workflow: draft one GitHub or GitLab story, bug, task, or epic from a
  short description, and create it only after explicit approval of the presented draft.
- Target project and parent issue resolution with a strict reference grammar, and the
  optional standard-library normalizer `scripts/normalize_reference.py`.
- Repository policy read from a trusted committed revision: instruction files, native issue
  templates, and the optional `.create-issue.toml`.
- Built-in story, bug, task, and epic templates.
- GitHub and GitLab adapters, with read-only tracker queries while drafting.
- Client metadata for Codex in `agents/openai.yaml` and for Claude Code in
  `.claude-plugin/plugin.json`.
- This changelog, the package README, and the MIT license.
