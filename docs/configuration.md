# Configuration

`create-issue` works with no configuration. It follows your repository's instruction files,
native issue templates, and existing labels and milestones, and falls back to package
defaults for the rest.

Add a `.create-issue.toml` at the repository root only for decisions the skill cannot
discover from those, such as a title prefix style, the labels every bug gets, or where
estimates are written.

This page is the user guide. The schema, validation rules, and precedence are normative in
[`skills/create-issue/references/configuration.md`](../skills/create-issue/references/configuration.md);
if the two ever disagree, the reference is correct and this page is a bug.
`tests/test_configuration_documentation.py` compares every key's type, default, and accepted
values in the tables below with that reference, so the suite fails when either one changes
alone.

## What configuration cannot do

- **It cannot authorize creation without approval.** An issue is created only after you
  explicitly approve the exact draft presented to you. No key skips or pre-approves that
  step.
- **It cannot authorize creating a label or milestone.** Configuration can name labels and
  milestones, but one that does not exist yet is created only after its own explicit
  approval.
- **It cannot authorize any change to an existing issue.** The skill never edits, comments
  on, closes, reopens, transfers, or deletes an existing issue, whatever the file says.
- **It is data, never code.** The file is parsed as TOML. It is never sourced or executed,
  and its values are never interpolated into shell syntax.

Validation is strict. An unknown table or key stops the run, as do a missing or unsupported
`version`, a value of the wrong type, a value outside a key's accepted values, and every
other rule under Validation in the reference. The skill reports the key, the value, and the
rule it breaks; it never ignores, coerces, or guesses an invalid value.

## Where it fits

Settings apply in this order, first match winning:

1. What you ask for in the request.
2. Repository instruction files: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, and the issue
   or planning documents they reference.
3. Native issue templates.
4. `.create-issue.toml`.
5. Package defaults.

So the file fills gaps the levels above it leave open; it does not override them.

The file is read only when repository policy applies: you run the skill from a local
checkout, and you either name no project or name the project of one of the checkout's
remotes. When you name another project, the file is not read at all and package defaults
apply.

The skill reads the file from a trusted committed revision: the default-branch tip of
`origin`, or of the only forge remote when there is no `origin`, after a fetch when the
network allows it. A modified, untracked, or unmerged copy has no effect. Commit the file and
merge it into the default branch before relying on it.

## A minimal file

A GitLab project that records estimates as issue weights and wants every issue in a
milestone:

```toml
version = 1

[milestone]
policy = "required"

[estimation]
target = "gitlab-weight"
```

`version` is required whenever the file exists. Every other key is optional; omit anything
you are happy to leave to the defaults.

## Keys

Each table lists the key's type, its default when omitted, and the values it accepts. Keys
inside a TOML table, such as `[title]`, are written in the tables below with the table name
as a prefix: `prefix` under `[title]` is `title.prefix`.

### Schema version and target

```toml
version = 1
provider = "auto"                    # auto | github | gitlab
remote = "origin"
```

| Key | Type | Default | Accepted values |
| --- | --- | --- | --- |
| `version` | integer | required | `1` |
| `provider` | string | `"auto"` | `auto`, `github`, `gitlab` |
| `remote` | string | `"origin"` | a Git remote name |

- **`provider`** identifies the forge of a self-hosted host whose name does not. Neither
  `github.com` and `gitlab.com` nor a self-hosted host with a `github` or `gitlab` hostname
  label, such as `gitlab.example.com`, needs it. A configured `provider` that contradicts a
  host that identifies itself stops the run.
- **`remote`** selects the target project when you name none, which suits a fork whose
  issues belong upstream (`remote = "upstream"`). The remote must exist and its host must
  identify a forge; otherwise the run stops. A project you name in the request always wins.

### Titles

```toml
[title]
prefix = "category"                  # none | type | category
categories = ["feature", "bug", "chore", "docs"]
max_length = 72
```

| Key | Type | Default | Accepted values |
| --- | --- | --- | --- |
| `title.prefix` | string | `"none"` | `none`, `type`, `category` |
| `title.categories` | string array | `[]` | nonempty strings without `[`, `]`, or line breaks |
| `title.max_length` | integer | `72` | `20` through `256` |

- **`prefix`** `none` writes the title alone, `type` writes `[<type>] <title>`, such as
  `[bug] Export drops the header row`, and `category` writes `[<category>] <title>` with one
  value from `categories`.
- **`categories`** must be nonempty when `prefix = "category"`.
- **`max_length`** limits the complete title, including any prefix.

### Issue types

```toml
[types]
enabled = ["story", "bug", "task"]
default_persona = "site administrator"
```

| Key | Type | Default | Accepted values |
| --- | --- | --- | --- |
| `types.enabled` | string array | `["story", "bug", "task", "epic"]` | nonempty subset of `story`, `bug`, `task`, `epic` |
| `types.default_persona` | string | `"user"` | 1 through 80 characters, no line breaks |

- **`enabled`** lists the issue types the skill may draft.
- **`default_persona`** is the "As a …" persona of a user story when neither you nor your
  repository instructions name one. Make it as specific as your users are.

### Labels

```toml
[labels]
policy = "existing-only"             # existing-only | propose-new | none
story = ["enhancement"]
bug = ["bug"]
task = ["maintenance"]
epic = ["epic"]
bug_detection = ["found-by-test", "found-by-manual-testing", "found-in-production"]
```

| Key | Type | Default | Accepted values |
| --- | --- | --- | --- |
| `labels.policy` | string | `"existing-only"` | `existing-only`, `propose-new`, `none` |
| `labels.story` | string array | `[]` | label names |
| `labels.bug` | string array | `[]` | label names |
| `labels.task` | string array | `[]` | label names |
| `labels.epic` | string array | `[]` | label names |
| `labels.bug_detection` | string array | `[]` | label names |

- **`policy`**
  - `existing-only` applies existing labels that fit the issue, plus every configured label
    for its type that exists. A configured label that does not exist is reported as missing,
    and its creation is offered for separate approval.
  - `propose-new` also suggests new labels where no existing label fits, each needing the
    same separate approval.
  - `none` applies no labels and ignores the per-type lists and `bug_detection`.
- **`story`, `bug`, `task`, `epic`** are labels always proposed for that type.
- **`bug_detection`** is a vocabulary for how a bug was found. When it is nonempty, exactly
  one of its labels is applied to every bug, and the skill asks when it cannot tell which.

### Milestones

```toml
[milestone]
policy = "optional"                  # none | optional | required

[[milestone.rules]]
name = "CI Improvements"
when = "CI workflows, scheduling, caching, dependency bots"
```

| Key | Type | Default | Accepted values |
| --- | --- | --- | --- |
| `milestone.policy` | string | `"optional"` | `none`, `optional`, `required` |
| `milestone.rules[].name` | string | none | a milestone title |
| `milestone.rules[].when` | string | none | nonempty prose |

- **`policy`** `none` never assigns a milestone. `optional` assigns an open milestone when a
  rule or an obvious existing milestone fits. `required` always assigns one; when nothing
  fits, it proposes a new milestone for separate approval rather than choosing silently.
- **`rules`** are checked in order, and the first whose `when` describes the issue wins.
  Every rule needs both `name` and `when`, and no two rules may share a `name`. A rule that
  names a milestone that does not exist proposes creating it; it is never assigned silently.

### Definition of Done

```toml
[definition_of_done]
common = ["Tests cover each acceptance criterion"]
```

| Key | Type | Default | Accepted values |
| --- | --- | --- | --- |
| `definition_of_done.common` | string array | `[]` | nonempty strings |

- **`common`** items are appended to every Definition of Done the selected template has,
  unless an issue-specific item already covers them.

### Estimates

```toml
[estimation]
target = "github-project"            # none | github-project | gitlab-weight
scale = [1, 2, 3, 5, 8]
warn_at = 13
refuse_at = 21
epic_sizes = ["XS", "S", "M", "L", "XL"]
```

| Key | Type | Default | Accepted values |
| --- | --- | --- | --- |
| `estimation.target` | string | `"none"` | `none`, `github-project`, `gitlab-weight` |
| `estimation.scale` | integer array | `[1, 2, 3, 5, 8]` | strictly increasing positive integers |
| `estimation.warn_at` | integer | `13` | greater than every `scale` value |
| `estimation.refuse_at` | integer | `21` | greater than `warn_at` |
| `estimation.epic_sizes` | string array | `["XS", "S", "M", "L", "XL"]` | nonempty strings, smallest first |

- **`target`** decides where an estimate is written: nowhere (`none`), a GitHub project
  board (`github-project`, which needs a `[github_project]` table and a GitHub target), or
  the GitLab issue weight (`gitlab-weight`, which needs a GitLab target).
- **`scale`** holds the ordinary estimate values for stories, bugs, and tasks.
- **`warn_at`** is the only larger estimate allowed. The skill proposes it with a warning
  that the issue should probably be split, and writes it only after you confirm that value.
- **`refuse_at`** and anything above it are refused; the skill proposes an epic with child
  issues instead.
- **`epic_sizes`** are the sizes an epic can get, matched by name to the options of the
  project board's size field. An epic gets a size only with `target = "github-project"` and
  a nonempty `github_project.size_field`; otherwise it gets neither a size nor an estimate.

### GitHub project board

```toml
[github_project]
owner = "OWNER"
number = 1
estimate_field = "Estimate"
size_field = "Size"
```

| Key | Type | Default | Accepted values |
| --- | --- | --- | --- |
| `github_project.owner` | string | none | a user or organization login, or `@me` |
| `github_project.number` | integer | none | positive integer |
| `github_project.estimate_field` | string | `"Estimate"` | field name |
| `github_project.size_field` | string | `"Size"` | field name, or `""` to disable |

- When this table is present, every created issue is added to the project, and both `owner`
  and `number` are required. The table is rejected when the target is on GitLab.
- The project, its fields, and each size option are looked up by name when the skill runs.
  A missing project, field, or option stops the run before the issue is created; the skill
  never writes a different field or option.
- Never put project, field, or option node IDs in the file.

## Full example

Every key, for reference; a real file is usually much shorter. The suite parses this block
and checks that it uses exactly the keys the reference defines, with values of the declared
types and accepted values.

```toml
version = 1
provider = "auto"
remote = "upstream"

[title]
prefix = "category"
categories = ["feature", "bug", "chore", "docs"]
max_length = 80

[types]
enabled = ["story", "bug", "task", "epic"]
default_persona = "site administrator"

[labels]
policy = "existing-only"
story = ["enhancement"]
bug = ["bug"]
task = ["maintenance"]
epic = ["epic"]
bug_detection = ["found-by-test", "found-by-manual-testing", "found-in-production"]

[milestone]
policy = "required"

[[milestone.rules]]
name = "Bug Fixes"
when = "Bugs, flaky tests, and security patches"

[[milestone.rules]]
name = "CI Improvements"
when = "CI workflows, scheduling, caching, and dependency bots"

[definition_of_done]
common = ["User-facing documentation updated for any behavior change"]

[estimation]
target = "github-project"
scale = [1, 2, 3, 5, 8]
warn_at = 13
refuse_at = 21
epic_sizes = ["XS", "S", "M", "L", "XL"]

[github_project]
owner = "OWNER"
number = 1
estimate_field = "Estimate"
size_field = "Size"
```

This example is valid only for a GitHub target, because it writes estimates to a GitHub
project board.
