# Project Configuration

`.create-issue.toml` is optional. Add it at the repository root only for decisions the skill cannot discover from repository instructions, native issue templates, and existing labels and milestones.

## Contents

- Trusted loading
- Schema
- Keys
- Validation
- Field behavior
- Examples

## Trusted loading

Read the file only when `SKILL.md` determines that repository policy applies to the target, and only from the trusted policy revision it selects, with `git show <revision>:.create-issue.toml`. A modified or untracked worktree copy is never authority. Parse it as TOML data; never source it, execute it, or interpolate its values into shell syntax. If Python 3.11 or later is available, `tomllib` may parse it; otherwise interpret only the documented scalar, string-array, integer-array, and table forms, and treat anything else as a validation error.

Configuration fills gaps below the user's request, repository instruction files, and native issue templates. It can never authorize creation without approval, creation of labels or milestones without approval, or any mutation of an existing issue.

## Schema

Every key is shown with an illustrative value. Defaults are listed under Keys.

```toml
version = 1
provider = "auto"                    # auto | github | gitlab
remote = "origin"

[title]
prefix = "none"                      # none | type | category
categories = ["feature", "bug", "chore", "docs"]
max_length = 72

[types]
enabled = ["story", "bug", "task", "epic"]
default_persona = "user"

[labels]
policy = "existing-only"             # existing-only | propose-new | none
story = ["enhancement"]
bug = ["bug"]
task = ["maintenance"]
epic = ["epic"]
bug_detection = ["found-by-test", "found-by-manual-testing", "found-in-production"]

[milestone]
policy = "optional"                  # none | optional | required

[[milestone.rules]]
name = "CI Improvements"
when = "CI workflows, scheduling, caching, dependency bots"

[definition_of_done]
common = ["Tests cover each acceptance criterion"]

[estimation]
target = "none"                      # none | github-project | gitlab-weight
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

## Keys

| Key | Type | Default | Accepted values | Meaning |
| --- | --- | --- | --- | --- |
| `version` | integer | required | `1` | Schema version. Required whenever the file exists. |
| `provider` | string | `"auto"` | `auto`, `github`, `gitlab` | Identifies the forge for a self-hosted host whose name does not. It must agree with the resolved target. |
| `remote` | string | `"origin"` | a Git remote name | The remote whose project is the target when the user names none. It must exist and its host must identify a forge. |
| `title.prefix` | string | `"none"` | `none`, `type`, `category` | Title prefix style: none, `[<type>]`, or `[<category>]`. |
| `title.categories` | string array | `[]` | nonempty strings without `[`, `]`, or line breaks | Categories for `prefix = "category"`. Required to be nonempty for that style. |
| `title.max_length` | integer | `72` | `20` through `256` | Maximum length of the complete title, including any prefix. |
| `types.enabled` | string array | `["story", "bug", "task", "epic"]` | nonempty subset of `story`, `bug`, `task`, `epic` | Issue types the skill may draft. |
| `types.default_persona` | string | `"user"` | 1 through 80 characters, no line breaks | User-story persona when neither the user nor repository policy names one. |
| `labels.policy` | string | `"existing-only"` | `existing-only`, `propose-new`, `none` | How labels are chosen; see Field behavior. |
| `labels.story` | string array | `[]` | label names | Labels always proposed for stories. |
| `labels.bug` | string array | `[]` | label names | Labels always proposed for bugs. |
| `labels.task` | string array | `[]` | label names | Labels always proposed for tasks. |
| `labels.epic` | string array | `[]` | label names | Labels always proposed for epics. |
| `labels.bug_detection` | string array | `[]` | label names | Detection vocabulary; exactly one is applied to each bug when nonempty. |
| `milestone.policy` | string | `"optional"` | `none`, `optional`, `required` | Whether a milestone is never, optionally, or always assigned. |
| `milestone.rules[].name` | string | none | a milestone title | Milestone to assign when its rule matches. |
| `milestone.rules[].when` | string | none | nonempty prose | The kind of work that belongs in the named milestone. |
| `definition_of_done.common` | string array | `[]` | nonempty strings | Items appended to every Definition of Done that has one. |
| `estimation.target` | string | `"none"` | `none`, `github-project`, `gitlab-weight` | Where estimates are written, if anywhere. |
| `estimation.scale` | integer array | `[1, 2, 3, 5, 8]` | strictly increasing positive integers | Ordinary estimate values. |
| `estimation.warn_at` | integer | `13` | greater than every `scale` value | Estimate allowed only after a split warning and explicit confirmation. |
| `estimation.refuse_at` | integer | `21` | greater than `warn_at` | Estimates at or above this value are refused in favor of an epic. |
| `estimation.epic_sizes` | string array | `["XS", "S", "M", "L", "XL"]` | nonempty strings, smallest first | Epic sizes, matched by name to the project size field's options. |
| `github_project.owner` | string | none | a user or organization login, or `@me` | Owner of the GitHub project board. |
| `github_project.number` | integer | none | positive integer | Project number within the owner. |
| `github_project.estimate_field` | string | `"Estimate"` | field name | Number field that receives the estimate. |
| `github_project.size_field` | string | `"Size"` | field name, or `""` to disable | Single-select field that receives the epic size. |

## Validation

Validate the whole file before resolving the target, deferring only the rules that mention the resolved provider until the provider is known. Stop and report the key, the value, and the broken rule on any of these:

- an unknown table or key, including inside `[[milestone.rules]]`;
- a missing `version`, or a `version` other than the integer `1`;
- a value of the wrong TOML type (a boolean is never an integer);
- an enum value outside its accepted values;
- an empty string, a string containing a line break, or a duplicate entry in any string array;
- `title.prefix = "category"` with empty `title.categories`;
- `estimation.scale` empty or not strictly increasing, `warn_at` not greater than every `scale` value, or `refuse_at` not greater than `warn_at`;
- `estimation.target = "github-project"` without a `[github_project]` table, or with an empty `estimate_field`;
- `estimation.target = "github-project"`, or a `[github_project]` table, when the resolved provider is GitLab;
- `estimation.target = "gitlab-weight"` when the resolved provider is GitHub;
- a `[github_project]` table without `owner` and `number`;
- a `[[milestone.rules]]` entry missing `name` or `when`, or two entries with the same `name`.

Never ignore, coerce, or guess an invalid value.

## Field behavior

- **Precedence.** Apply the user's explicit request, then repository instruction files, then native issue templates, then this file, then package defaults. A lower level fills only what higher levels leave open.
- **`provider` and `remote`.** Configuration is loaded before the target is resolved. A project the user names always wins; when it is not the project of a local remote, the file is not read at all. Otherwise a configured `remote` selects the target, which suits forks whose issues belong upstream. A configured `remote` that does not exist or whose host does not identify a forge stops the run. `provider` identifies only a self-hosted host; when it contradicts a host that identifies itself, the run stops.
- **`labels.policy`.**
  - `existing-only` applies existing labels that fit, plus every configured label for the type that exists. A configured label that does not exist is reported as missing, and its creation is offered for separate approval.
  - `propose-new` also suggests new labels where no existing label fits. Each needs the same separate approval.
  - `none` applies no labels, ignores the per-type lists and `bug_detection`, and offers no label creation.
- **`milestone.policy`.**
  - `optional` assigns an open milestone when a rule or an obvious existing milestone fits.
  - `required` always assigns one; when nothing fits, it proposes a new milestone for separate approval instead of choosing silently.
  - Rules are evaluated in order, and the first whose `when` describes the issue wins. A rule naming a milestone that does not exist is proposed for creation, never assigned silently.
- **`estimation`.**
  - Stories, bugs, and tasks get an estimate from `scale`, or exactly `warn_at` after a split warning and explicit confirmation. Any estimate at or above `refuse_at` is refused, and an epic with child issues is proposed instead.
  - Epics get a size from `epic_sizes` only when `target = "github-project"` and `github_project.size_field` is not empty. Otherwise an epic gets neither size nor estimate.
  - `gitlab-weight` writes the estimate as the GitLab issue weight.
- **`[github_project]`.**
  - When present, every created issue is added to the project.
  - The project, the estimate and size fields, and each size option are resolved by name at run time. A missing project, field, or option stops before creation; never write a different field or option.
  - Never store project, field, or option node IDs in configuration.

## Examples

A GitLab project that records estimates as weights and requires a milestone:

```toml
version = 1

[milestone]
policy = "required"

[estimation]
target = "gitlab-weight"
```

A GitHub repository with categorized titles, detection labels for bugs, milestone rules, a shared Definition of Done, and a project board:

```toml
version = 1

[title]
prefix = "category"
categories = ["bug", "ci", "enhancement", "test-quality", "epic"]

[labels]
epic = ["epic"]
bug_detection = ["found-by-test", "found-by-manual-testing", "found-in-production"]

[milestone]
policy = "required"

[[milestone.rules]]
name = "Bug Fixes"
when = "Bugs, flakiness fixes, security patches"

[[milestone.rules]]
name = "CI Improvements"
when = "CI workflows: scheduling, triggers, parallelism, caching, dependency bots"

[definition_of_done]
common = ["Estimate set on the project board", "Actual hours recorded on the project board"]

[estimation]
target = "github-project"

[github_project]
owner = "OWNER"
number = 1
```
