# Maintainer guide

Procedures that need the Maintainer role on the GitLab project.

## CI and pipelines

[`.gitlab-ci.yml`](../.gitlab-ci.yml) defines one `test` job that runs
`python -m unittest discover -s tests -v` on Python 3.10 and Python 3.14. Both versions
are required: `requirements-test.txt` installs `tomli` only below Python 3.11, so 3.10
exercises the `tomli` fallback in `tests/test_configuration.py` and 3.14 exercises the
standard-library `tomllib`.

### When a pipeline runs

GitLab applies the first matching workflow rule:

| Event | Pipeline |
| --- | --- |
| **Build > Pipelines > New pipeline** | Always runs, even when `CI_ENABLED` is `false` |
| Any other event while `CI_ENABLED` is `false` | None |
| A merge request is opened or updated | Merge request pipeline |
| A push to a branch with an open merge request | None; the merge request pipeline covers it |
| A push to any other branch | Branch pipeline |

[`tests/test_ci_configuration.py`](../tests/test_ci_configuration.py) pins this order, so
reordering the rules fails the suite.

### Disabling automatic pipelines

`CI_ENABLED` is declared in `.gitlab-ci.yml` with the value `true`. To stop automatic
pipelines, for example while CI minutes are exhausted:

1. Go to **Settings > CI/CD > Variables** and add a project variable `CI_ENABLED` with the
   value `false`. Only the exact lowercase string `false` disables pipelines.
   - Select **Visible**. The default, **Masked**, requires at least eight characters, so
     `false` cannot be saved with it.
   - Leave **Protect variable** cleared. A protected variable reaches only pipelines on
     protected branches, so pushes to other branches would still run pipelines.
2. To restore automatic pipelines, delete the project variable.

While pipelines are disabled, a merge request gets no new pipeline, so the merge gate blocks
it. A pipeline started from **Build > Pipelines > New pipeline** is a branch pipeline and
does not unblock the merge, because the merge check uses the merge request pipeline. To
unblock a merge request, retry the failed jobs of its merge request pipeline when that
pipeline ran on the latest commit. Otherwise, delete the project variable and select
**Run pipeline** on the merge request's **Pipelines** tab.

### Updating a Python image

Images are pinned by manifest digest so that a retagged image cannot change a passing
pipeline. To move to a newer patch release, resolve the digest of the multi-platform image
and replace the tag and digest together:

```bash
docker buildx imagetools inspect python:3.14-slim
```

Python 3.10 is the only matrix entry that exercises the `tomli` fallback. To change which
versions run, update `SUPPORTED_PYTHONS` in `tests/test_ci_configuration.py` in the same
change as the matrix.

### Merge gating

Merges require a successful pipeline: **Settings > Merge requests > Merge checks >
Pipelines must succeed**. Leave **Skipped pipelines are considered successful** off. Enable
the check only after a pipeline has passed on `main`, then confirm it through the API:

```bash
glab api --method PUT projects/:id --field only_allow_merge_if_pipeline_succeeds=true
glab api projects/:id | jq .only_allow_merge_if_pipeline_succeeds
```

The second command must print `true`.
