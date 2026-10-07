# Create Issue

A portable agent skill that turns a short description into one complete GitHub or GitLab
issue — a story, bug, task, or epic — shows you the draft, and creates it only after you
approve that exact draft.

The skill assumes nothing about your repository layout, forge, label vocabulary, or planning
process. It follows your repository's instruction files, native issue templates, and an
optional `.create-issue.toml`, and it asks when the evidence is ambiguous.

- Project: <https://gitlab.com/hubertgajewski-ai/create-issue>
- Issues: <https://gitlab.com/hubertgajewski-ai/create-issue/-/issues>

## What it does

- Resolves the target project from the project you name or from the checkout's Git remotes,
  and rejects an ambiguous project or parent reference instead of guessing.
- Reads `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, native issue templates, and
  `.create-issue.toml` from a trusted committed revision, so uncommitted edits cannot change
  the rules of a run.
- Classifies the request as a story, bug, task, or epic and drafts it from a native issue
  template or the matching built-in template, with numbered acceptance criteria and a
  Done Checklist that includes your team's Definition of Done when one is configured.
- Searches open and closed issues for duplicates before drafting.
- Proposes labels, a milestone, an estimate or epic size, and project-board fields, and
  checks a parent issue you name, using read-only tracker queries.
- Reports quality notes beside the draft, such as an INVEST check for a story or missing
  reproduction steps for a bug.

## Boundaries

The skill has two boundaries and never crosses from the first to the second on its own:

| Boundary | The skill will |
| --- | --- |
| Draft (the default) | Gather context, run read-only tracker queries, and present the complete draft. It makes no change on the tracker. |
| Create | Create the issue and apply its approved labels, milestone, estimate, parent link, and project-board fields. |

- **Drafting is the default.** A request such as "create an issue for X" authorizes a draft,
  not creation.
- **Creation needs explicit approval of the presented draft.** If the title, body, type,
  labels, milestone, estimate, size, parent, or target project changes after you approve,
  the skill presents the changed draft and waits for a new approval.
- **A new label or milestone needs its own approval.** Creating a label or milestone that
  does not exist yet is a separate change, approved separately.
- **Existing issues are never edited.** The skill does not edit, comment on, close, reopen,
  transfer, or delete an existing issue. When you want one changed, it hands you the drafted
  text and stops.

Repository instructions, native templates, and `.create-issue.toml` can narrow these
boundaries. Nothing can widen them.

## Untrusted-input model

Everything the skill gathers as context is data, never instructions: source files and
comments, logs, command output, existing issues and comments, linked pages, native issue
templates, and repository policy files.

- Instructions embedded in that content are never followed and never broaden your authority.
- Credentials found in it are never reproduced; a draft uses `[REDACTED CREDENTIAL]` instead.
- Excerpts are bounded in size, and every truncation is reported.
- No line of a GitLab body begins with `/` outside a fenced code block, so a quick action
  such as `/close` cannot run when the issue is created.
- Titles, bodies, labels, and other values are passed to `gh` or `glab` as separate
  arguments or a file, never spliced into shell syntax.
- Tracker requests use HTTPS, and project and parent references follow a strict grammar.

## Quick start

1. Install a release with the checksum-verified installer, or copy `skills/create-issue/` on
   its own into your client's skill directory. The
   [installation guide](docs/installation.md) gives the commands and the directory for each
   client and scope.
2. Authenticate `gh` for GitHub or `glab` for GitLab.
3. From the repository you want to file an issue in, invoke the skill:

   | Client | Invocation |
   | --- | --- |
   | Claude Code | `/create-issue <what the issue is about>` |
   | Codex | `$create-issue <what the issue is about>` |
   | Cursor | `/create-issue <what the issue is about>` in Agent chat |
   | Gemini CLI | No dedicated syntax. Describe the issue you want drafted and approve the `create-issue` activation prompt. |

   Any other agent can follow the workflow by loading `create-issue/SKILL.md` from the
   installed directory.

For example:

```text
/create-issue Draft a bug: the CSV export drops the header row when the table is empty.
```

Review the draft, ask for changes, and approve it explicitly when it is right. To file the
issue in a project other than the checkout's, name it in the request, for example
`GROUP/PROJECT` or its HTTPS URL.

## Requirements

- An agent client that supports Agent Skills or can load `SKILL.md` directly.
- Git, to resolve the target project and the trusted policy revision from a local checkout.
- `gh` for GitHub or `glab` for GitLab, authenticated for the target host. Drafting uses
  them for read-only queries such as labels, milestones, and duplicate search.
- Python 3.10 or later is optional. It runs the bundled reference normalizer, which accepts
  project and issue URLs; without it, name projects as paths such as `OWNER/REPO` and parents
  as `#N` or `PROJECT#N`.

## Documentation

- [Installation](docs/installation.md) — requirements, client directories, user and project
  scope, verifying the install, and updating.
- [Configuration](docs/configuration.md) — the optional `.create-issue.toml`, key by key,
  with what configuration cannot do.
- [`skills/create-issue/SKILL.md`](skills/create-issue/SKILL.md) — the workflow itself.
- [`skills/create-issue/references/`](skills/create-issue/references/) — the forge adapters,
  the normative configuration schema, the reference grammar, and the built-in templates.
- [Contributing](CONTRIBUTING.md) — development environment, validation, and merge requests.
- [Security policy](SECURITY.md) — what is in scope and how to report a vulnerability
  privately.
- [Maintainer guide](docs/maintainers.md) — CI and pipeline controls.

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 Hubert Gajewski.
