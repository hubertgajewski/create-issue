# Story Template

Use for new or changed behavior with a user-visible or consumer-visible outcome.

## Title

An imperative outcome, for example `Export monthly report as CSV`. Name the outcome, not the implementation.

## Sections

| Section | Required | Content |
| --- | --- | --- |
| Summary | yes | One or two sentences: the problem and why it matters now. |
| User Story | yes | `As a <concrete persona>, I want <capability>, so that <benefit>.` One story per issue. |
| Context | yes | Current behavior, constraints, and evidence: `path:line` references, links, prior issues. |
| Scope | yes | **In scope** and **Out of scope** bullet lists. Out of scope names the nearest tempting extensions. |
| Acceptance Criteria | yes | `### AC1: <name>` onward, each a bulleted Given/When/Then scenario; at least one failure or edge case. |
| Technical Notes | no | Non-binding implementation ideas, starting with the line `Non-binding.` |
| Dependencies | no | Parent epic, blocking and blocked issues, related issues, each as an issue link. |
| Definition of Done | yes | Issue-specific `- [ ]` items, then configured common items. |

## Body

```markdown
## Summary

<problem and why it matters>

## User Story

As a <persona>, I want <capability>, so that <benefit>.

## Context

<current behavior, constraints, path:line references>

## Scope

**In scope**

- <item>

**Out of scope**

- <item>

## Acceptance Criteria

### AC1: <happy path>

- **Given** <precondition>
- **When** <action>
- **Then** <observable outcome>

### AC2: <failure or edge case>

- **Given** <precondition>
- **When** <action>
- **Then** <observable outcome>

## Technical Notes

Non-binding.

- <idea>

## Dependencies

- <relationship>: <issue link>

## Definition of Done

- [ ] <observable, verifiable item>
```
