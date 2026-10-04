# Create Issue

`create-issue` is a portable agent skill. It turns a short description into one complete
GitHub or GitLab issue — a story, bug, task, or epic — presents the draft, and creates the
issue only after you explicitly approve that exact draft. Drafting changes nothing on the
tracker.

This directory is the whole package. It depends on nothing outside itself, so a copy
installed on its own behaves like the one in the source repository.

## Invocation

Run the skill from a checkout of the repository you want to file an issue in.

| Client | Invocation |
| --- | --- |
| Claude Code | `/create-issue <request>` |
| Codex | `$create-issue <request>`; `/skills` lists installed skills |
| Cursor | `/create-issue <request>` in Agent chat |
| Gemini CLI | No dedicated syntax: describe the issue you want drafted, and approve the activation prompt for `create-issue`. `/skills list` lists installed skills. |

For example:

```text
/create-issue Draft a bug: the CSV export drops the header row when the table is empty.
```

Review the draft, ask for changes, and approve it explicitly when it is right. To file the
issue in a project other than the checkout's, name it in the request.

Any other agent can follow the workflow by loading [`SKILL.md`](SKILL.md) directly; every
path the workflow loads is relative to it.

## Requirements

- An agent client that supports Agent Skills or can load `SKILL.md` directly.
- Git, to resolve the target project and the trusted policy revision from a local checkout.
- `gh` for GitHub or `glab` for GitLab, authenticated for the target host.
- Python 3.10 or later is optional. It runs `scripts/normalize_reference.py`, which accepts
  project and issue URLs; without it, name projects as paths such as `OWNER/REPO` and parents
  as `#N` or `PROJECT#N`.

## Contents

| Path | Contents |
| --- | --- |
| [`SKILL.md`](SKILL.md) | The workflow the agent follows. |
| [`references/`](references/) | Forge adapters, the configuration schema, the reference grammar, and the built-in templates. |
| [`scripts/normalize_reference.py`](scripts/normalize_reference.py) | The optional reference normalizer. |
| [`agents/openai.yaml`](agents/openai.yaml) | Codex interface metadata. |
| [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) | Claude Code metadata, including the package version. |
| [`CHANGELOG.md`](CHANGELOG.md) | The version history. |
| [`LICENSE`](LICENSE) | The MIT License. |

## Version

The package version is `version` in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json).
The latest entry in [`CHANGELOG.md`](CHANGELOG.md) has the same version and lists what it
changed.

## Documentation

- [Project](https://gitlab.com/hubertgajewski-ai/create-issue)
- [Installation and updating](https://gitlab.com/hubertgajewski-ai/create-issue/-/blob/main/docs/installation.md)
- [Configuration with `.create-issue.toml`](https://gitlab.com/hubertgajewski-ai/create-issue/-/blob/main/docs/configuration.md)
- [Issues](https://gitlab.com/hubertgajewski-ai/create-issue/-/issues)
- [Security policy](https://gitlab.com/hubertgajewski-ai/create-issue/-/blob/main/SECURITY.md)

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 Hubert Gajewski.
