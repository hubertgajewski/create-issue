# Task Template

Use for technical work with no direct user-facing behavior change: refactoring, CI, dependency upgrades, documentation, or tooling. Do not force a user story onto a task.

## Title

An imperative action with its object, for example `Pin CI container images by digest`.

## Sections

| Section | Required | Content |
| --- | --- | --- |
| Summary | yes | One or two sentences: what changes. |
| Motivation | yes | Why the work is needed now: risk, cost, or the work it unblocks. |
| Scope | yes | **In scope** and **Out of scope** bullet lists. |
| Acceptance Criteria | yes | `### AC1: <name>` onward, each one observable, verifiable statement. |
| Done Checklist | yes | Issue-specific `- [ ]` items, then the configured team-wide Definition of Done items. |

## Body

```markdown
## Summary

<what changes>

## Motivation

<why now>

## Scope

**In scope**

- <item>

**Out of scope**

- <item>

## Acceptance Criteria

### AC1: <name>

<observable, verifiable statement>

## Done Checklist

- [ ] <observable, verifiable item>
```
