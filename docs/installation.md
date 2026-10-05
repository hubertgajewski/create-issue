# Installation

`create-issue` is an [Agent Skill](https://agentskills.io) packaged in `skills/create-issue/`.
Install it with the release installer, which downloads a pinned version, verifies its SHA-256
checksum, and copies the package into your client's skill directory. You can also copy the
directory yourself from a source checkout.

## Requirements

- **An agent client that supports Agent Skills**, or one that can load `SKILL.md` directly.
- **Git**, to resolve the target project and the trusted policy revision from a local
  checkout, and to fetch the package.
- **`gh` for GitHub or `glab` for GitLab**, authenticated for the host you file issues on.
  The skill uses them for read-only queries while drafting, and to create the issue after
  you approve it.
- **For the release installer:** `sh`, `curl`, `tar`, and `sha256sum` or `shasum` on Linux
  and macOS, or PowerShell 7 on Windows.
- **Python 3.10 or later is optional.** It runs
  `create-issue/scripts/normalize_reference.py`, which accepts project and issue URLs.
  Without it, the skill asks you to name a project as a path such as `OWNER/REPO` and a
  parent issue as `#N` or `PROJECT#N`.

## Install from a release

Releases start at `v1.0.0`. Until that release is published, the commands below fail at the
download step and change nothing; [install from a source checkout](#install-from-a-source-checkout)
instead.

Paste the three commands for your operating system from the directory you want a project
installation in, or from anywhere for a user installation. The installer asks which client and
[scope](#choose-a-scope) to use, and shows the destination before it downloads the package or
changes any file. It does not default to any client.

### Linux

```bash
( set -eu; install_dir="$(mktemp -d)"; trap 'rm -rf "$install_dir"' EXIT HUP INT TERM; curl --fail --fail-early --location --proto '=https' --tlsv1.2 --output "$install_dir/create-issue-install.sh" https://gitlab.com/hubertgajewski-ai/create-issue/-/releases/v1.0.0/downloads/create-issue-install.sh --output "$install_dir/create-issue-install.sh.sha256" https://gitlab.com/hubertgajewski-ai/create-issue/-/releases/v1.0.0/downloads/create-issue-install.sh.sha256 &&
(cd "$install_dir" && sha256sum -c create-issue-install.sh.sha256) &&
sh "$install_dir/create-issue-install.sh" )
```

### macOS

```bash
( set -eu; install_dir="$(mktemp -d)"; trap 'rm -rf "$install_dir"' EXIT HUP INT TERM; curl --fail --fail-early --location --proto '=https' --tlsv1.2 --output "$install_dir/create-issue-install.sh" https://gitlab.com/hubertgajewski-ai/create-issue/-/releases/v1.0.0/downloads/create-issue-install.sh --output "$install_dir/create-issue-install.sh.sha256" https://gitlab.com/hubertgajewski-ai/create-issue/-/releases/v1.0.0/downloads/create-issue-install.sh.sha256 &&
(cd "$install_dir" && shasum -a 256 -c create-issue-install.sh.sha256) &&
sh "$install_dir/create-issue-install.sh" )
```

The checksum command must print `create-issue-install.sh: OK`. Because the commands are joined
with `&&`, a failed download or checksum stops the installer from running.

### Windows PowerShell

```powershell
& { $ErrorActionPreference = "Stop"; $installDir = Join-Path ([System.IO.Path]::GetTempPath()) ("create-issue-install-" + [guid]::NewGuid()); New-Item -ItemType Directory -Path $installDir | Out-Null; try { Invoke-WebRequest https://gitlab.com/hubertgajewski-ai/create-issue/-/releases/v1.0.0/downloads/create-issue-install.ps1 -OutFile (Join-Path $installDir "create-issue-install.ps1"); Invoke-WebRequest https://gitlab.com/hubertgajewski-ai/create-issue/-/releases/v1.0.0/downloads/create-issue-install.ps1.sha256 -OutFile (Join-Path $installDir "create-issue-install.ps1.sha256")
$expected = ((Get-Content (Join-Path $installDir "create-issue-install.ps1.sha256") -TotalCount 1) -split '\s+')[0]; if ((Get-FileHash (Join-Path $installDir "create-issue-install.ps1") -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expected) { throw "Installer checksum verification failed" }
& (Join-Path $installDir "create-issue-install.ps1") } finally { Remove-Item -Recurse -Force -LiteralPath $installDir -ErrorAction SilentlyContinue } }
```

PowerShell stops if either download or the checksum check fails.

The installer then downloads the package archive, verifies it against its `.sha256` file, and
checks that the archive holds only regular files and directories under `create-issue/`, with
the package version it asked for. A failed check exits non-zero, names the problem, and leaves
the skill directory unchanged. On success it reports the installed version, the destination,
the checksum, and the command to draft a first issue.

## Automated installation

Non-interactive runs must give a client and a scope; the installer never guesses. The release
version is built into each installer; `--version` or `-Version` selects another release.

| Argument | POSIX | PowerShell | Values |
| --- | --- | --- | --- |
| Client | `--client` | `-Client` | `claude-code`, `codex`, `cursor`, or `gemini` |
| Scope | `--scope` | `-Scope` | `user` or `project`; PowerShell ignores case |
| Version | `--version` | `-Version` | An exact release such as `v1.0.0` |
| Replace an installation | `--update` | `-Update` | Replaces an existing `create-issue` directory |
| Offline assets | `--asset-dir` | `-AssetDirectory` | A directory holding the archive and its `.sha256` file |

Each client ID installs into the skill directory listed in
[Client directories](#client-directories): `.claude/skills` for `claude-code`, and
`.agents/skills` for `codex`, `cursor`, and `gemini`, under your home directory for `user`
scope or the current directory for `project` scope. Any other client ID is rejected with the
list of supported IDs. `release-contract.json` at the repository root owns this mapping.

For example, a Claude Code project installation uses:

```bash
sh ./create-issue-install.sh --client claude-code --scope project
```

```powershell
.\create-issue-install.ps1 -Client claude-code -Scope Project
```

### Manual download

If command-line downloads are unavailable, open the
[`v1.0.0` release](https://gitlab.com/hubertgajewski-ai/create-issue/-/releases/v1.0.0) and
save all four files for your operating system in one directory:

- Linux and macOS: `create-issue-install.sh`, `create-issue-install.sh.sha256`,
  `create-issue-v1.0.0.tar.gz`, and `create-issue-v1.0.0.tar.gz.sha256`.
- Windows: `create-issue-install.ps1`, `create-issue-install.ps1.sha256`,
  `create-issue-v1.0.0.zip`, and `create-issue-v1.0.0.zip.sha256`.

From the directory you want a project installation in, verify the installer and run it against
the downloaded files. On Linux:

```bash
(cd /path/to/downloads && sha256sum -c create-issue-install.sh.sha256) &&
sh /path/to/downloads/create-issue-install.sh --asset-dir /path/to/downloads
```

On macOS, replace `sha256sum -c` with `shasum -a 256 -c`. In PowerShell:

```powershell
$assets = "C:\path\to\downloads"; $installer = Join-Path $assets "create-issue-install.ps1"; $expected = ((Get-Content (Join-Path $assets "create-issue-install.ps1.sha256") -TotalCount 1) -split '\s+')[0]
if ((Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expected) { throw "Installer checksum verification failed" }
& $installer -AssetDirectory $assets
```

The installer verifies the package checksum again before it changes the destination. Do not
run an installer whose own checksum check failed.

### What a checksum proves

A `.sha256` file published beside its archive detects a corrupted or truncated download. It
does not prove who published the archive: someone able to replace both files could make them
agree. Release tags are protected so that only maintainers can create them, which limits who
can publish a release in the first place.

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
<skill-directory>/create-issue/README.md
<skill-directory>/create-issue/CHANGELOG.md
<skill-directory>/create-issue/LICENSE
<skill-directory>/create-issue/.claude-plugin/plugin.json
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

For a release installation, read the new release's
[changelog](../skills/create-issue/CHANGELOG.md) entry, then download and verify its installer
as in [Manual download](#manual-download) and run it with `--update` or `-Update`. The
installer replaces the directory in one step and restores the previous installation if
activation fails.

For a source installation:

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

## Other installation environments

The installer refuses a client with no local skill directory instead of guessing one:

- `claude-chat`: Claude's chat apps load skills from uploads rather than a directory on disk,
  and this skill needs a local Git checkout and `gh` or `glab`, which they do not provide.

Any other client that supports Agent Skills can use a manual copy, as described in
[Client directories](#client-directories).
