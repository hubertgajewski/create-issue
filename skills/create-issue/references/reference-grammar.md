# Reference Grammar

Normalize every target project and parent issue reference the user gives before it selects a target, reaches a tracker command, or appears in a draft. This document is normative: a reference outside it is rejected, never repaired by guessing. [scripts/normalize_reference.py](../scripts/normalize_reference.py) implements it with the Python 3.10 standard library.

A GitLab group epic (`&N` or a `/groups/` URL) is not an issue reference and is outside this grammar; it follows the group-epic rule in [forges.md](forges.md).

## Common rules

- **Text**: trim surrounding whitespace once. The rest must be 1 to 4,096 printable ASCII characters with no whitespace.
- **Project component**: 1 to 100 ASCII letters, digits, `_`, `.`, or `-`; not `.` or `..`; not beginning with `-`.
- **Project path**: two or more project components joined by `/`, at most 255 characters. A GitHub project path has exactly two components, `OWNER/REPO`. A GitLab project path does not begin with the component `groups`, which names a group, not a project.
- **Issue number**: 1 to 20 ASCII digits without a leading zero.
- **Host**: lowercased, then dot-separated labels of 1 to 63 ASCII letters, digits, or `-`, neither beginning nor ending with `-`, at most 253 characters. An optional port is 1 to 65,535 without a leading zero; port 443 is removed, and any other port stays part of the host as `HOST:PORT`. An IP literal in brackets is rejected.
- **Provider**: a host whose labels include `github` or `gitlab`, such as `github.com` or `gitlab.example.com`, identifies that provider. A host with both labels is rejected. Otherwise the provider comes from `--provider`, and is `null` when that is absent. A `--provider` that contradicts the host's provider is rejected.

## URLs

Every URL must satisfy all of these:

- The scheme is `https`, compared case-insensitively. Every other scheme is rejected, including `http`, so no plain-HTTP reference reaches a tracker command.
- The authority is a host and optional port only. User information, anything before an `@`, is rejected because it may be a credential.
- The path contains no `%`. Project components never need percent-encoding, so encoded text can only disguise a separator or a different path.
- The query and fragment are discarded and never enter the result.
- After removing the leading `/` and at most one trailing `/`, the path is nonempty and has no empty component.

## Target projects

A target project is one of:

- a **project path**, such as `OWNER/REPO` or `GROUP/SUBGROUP/PROJECT`. It names no host, so the result's `host` is `null` unless a host is supplied separately with `--host`, which is validated by the host rule alone and never joined with the path into a URL. The path is never rewritten: `OWNER/REPO.git` keeps its `.git`;
- a **project URL**, `https://HOST/PROJECT`. One `.git` suffix on the last component is removed, so `https://gitlab.example.com/group/subgroup/project.git` normalizes to host `gitlab.example.com`, project `group/subgroup/project`. A path with a `-` component, such as `/-/tree/main`, points inside a project and is rejected.

When the provider is still unknown, the GitHub and GitLab project path rules cannot apply yet. Normalize the project again with `--provider` once the provider is resolved, and treat a rejection then like any other.

## Parent issues

A parent is resolved against the frozen target, whose provider, host, and project must themselves satisfy this grammar:

| Form | Project | Host |
| --- | --- | --- |
| `N` or `#N` | the target project | the target host |
| `PROJECT#N` | `PROJECT` | the target host |
| GitHub issue URL `https://HOST/OWNER/REPO/issues/N` | `OWNER/REPO` | `HOST` |
| GitLab issue URL `https://HOST/PROJECT/-/issues/N` | `PROJECT` | `HOST` |
| GitLab work item URL `https://HOST/PROJECT/-/work_items/N` | `PROJECT` | `HOST` |

- A parent URL's host must equal the target host after normalization; a parent on another host is rejected.
- The URL form must match the target provider: a `/-/` form on a GitHub target, or `/issues/N` without `/-/` on a GitLab target, is rejected.
- Every other URL is rejected as a parent, including merge request, pull request, file, tree, project, and group URLs.

## Helper

```text
python3 scripts/normalize_reference.py project --ref REFERENCE [--provider github|gitlab] [--host HOST]
python3 scripts/normalize_reference.py parent --ref REFERENCE --provider github|gitlab --host HOST --project PROJECT
```

Run it from the package directory, or give the script's path inside the package. Pass each value as a separate quoted argument, never through shell evaluation. In `project` mode, `--host` is accepted only with a project path and is rejected with a project URL. In `parent` mode, `--provider`, `--host`, and `--project` are the frozen target.

On success the helper exits `0` and prints one JSON object:

```json
{"host": "gitlab.example.com", "issue": 12, "project": "group/project", "provider": "gitlab"}
```

- `provider` is `github`, `gitlab`, or `null` when no host or `--provider` identifies it.
- `host` is the normalized host, or `null` for a project path given without `--host`.
- `project` is the normalized project path.
- `issue` is the issue number in `parent` mode and `null` in `project` mode.

On rejection it exits `2`, prints nothing on standard output, and prints one `error: REASON` line on standard error. Invalid arguments also exit `2`. A reason never repeats the rejected text.

Treat any nonzero exit, missing output, or malformed JSON as a rejection.

## Without the helper

When Python 3.10 or later is unavailable, apply the common rules in memory to project paths, `N`, `#N`, and `PROJECT#N` only. Do not parse a URL by hand; ask the user to restate it as a project path or `PROJECT#N`, and, for a target project that no single remote has, to name its host. Check that host against the host rule alone, as the helper's `--host` does, and keep the project path unchanged; never join them into a URL to parse.

## Rejections

A rejected reference is a stop condition: run no tracker command with it and do not present a draft that depends on it. Report the reason and ask the user for a corrected reference. Never repeat the rejected text in the report or the draft, because it may contain a credential; refer to a credential as `[REDACTED CREDENTIAL]`.
