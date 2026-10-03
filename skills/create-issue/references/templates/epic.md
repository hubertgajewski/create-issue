# Epic Template

Use for an outcome that needs two or more independently deliverable child issues. An epic describes the outcome and tracks its children; detailed acceptance criteria belong in the children.

## Title

The outcome as an imperative phrase, for example `Support self-hosted GitLab instances`.

## Sections

| Section | Required | Content |
| --- | --- | --- |
| Outcome | yes | One or two sentences describing the world once the epic is done. |
| Success Criteria | yes | Observable conditions that close the epic, as a bulleted list. |
| Scope | yes | **In scope** and **Out of scope** bullet lists. |
| Child Issues | yes | A task list with at least two entries: `- [ ] <issue link> — <title>` for existing issues, `- [ ] <title> (not yet created)` for planned ones. |
| Risks and Dependencies | yes | Known risks, external dependencies, and ordering constraints, or `None identified.` |

## Body

```markdown
## Outcome

<the world once the epic is done>

## Success Criteria

- <observable closing condition>

## Scope

**In scope**

- <item>

**Out of scope**

- <item>

## Child Issues

- [ ] <issue link> — <title>
- [ ] <title> (not yet created)

## Risks and Dependencies

- <risk or dependency>
```
