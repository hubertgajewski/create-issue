# Installation

`create-issue` is an [Agent Skill](https://agentskills.io) packaged in `skills/create-issue/`.
Install it by copying that directory, on its own, into a directory your agent client scans for
skills. There is no installer yet; this guide installs from a source checkout.

## Requirements

- **An agent client that supports Agent Skills**, or one that can load `SKILL.md` directly.
- **Git**, to resolve the target project and the trusted policy revision from a local
  checkout, and to fetch the package.
- **`gh` for GitHub or `glab` for GitLab**, authenticated for the host you file issues on.
  The skill uses them for read-only queries while drafting, and to create the issue after
  you approve it.
- **Python 3.10 or later is optional.** It runs
  `create-issue/scripts/normalize_reference.py`, which accepts project and issue URLs.
  Without it, the skill asks you to name a project as a path such as `OWNER/REPO` and a
  parent issue as `#N` or `PROJECT#N`.

## Choose a scope

| Scope | Use it when | Trust requirement |
| --- | --- | --- |
| User | You want one installation across all your repositories, or you work on branches you do not trust. | Install a revision you have reviewed, outside any contributor-controlled checkout. |
| Project | A team wants one version of the skill committed with the repository. | Everyone who can change the repository can change the installed skill, and a branch that edits it changes how the skill behaves when started from that branch. |

The skill reads repository policy from a trusted committed revision, but your client loads
the skill itself from the files on disk. Use a user installation when you start the client
from a branch or fork you have not reviewed.

## Client directories

Copy the package so that its directory is named `create-issue` inside one of these skill
directories. Paths starting with `~` are in your home directory; the others are relative to
the repository root.

| Client | Project scope | User scope | Invocation |
| --- | --- | --- | --- |
| Claude Code | `.claude/skills` | `~/.claude/skills` | `/create-issue <request>` |
| Codex | `.agents/skills` | `~/.agents/skills` | `$create-issue <request>`; `/skills` lists installed skills |
| Cursor | `.agents/skills` or `.cursor/skills` | `~/.agents/skills` or `~/.cursor/skills` | `/create-issue <request>` in Agent chat |
| Gemini CLI | `.agents/skills` or `.gemini/skills` | `~/.agents/skills` or `~/.gemini/skills` | No dedicated syntax: describe the issue you want drafted, and approve the activation prompt for `create-issue`. `/skills list` lists installed skills. |

Codex, Cursor, and Gemini CLI all read `.agents/skills` and `~/.agents/skills`, so one copy
there serves all three. Claude Code uses `.claude/skills` and `~/.claude/skills` instead.

Another client that supports Agent Skills works the same way: copy the package into the
directory its documentation names. A client without skill support can be pointed at
`create-issue/SKILL.md` directly; every path the workflow loads is relative to that file.

The installed layout must be:

```text
<skill-directory>/create-issue/SKILL.md
<skill-directory>/create-issue/agents/openai.yaml
<skill-directory>/create-issue/references/
<skill-directory>/create-issue/scripts/normalize_reference.py
```

Copy the whole directory. Do not flatten it, copy only `SKILL.md`, or copy the repository
root: the skill depends on nothing outside `skills/create-issue/`, and the repository's own
`AGENTS.md`, tests, and documentation are not part of it.

These first-party pages own the directory paths and invocation syntax above, which change
between client releases. They were last checked on 2026-10-04.

- [Claude Code](https://code.claude.com/docs/en/skills)
- [Codex](https://learn.chatgpt.com/docs/build-skills)
- [Cursor](https://cursor.com/docs/context/skills)
- [Gemini CLI](https://geminicli.com/docs/cli/using-agent-skills/)

## Install from a source checkout

Set `destination` to `<skill-directory>/create-issue` for your client and scope. Set
`create_issue_ref` to `origin/main` for the latest revision, or to a commit SHA you have
reviewed. The commands refuse to overwrite an existing installation; to replace one, follow
[Updating](#updating).

On Linux and macOS:

```bash
(
set -eu
create_issue_ref="origin/main"
destination="$HOME/.agents/skills/create-issue"
source_dir="$(mktemp -d)"
trap 'rm -rf "$source_dir"' EXIT

if [ -e "$destination" ] || [ -L "$destination" ]; then
  echo "$destination already exists; see Updating" >&2
  exit 1
fi

git clone --quiet https://gitlab.com/hubertgajewski-ai/create-issue.git "$source_dir"
git -C "$source_dir" checkout --quiet --detach "$create_issue_ref"
git -C "$source_dir" log -1 --format='Installing create-issue %H'
mkdir -p "$(dirname "$destination")"
cp -R "$source_dir/skills/create-issue" "$destination"
)
```

In Windows PowerShell:

```powershell
$createIssueRef = "origin/main"
$destination = Join-Path $HOME ".agents\skills\create-issue"
$sourceDir = Join-Path ([System.IO.Path]::GetTempPath()) ("create-issue-" + [guid]::NewGuid())

if ($null -ne (Get-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue)) {
    throw "$destination already exists; see Updating"
}

try {
    git clone --quiet https://gitlab.com/hubertgajewski-ai/create-issue.git $sourceDir
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
    git -C $sourceDir checkout --quiet --detach $createIssueRef
    if ($LASTEXITCODE -ne 0) { throw "git checkout failed" }
    git -C $sourceDir log -1 --format="Installing create-issue %H"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -Recurse -LiteralPath (Join-Path $sourceDir "skills\create-issue") -Destination $destination
}
finally {
    Remove-Item -Recurse -Force -LiteralPath $sourceDir -ErrorAction SilentlyContinue
}
```

Note the printed commit SHA; it identifies the installed revision when you update.

For a project installation, run the commands from the repository root with a relative
`destination` such as `.claude/skills/create-issue`, then commit the copied directory.

## Verify the installation

1. Start a new client session so the client discovers the new skill.
2. List the installed skills and confirm `create-issue` appears, with its entry point at
   `<skill-directory>/create-issue/SKILL.md`.
3. In a repository you can file issues in, ask for a draft, for example
   `/create-issue Draft a task to document the release process`.
4. Confirm that the skill presents a complete draft and stops to wait for your approval.
   Drafting changes nothing on the tracker, so you can decline the draft.

If the skill does not appear, check that the directory is named `create-issue`, that
`SKILL.md` sits directly inside it, and that the client reads the skill directory you used.

## Updating

Replace the whole installed directory with the new revision. Never copy a new revision over
an old one: files removed upstream would stay behind.

1. Review what changed since the installed revision, especially in `SKILL.md`,
   `references/`, and `scripts/`. From a clone of this repository, with the commit SHA
   printed when you installed:

   ```bash
   git fetch origin
   git diff <installed-commit-sha> origin/main -- skills/create-issue
   ```

   Without that SHA, compare the installed directory with `skills/create-issue` in a fresh
   clone using `diff -ru`.
2. Delete the installed directory: `rm -rf <skill-directory>/create-issue`, or in
   PowerShell `Remove-Item -Recurse -Force -LiteralPath <skill-directory>\create-issue`.
3. Run the commands in [Install from a source checkout](#install-from-a-source-checkout)
   again, with `create_issue_ref` set to the revision you reviewed.
4. Repeat [Verify the installation](#verify-the-installation).

For a project installation, make the replacement one commit, so reviewers see the complete
change to the skill.

To uninstall, delete the `create-issue` directory from the skill directory.
