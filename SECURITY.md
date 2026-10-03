# Security Policy

## Reporting a vulnerability

Report suspected vulnerabilities privately by opening a **confidential** issue against this
project. This link opens the issue form with confidentiality already selected:

<https://gitlab.com/hubertgajewski-ai/create-issue/-/issues/new?issue[confidential]=true>

The parameter sets the default, so confirm before submitting that **This issue is
confidential and should only be visible to team members with at least Reporter access** is
still ticked. Confidential issues are visible only to project members, so the report stays
private while it is triaged. If you reached the form by another route, tick that box
yourself.

Do not report vulnerabilities in a public issue, a merge request, or a commit message.

Please include:

- the affected file and revision (`skills/create-issue/SKILL.md`, a `references/` document,
  or a built-in template);
- the client and forge in use, if relevant;
- a minimal reproduction: the request, repository state, or crafted repository, issue,
  template, or configuration content that triggers the behavior;
- the impact you observed and the impact you believe is reachable.

Redact real credentials from any reproduction. Use a placeholder such as
`[REDACTED CREDENTIAL]`.

## Scope

This project is a skill that reads untrusted repository and tracker content, drafts an
issue, and publishes it to a tracker after the user approves the draft. Its security
boundary is the approval gate, the content it writes into a new issue, and the project it
writes to. In scope:

- **Approval-gate bypass** — creating an issue, label, or milestone without explicit
  approval of the presented draft, including after the title, body, metadata, or target
  changed, or because repository instructions, a native template, or `.create-issue.toml`
  widened rather than narrowed the boundary.
- **Mutation of existing issues** — editing, commenting on, closing, reopening,
  transferring, or deleting an existing issue, including as a rollback of a partial
  failure.
- **Prompt injection from gathered content** — following instructions embedded in source
  files, logs, command output, existing issues and comments, linked pages, native
  templates, or repository policy files instead of reading them as data.
- **Credential exposure** — reproducing a credential, token, private key, cookie,
  authorization value, or password in a drafted or created issue, or sending credentials to
  a plain-HTTP origin or an unintended host.
- **Quick-action execution** — a GitLab quick action, such as `/close` or `/assign`,
  executing from a created description, whether it came from a native template or from
  gathered content.
- **Target confusion** — resolving the wrong target project or host, applying one
  project's repository policy to another project, or linking a parent on a different host.
- **Path traversal** — reading a referenced policy file through an absolute prefix, `..`
  component, symlink, or submodule traversal, or from the mutable worktree instead of the
  trusted revision.
- **Shell injection** — a title, body, label, milestone, or other user-derived or
  configuration-derived value interpolated into shell syntax instead of passed as a
  separate argument or a file.

Also in scope: unbounded untrusted content reaching model context in a way that defeats the
documented excerpt limits, and an unrequested `@`-mention that notifies people on creation.

Out of scope:

- Vulnerabilities in the agent clients, forge CLIs (`gh`, `glab`), or the forges
  themselves. Report those to their maintainers.
- Content the user wrote or explicitly approved after the skill presented it accurately.
- Findings that require an already-compromised local machine or shell.
- Missing hardening with no demonstrated impact.

## Response expectations

This project is maintained by one person, on a best-effort basis.

- Acknowledgement within 7 days.
- An initial assessment, including whether the report is in scope, within 14 days.
- A fix or a documented mitigation for confirmed in-scope reports within 90 days, tracked
  in the confidential issue until it is resolved.

The confidential issue is made public after a fix ships, unless the reporter asks otherwise.
Credit is given in the issue and merge request unless the reporter prefers to stay anonymous.
There is no bug bounty.
