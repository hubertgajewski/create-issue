# Bug Template

Use for existing behavior that deviates from documented, specified, or reasonably expected behavior.

## Title

`<area>: <symptom> when <condition>`, for example `Checkout: total ignores discount when cart has one item`. Name the observable symptom, not the suspected cause.

## Sections

| Section | Required | Content |
| --- | --- | --- |
| Summary | yes | One or two sentences: what goes wrong and who is affected. |
| Environment | yes | Version or commit, platform, browser or device, and relevant configuration. |
| Steps to Reproduce | yes | Numbered, minimal steps from a clean state. |
| Expected Result | yes | The correct behavior and its source: documentation, specification, or prior behavior. |
| Actual Result | yes | Observed behavior with a minimal, redacted excerpt of errors or logs. |
| Frequency | yes | `Always`, or intermittent with the observed rate, for example `3 of 10 runs`. |
| Impact | yes | Severity, who is affected, and any workaround. |
| Detection | yes | How the bug was found, using the configured detection vocabulary when one exists, otherwise a short phrase or `Unknown`. |
| Suspected Cause | no | A hypothesis with `path:line` references, explicitly labeled as unconfirmed. |
| Acceptance Criteria | yes | `### AC1: <name>` onward, each a bulleted Given/When/Then scenario. The first restates the reproduction with the expected result; one requires a regression test. |
| Done Checklist | yes | Issue-specific `- [ ]` items, then the configured team-wide Definition of Done items. |

## Body

```markdown
## Summary

<what goes wrong and who is affected>

## Environment

- Version or commit: <value>
- Platform: <value>

## Steps to Reproduce

1. <step>

## Expected Result

<correct behavior and its source>

## Actual Result

<observed behavior and minimal redacted output>

## Frequency

<Always | intermittent with rate>

## Impact

<severity, affected users, workaround>

## Detection

<how it was found>

## Suspected Cause

Unconfirmed: <hypothesis with path:line references>

## Acceptance Criteria

### AC1: Reproduction yields the expected result

- **Given** <state from the reproduction steps>
- **When** <triggering action>
- **Then** <expected result>

### AC2: Regression is covered

- **Given** the fix is applied
- **When** the automated test suite runs
- **Then** a test that fails without the fix passes

## Done Checklist

- [ ] <observable, verifiable item>
```
