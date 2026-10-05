# Maintainer guide

Procedures that need the Maintainer role on the GitLab project.

## CI and pipelines

[`.gitlab-ci.yml`](../.gitlab-ci.yml) defines a `test` job that runs
`python -m unittest discover -s tests -v` on Python 3.10 and Python 3.14. Both versions
are required: `requirements-test.txt` installs `tomli` only below Python 3.11, so 3.10
exercises the `tomli` fallback in `tests/test_configuration.py` and 3.14 exercises the
standard-library `tomllib`.

The Python images have no PowerShell, so the PowerShell installer tests skip there. The
`installer_powershell_test` job runs `tests/test_installers.py` again in a PowerShell image,
where they run. A tag pipeline adds the `build_release` and `publish_release` jobs described
in [Releases](#releases).

### When a pipeline runs

GitLab applies the first matching workflow rule:

| Event | Pipeline |
| --- | --- |
| **Build > Pipelines > New pipeline** | Always runs, even when `CI_ENABLED` is `false` |
| Any other event while `CI_ENABLED` is `false` | None |
| A tag is pushed | Tag pipeline, with the release jobs for a `vX.Y.Z` tag |
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

The same applies to the `python:3.14-trixie` image of `build_release`, which is used because
it includes Git, and to the PowerShell image of `installer_powershell_test`.

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

## Releases

A release publishes the package as `create-issue-vX.Y.Z.tar.gz` and `create-issue-vX.Y.Z.zip`,
plus `create-issue-install.sh` and `create-issue-install.ps1`, each with a `.sha256` file.
[`release-contract.json`](../release-contract.json) owns the asset names and the client
skill directories. Both installers carry a copy of the client table, because they must choose
a destination before they download anything; `tests/test_installers.py` fails when a copy
differs from the contract.

### Protecting release tags

Only Maintainers may create `v*` tags. Protect the pattern once, then confirm it through the
API:

```bash
glab api --method POST projects/:id/protected_tags --field name='v*' --field create_access_level=40
glab api projects/:id/protected_tags
```

The second command must list `v*` with `create_access_levels` containing only
`"access_level": 40`, `Maintainers`. Releasing needs this protection: `build_release` fails
for an unprotected tag, and `publish_release` does not run for one.

In the group's package registry settings, disable duplicate generic packages, so a published
version cannot be overwritten, and limit who can delete packages.

### Cutting a release

1. Choose the version under Semantic Versioning. Set it as `version` in
   `skills/create-issue/.claude-plugin/plugin.json`, as the latest heading in
   `skills/create-issue/CHANGELOG.md` with the release date, and as the default version in
   both installers: `version=` in `create-issue-install.sh` and `$Version` in
   `create-issue-install.ps1`. Update the release commands and asset names in
   `docs/installation.md` to the new tag. The suite fails while any of these disagree.
2. Merge that change to `main` through a merge request, and wait for the `main` pipeline to
   pass.
3. Tag the merged commit with an annotated tag and push it:

   ```bash
   git fetch origin main
   release_version=$(git show origin/main:skills/create-issue/.claude-plugin/plugin.json | python3 -c 'import json, sys; print(json.load(sys.stdin)["version"])')
   git tag -a "v$release_version" origin/main -m "Create Issue $release_version"
   git push origin "v$release_version"
   ```

4. Follow the tag pipeline. After the test jobs pass, `build_release` checks that the tag is
   protected, annotated, on a commit contained in `main`, and equal to the package version, and
   that both installers default to it. Any failed check fails the job before an asset is built.
   It then builds both archives with `git archive` from the tagged tree, so no working-tree
   state reaches a release, copies the installers from the tag, and writes the checksums.
5. `publish_release` checks again that the tag is protected and still targets the pipeline
   commit, uploads the eight assets to the project's generic package registry, and creates the
   GitLab release with a link to each. Rerunning it reuses identical uploads and fails if an
   asset with the same name has different content.
6. Open the release page, confirm all eight links, and run the published Linux or macOS
   commands in a scratch directory.

A published version is never changed. Fix a bad release with a new version.

### What a checksum covers

A `.sha256` file published beside its asset detects corruption, not an attacker who can
replace both. Releases are not signed; the protected tag and the package registry's access
controls are what limit who can publish.
