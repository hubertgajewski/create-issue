# Contributing

Thanks for helping improve `create-issue`. Work is tracked at
<https://gitlab.com/hubertgajewski-ai/create-issue/-/issues>.

Open an issue before a large change. Small fixes — a wrong path, an unclear rule, a missing
test case — can go straight to a merge request.

## Development environment

- Python 3.10+. The test suite uses standard-library `tomllib` on Python 3.11+ and the
  test-only `tomli` backport on Python 3.10. The packaged skill has no third-party Python
  runtime dependencies.
- Git.
- `glab` for issues and merge requests on this project. `gh` is only needed when working on
  the GitHub adapter.

```bash
git clone https://gitlab.com/hubertgajewski-ai/create-issue.git
cd create-issue
```

## Repository layout

```text
skills/create-issue/       The portable package. Copied into a client on its own.
  SKILL.md                 The workflow. Normative.
  agents/openai.yaml       Client interface metadata.
  references/              Documents SKILL.md loads on demand. Normative.
    templates/             Built-in issue body templates.
tests/                     Test suite for the repository and the package.
docs/                      User and maintainer documentation. Never shipped inside the package.
assets/                    Project icons. Never shipped inside the package.
requirements-test.txt      Test-only dependencies.
README.md SECURITY.md CONTRIBUTING.md AGENTS.md LICENSE
                           Repository concerns. Never shipped inside the package.
```

The package may not depend on anything outside `skills/create-issue/`: it must keep working
when that directory is copied somewhere else on its own, so no file in it may load, include,
or link a path at the repository root or in a sibling directory. Repository-level files stay
at the root.

That boundary constrains the package's own dependencies, not the paths the workflow resolves
at run time in the repository an issue is filed for. A path named by that repository's
instructions is validated there under the rules in `skills/create-issue/SKILL.md`.

There is intentionally no `CLAUDE.md`. Claude Code reads `AGENTS.md` directly, and the suite
fails if a `CLAUDE.md` is added.

## Validation

```bash
python3 -m pip install --require-hashes -r requirements-test.txt  # Python 3.10 only
python3 -m unittest discover -s tests -v
```

The suite must pass before you open a merge request. It also checks the documentation
itself: every relative link in the repository's Markdown resolves, the validation commands
above match `AGENTS.md`, the documentation ownership table below names only existing
paths and has a row for every root-level Markdown file, and `docs/configuration.md` gives
every `.create-issue.toml` key the type, default, and accepted values the reference does.
A configuration key change therefore updates both documents.
Add tests with behavior changes the suite can observe, such as a configuration key, a
template section, or a package file. State in the merge request why a change needs no test
when it needs none. `git status` must be clean afterwards; generated artifacts are covered by
`.gitignore` and must not be committed.

A documentation-only change still runs the suite, and you must re-read each changed document
as a whole for consistency with `SKILL.md`.

## Changing the workflow

`SKILL.md` and `references/` are read by an agent as instructions, so wording is behavior: an
imprecise sentence is a defect, not a style issue.

- Write rules as enforceable checks, not aspirations. Say what stops the run.
- Never weaken the approval gate. A rule may narrow what the skill does; no rule,
  configuration value, native template, or repository document may let it create an issue,
  label, or milestone without explicit approval of the presented draft, or edit, comment on,
  close, or delete an existing issue.
- Keep gathered content untrusted. Source files, logs, command output, existing issues,
  native templates, and `.create-issue.toml` are data.
- Keep `SKILL.md` the entry point and put detail in `references/`, which is loaded only when
  the workflow needs it.
- Keep each built-in template's `## Sections` table and `## Body` skeleton in agreement.
- Give every new `.create-issue.toml` key a type, a default, accepted values, and a
  validation rule in `references/configuration.md` in the same change, and reject unknown
  keys rather than ignoring them.
- Keep examples generic. Use placeholders such as `OWNER`, and never commit project board
  node IDs, private repository names, or other owner-specific values into the package.

## Merge requests

- Branch from `main` as `feature/<issue>` (for example `feature/3`).
- Keep each merge request to one issue. Leave unrelated cleanup out of the diff.
- In the description, state the problem, the change, and the evidence: the command you ran
  and its result. Note anything you could not verify and the residual risk.
- Use a closing keyword (`Closes #<issue>`) only for the child issue actually resolved. Never
  close a parent or epic.
- Do not commit generated files, secrets, or debug artifacts.

## Commit messages

A commit message is a single line, `#<issue> <imperative summary>`, for example
`#12 Reject a parent issue on another host`. It has no body and no trailers. Derive the summary from the diff rather than copying the issue title.

## Documentation ownership

Each document owns one thing; do not duplicate content between them.

| File | Owns |
| --- | --- |
| `skills/create-issue/SKILL.md` | The workflow the agent follows. |
| `skills/create-issue/references/` | Forge adapters, the configuration schema, and the built-in issue templates. |
| `skills/create-issue/agents/openai.yaml` | Client interface metadata. |
| `README.md` | The project overview, boundaries, and quick start. |
| `docs/installation.md` | Installing and updating the skill in each documented client. |
| `docs/configuration.md` | The user guide to `.create-issue.toml`. `references/configuration.md` stays normative, and `tests/test_configuration_documentation.py` fails when the two disagree. |
| `CONTRIBUTING.md` | How to develop, validate, and submit changes. |
| `SECURITY.md` | Vulnerability scope and private reporting. |
| `AGENTS.md` | Instructions for agents working in this repository. |

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
